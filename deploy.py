"""
DEPLOY - publish the site and push it to S3 through the AWS CLI

    python deploy.py                 # publish, sync to the bucket, invalidate CloudFront
    python deploy.py --dry-run       # list what the sync would upload; publishes nothing, sends nothing
    python deploy.py --no-publish    # sync whatever is already in the site folder
    python deploy.py --set-headers   # rewrite Cache-Control on everything already in the bucket

Settings come from a .env file in the repo root (gitignored - copy .env.example):

    FRETWORK_BUCKET=my-bucket             required (a bare bucket name)
    FRETWORK_DISTRIBUTION=E1ABC23DEF456   optional, CloudFront id to invalidate
    FRETWORK_HEADER=Main                  optional, default config.HEADER
    FRETWORK_SITE_DIR=site/Main           optional, default SITE_DIR/<header>
    AWS_PROFILE=fretwork-deploy           optional, handed to the AWS CLI
    AWS_REGION / AWS_DEFAULT_REGION       optional, likewise

For those AWS_* keys the .env value wins over one exported in your shell, so
the deploy always uses the profile you wrote down for it. Credentials never go
in .env: the AWS CLI's own profile or SSO login supplies them, and a .env that
contains any is refused. Needs `aws` on PATH; nothing is added to
requirements.txt.

The sync uses --delete, so the bucket must hold nothing but this site. Two
guards enforce that on this side: the site folder may contain only what
publish writes, and it must contain a publish output before anything is sent.

It goes up as two syncs, because the two halves want opposite caching. The page
and its assets are not fingerprinted - a deploy rewrites main.js in place - so
they carry no-cache and are revalidated, which costs a 304 and never serves a
stale script. A chart's PNG changes only when that chart does, so graphs carry a
week. sync sets those headers on the files it uploads, which means files already
in the bucket keep whatever they were uploaded with: --set-headers rewrites the
metadata on everything in place, and is only needed after changing these values.
"""

import argparse
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys

import config
from functions import envfile
from publish import publish

ENV_FILE = '.env'
AWS_ENV = ('AWS_PROFILE', 'AWS_REGION', 'AWS_DEFAULT_REGION')
CREDENTIAL_PREFIXES = ('AWS_ACCESS_KEY', 'AWS_SECRET', 'AWS_SESSION')
BUCKET_RE = re.compile(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$')
BUNDLE_TOP = {'index.html', '404.html', 'bootstrap.css', 'static', 'graph'}  # all publish writes
REQUIRED = ('index.html', 'graph/manifest.json')                   # proof it came from publish
GRAPHS = 'graph'
CACHE_PAGE = 'no-cache'                     # revalidate: these are rewritten in place
CACHE_GRAPHS = 'public, max-age=604800'     # a week; a chart's PNG changes when its chart does


def settings(env_path):
    values = envfile.load(env_path)
    leaked = [k for k in values if k.startswith(CREDENTIAL_PREFIXES)]
    if leaked:
        sys.exit(f"{env_path} contains AWS credentials ({', '.join(leaked)}) - remove them "
                 f"and use an AWS CLI profile or SSO login instead")
    for key in AWS_ENV:
        if values.get(key):
            os.environ[key] = values[key]
    bucket = re.sub(r'^s3://', '', values.get('FRETWORK_BUCKET', '').strip()).strip('/')
    if bucket and not BUCKET_RE.match(bucket):
        sys.exit(f"FRETWORK_BUCKET={values['FRETWORK_BUCKET']!r} is not a valid bucket name")
    header = values.get('FRETWORK_HEADER') or config.HEADER
    site_dir = values.get('FRETWORK_SITE_DIR') or pathlib.Path(config.SITE_DIR) / header
    return bucket, values.get('FRETWORK_DISTRIBUTION'), header, pathlib.Path(site_dir).expanduser()


# Anything publish would not have written means this is not the site's own folder.
def check_site(site_dir, need_output):
    if site_dir.exists():
        strays = sorted(p.name for p in site_dir.iterdir() if p.name not in BUNDLE_TOP)
        if strays:
            shown = ', '.join(strays[:5]) + (' ...' if len(strays) > 5 else '')
            sys.exit(f"{site_dir}/ holds files publish did not write ({shown}); refusing to "
                     f"use it as the site folder")
    if need_output:
        missing = [name for name in REQUIRED if not (site_dir / name).is_file()]
        if missing:
            sys.exit(f"{site_dir}/ has no publish output (missing {', '.join(missing)}); "
                     f"run publish.py first or drop --no-publish")


def run(cmd, dry_run):
    print('    ' + ' '.join(shlex.quote(part) for part in cmd))
    if dry_run and cmd[1] == 'cloudfront':
        return
    subprocess.run(cmd, check=True)


# One-off: sync only sets headers on what it uploads, so changing the values
# above leaves everything already in the bucket as it was.
def set_headers(bucket, dry_run):
    print(f"\nRewriting Cache-Control on s3://{bucket}/" + ("  (dry run)" if dry_run else ""))
    for prefix, value, extra in (
        (f"{GRAPHS}/", CACHE_GRAPHS, []),
        ("", CACHE_PAGE, ['--exclude', f"{GRAPHS}/*"]),
    ):
        cmd = ['aws', 's3', 'cp', f"s3://{bucket}/{prefix}", f"s3://{bucket}/{prefix}",
               '--recursive', '--metadata-directive', 'REPLACE',
               '--cache-control', value] + extra
        run(cmd + ['--dryrun'] if dry_run else cmd, dry_run)


def deploy(env_path=ENV_FILE, do_publish=True, dry_run=False, headers_only=False):
    bucket, distribution, header, site_dir = settings(env_path)
    if not bucket:
        sys.exit(f"FRETWORK_BUCKET is not set - copy .env.example to {env_path} and fill it in")
    if shutil.which('aws') is None:
        sys.exit("the AWS CLI (`aws`) is not on PATH")

    if headers_only:
        set_headers(bucket, dry_run)
        print("\nDry run - nothing was changed\n" if dry_run else "\nDone\n")
        return

    do_publish = do_publish and not dry_run
    check_site(site_dir, need_output=not do_publish)
    if do_publish:
        publish(header=header, out_dir=site_dir)
        check_site(site_dir, need_output=True)

    print(f"\nDeploying {site_dir}/ -> s3://{bucket}/" + ("  (dry run)" if dry_run else ""))
    # Graphs first, so a chart's PNG is in place before the page that links it.
    # The page sync excludes graph/, and an AWS CLI filter applies to the
    # destination listing too, so --delete there cannot reach a graph.
    for cmd in (
        ['aws', 's3', 'sync', f"{site_dir}/{GRAPHS}/", f"s3://{bucket}/{GRAPHS}/",
         '--delete', '--cache-control', CACHE_GRAPHS],
        ['aws', 's3', 'sync', f"{site_dir}/", f"s3://{bucket}/",
         '--delete', '--exclude', f"{GRAPHS}/*", '--cache-control', CACHE_PAGE],
    ):
        run(cmd + ['--dryrun'] if dry_run else cmd, dry_run)
    if distribution:
        run(['aws', 'cloudfront', 'create-invalidation', '--distribution-id', distribution,
             '--paths', '/*'], dry_run)
    print("\nDry run - nothing was published or sent\n" if dry_run else "\nDone\n")


def main():
    parser = argparse.ArgumentParser(description="Publish the site and sync it to S3.")
    parser.add_argument('--env', default=ENV_FILE, help=f"settings file (default: {ENV_FILE})")
    parser.add_argument('--no-publish', action='store_true', help="sync the existing site folder without publishing")
    parser.add_argument('--dry-run', action='store_true',
                        help="list what the sync would upload; publishes nothing and sends nothing")
    parser.add_argument('--set-headers', action='store_true',
                        help="rewrite Cache-Control on everything already in the bucket, then stop")
    args = parser.parse_args()
    try:
        deploy(env_path=args.env, do_publish=not args.no_publish, dry_run=args.dry_run,
               headers_only=args.set_headers)
    except subprocess.CalledProcessError as exc:
        sys.exit(f"aws exited with status {exc.returncode}")


if __name__ == '__main__':
    main()
