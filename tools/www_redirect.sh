#!/usr/bin/env bash
# www.fretladder.com -> fretladder.com (section 21 of the spec). One idempotent
# pass, run by the maintainer with the SSO profile from .env, since it changes
# the live distribution and the zone (the maintainer's to run, like deploy.py):
#   1. the CloudFront Function in tools/cloudfront/www-to-apex.js, created or
#      updated from the file, tested on a www request, then published;
#   2. the distribution given www.fretladder.com as a second alias (the
#      certificate already covers *.fretladder.com) and the function attached
#      to its viewer-request;
#   3. Route 53: A and AAAA alias records for www pointing at the distribution;
#   4. a wait for the distribution to deploy, then the redirect checked from
#      outside.
# Every step reads what is there first and changes only what differs.
set -euo pipefail
cd "$(dirname "$0")/.."
eval "$(python3 -c "
from functions import envfile
v = envfile.load('.env')
if v.get('AWS_PROFILE'):
    print(f\"export AWS_PROFILE='{v['AWS_PROFILE']}'\")
print(f\"D='{v['FRETWORK_DISTRIBUTION']}'\")
")"
APEX=fretladder.com
WWW=www.$APEX
FN=fretladder-www-to-apex
CF_ZONE=Z2FDTNDATAQYW2                      # CloudFront's own hosted zone id, the same for every distribution
SCRATCH=$(mktemp -d)
trap 'rm -rf "$SCRATCH"' EXIT

echo "1. the function $FN"
CONFIG="{\"Comment\":\"$WWW -> $APEX, 301, path and query kept\",\"Runtime\":\"cloudfront-js-2.0\"}"
if aws cloudfront describe-function --name "$FN" --query ETag --output text >"$SCRATCH/etag" 2>/dev/null; then
  aws cloudfront update-function --name "$FN" --if-match "$(cat "$SCRATCH/etag")" --function-config "$CONFIG" \
    --function-code fileb://tools/cloudfront/www-to-apex.js --query ETag --output text >"$SCRATCH/etag"
  echo "   updated from tools/cloudfront/www-to-apex.js"
else
  aws cloudfront create-function --name "$FN" --function-config "$CONFIG" \
    --function-code fileb://tools/cloudfront/www-to-apex.js --query ETag --output text >"$SCRATCH/etag"
  echo "   created"
fi
cat >"$SCRATCH/event.json" <<JSON
{"version":"1.0","context":{"eventType":"viewer-request"},"viewer":{"ip":"1.2.3.4"},
 "request":{"method":"GET","uri":"/song/x.html","querystring":{"code":{"value":"10145439XG"}},
            "headers":{"host":{"value":"$WWW"}},"cookies":{}}}
JSON
OUT=$(aws cloudfront test-function --name "$FN" --if-match "$(cat "$SCRATCH/etag")" --stage DEVELOPMENT \
  --event-object fileb://"$SCRATCH/event.json" --query 'TestResult.FunctionOutput' --output text)
case "$OUT" in
  *'"statusCode":301'*"https://$APEX/song/x.html?code=10145439XG"*) echo "   test: 301 to the apex with the path and query" ;;
  *) echo "   test failed: $OUT"; exit 1 ;;
esac
ARN=$(aws cloudfront publish-function --name "$FN" --if-match "$(cat "$SCRATCH/etag")" \
  --query 'FunctionSummary.FunctionMetadata.FunctionARN' --output text)
echo "   published $ARN"

echo "2. the distribution $D"
aws cloudfront get-distribution-config --id "$D" >"$SCRATCH/dist.json"
python3 - "$SCRATCH" "$WWW" "$ARN" <<'PY'
import json, sys
scratch, www, arn = sys.argv[1:]
doc = json.load(open(f'{scratch}/dist.json'))
before = json.dumps(doc['DistributionConfig'], sort_keys=True)
cfg = doc['DistributionConfig']
items = list(cfg['Aliases'].get('Items') or [])
if www not in items:
    items.append(www)
cfg['Aliases'] = {'Quantity': len(items), 'Items': items}
kept = [a for a in (cfg['DefaultCacheBehavior'].get('FunctionAssociations', {}).get('Items') or []) if a['EventType'] != 'viewer-request']
kept.append({'FunctionARN': arn, 'EventType': 'viewer-request'})
cfg['DefaultCacheBehavior']['FunctionAssociations'] = {'Quantity': len(kept), 'Items': kept}
json.dump(cfg, open(f'{scratch}/dist-new.json', 'w'))
open(f'{scratch}/etag', 'w').write(doc['ETag'])
open(f'{scratch}/changed', 'w').write('0' if json.dumps(cfg, sort_keys=True) == before else '1')
print('   aliases', items, '| the function on viewer-request')
PY
if [ "$(cat "$SCRATCH/changed")" = 1 ]; then
  aws cloudfront update-distribution --id "$D" --if-match "$(cat "$SCRATCH/etag")" \
    --distribution-config file://"$SCRATCH/dist-new.json" --query 'Distribution.Status' --output text
else
  echo "   already so"
fi
TARGET=$(aws cloudfront get-distribution --id "$D" --query 'Distribution.DomainName' --output text)

echo "3. Route 53: $WWW -> $TARGET"
ZONE=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='$APEX.'].Id" --output text | sed 's|/hostedzone/||')
[ -n "$ZONE" ] || { echo "   no hosted zone for $APEX in this account"; exit 1; }
cat >"$SCRATCH/records.json" <<JSON
{"Comment":"$WWW as an alias of the distribution (section 21)","Changes":[
 {"Action":"UPSERT","ResourceRecordSet":{"Name":"$WWW.","Type":"A","AliasTarget":{"HostedZoneId":"$CF_ZONE","DNSName":"$TARGET.","EvaluateTargetHealth":false}}},
 {"Action":"UPSERT","ResourceRecordSet":{"Name":"$WWW.","Type":"AAAA","AliasTarget":{"HostedZoneId":"$CF_ZONE","DNSName":"$TARGET.","EvaluateTargetHealth":false}}}]}
JSON
aws route53 change-resource-record-sets --hosted-zone-id "$ZONE" --change-batch file://"$SCRATCH/records.json" \
  --query 'ChangeInfo.Status' --output text

echo "4. waiting for the distribution to deploy (a few minutes)"
aws cloudfront wait distribution-deployed --id "$D"
for path in / /song/ '/?code=10145439XG'; do
  printf '   https://%s%s -> ' "$WWW" "$path"
  curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' --max-time 20 "https://$WWW$path" || echo "no answer yet (DNS can take a minute; run the curl again)"
done
echo "done: $WWW answers 301 to https://$APEX with the path and query kept"
