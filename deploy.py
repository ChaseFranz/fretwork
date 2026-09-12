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

It goes up in three cache classes, each its own sync. The entry pages
(index.html and the document pages) are rewritten in place, so they carry
no-cache and are revalidated. Everything under static/ and data/ carries a
content hash in its name, so it is immutable and cached for a year: a change is
a new name. A chart's files change only when that chart does, so graph/ carries
a week. The order keeps a page in flight consistent: graphs, then the hashed
files without --delete, then the entry pages with --delete, then the CloudFront
invalidation and a wait for it to complete, then the hashed files again with
--delete, which removes the previous generation only once no edge can still
serve the page that named it. sync sets those headers on the files it uploads,
which means files already in the bucket keep whatever they were uploaded with:
--set-headers rewrites the metadata on everything in place, and is only needed
after changing these values.
"""

import argparse
import json
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
from web import assets
from web.assets import CACHE_GRAPHS, CACHE_IMMUTABLE, CACHE_PAGE, IMMUTABLE_DIRS

ENV_FILE = '.env'
AWS_ENV = ('AWS_PROFILE', 'AWS_REGION', 'AWS_DEFAULT_REGION')
CREDENTIAL_PREFIXES = ('AWS_ACCESS_KEY', 'AWS_SECRET', 'AWS_SESSION')
BUCKET_RE = re.compile(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$')
# the entry pages publish writes, plus the three directories; a new page joins
# this set and bundle.PAGE_TOP in the same change
BUNDLE_TOP = {'index.html', '404.html', 'about.html', 'changelog.html', 'methodology.html', 'robots.txt',
              'static', 'data', 'graph'}
REQUIRED = ('index.html', 'graph/manifest.json')                   # proof it came from publish
GRAPHS = assets.GRAPH_DIR

# `aws s3 cp --metadata-directive REPLACE` replaces ALL metadata, and does not
# re-derive Content-Type the way an upload does: without these it writes
# binary/octet-stream over every object, which browsers refuse to run as an ES
# module. So --set-headers walks one pass per (prefix, file type) and states
# both the cache class and the type.
HEADER_PASSES = (
    # prefix, cache, globs
    (f'{GRAPHS}/', CACHE_GRAPHS, ('*.png', '*.json')),
    ('static/', CACHE_IMMUTABLE, ('*.js', '*.css', '*.svg')),
    ('data/', CACHE_IMMUTABLE, ('*.json',)),
    ('', CACHE_PAGE, ('*.html', '*.txt')),
)
# one sample of each kind verify() asks S3 about, as a glob under the site folder
SAMPLES = ('index.html', 'robots.txt', 'static/*.js', 'static/*.css', 'static/*.svg',
           'data/*.json', f'{GRAPHS}/*.png', f'{GRAPHS}/*.json')


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


def run(cmd, dry_run, capture=False):
    print('    ' + ' '.join(shlex.quote(part) for part in cmd))
    if dry_run and cmd[1] == 'cloudfront':
        return None
    if capture:
        return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    subprocess.run(cmd, check=True)
    return None


# One-off: sync only sets headers on what it uploads, so changing the values
# above leaves everything already in the bucket as it was. Every pass names both
# the cache policy and the content type, because REPLACE drops what it is not told.
def set_headers(bucket, dry_run):
    print(f"\nRewriting headers on s3://{bucket}/" + ("  (dry run)" if dry_run else ""))
    top_excludes = [arg for d in (GRAPHS, *IMMUTABLE_DIRS) for arg in ('--exclude', f'{d}/*')]
    for prefix, cache, globs in HEADER_PASSES:
        for pattern in globs:
            ctype = assets.content_type(pattern)
            cmd = ['aws', 's3', 'cp', f"s3://{bucket}/{prefix}", f"s3://{bucket}/{prefix}",
                   '--recursive', '--metadata-directive', 'REPLACE',
                   '--cache-control', cache, '--exclude', '*'] + (top_excludes if not prefix else []) + [
                   '--include', pattern, '--content-type', ctype]
            run(cmd + ['--dryrun'] if dry_run else cmd, dry_run)


# One object of each kind found locally, with the Content-Type prefix and the
# Cache-Control S3 must answer for it. A glob with no local match is skipped.
def samples(site_dir):
    site = pathlib.Path(site_dir)
    found = {}
    for pattern in SAMPLES:
        matches = sorted(site.glob(pattern))
        if matches:
            key = matches[0].relative_to(site).as_posix()
            found[key] = (assets.content_type(key).split(';')[0], assets.cache_class(key))
    return found


# A wrong Content-Type is invisible from this side - the upload succeeds, the
# bucket looks right, and the browser refuses to run the file. So ask S3 what it
# will actually serve, type and cache class, for one object of each kind before
# calling the deploy done.
def verify(bucket, site_dir):
    print("\nChecking what S3 will serve")
    wrong = []
    for key, (want_type, want_cache) in samples(site_dir).items():
        got = subprocess.run(
            ['aws', 's3api', 'head-object', '--bucket', bucket, '--key', key,
             '--query', '[ContentType,CacheControl]', '--output', 'text'],
            capture_output=True, text=True).stdout.strip()
        parts = got.split('\t') if got else ['', '']
        got_type, got_cache = (parts + ['', ''])[:2]
        ok = got_type.startswith(want_type) and got_cache == want_cache
        print(f"    {'ok  ' if ok else 'WRONG'}  {key}  ->  {got_type or '(no answer)'}  {got_cache}")
        if not ok:
            wrong.append(key)
    if wrong:
        sys.exit(f"\n{len(wrong)} object(s) would be served as the wrong type. "
                 f"Run: python deploy.py --set-headers")


# The commands a deploy runs, in order, so a test can read them without an
# aws on PATH. Graphs first, so a chart's files are in place before the page
# that links them; then the hashed files without --delete, so the new page
# never names a missing file; then the entry pages with --delete (its
# --exclude patterns apply to the destination listing too, so it cannot delete
# inside the three directories); then the invalidation and a wait for it; then
# the hashed files again with --delete, removing the previous generation once
# no edge can still serve the page that named it. An immutable directory the
# bundle does not have is skipped on both its passes (a bundle from before the
# data/ split still deploys). The wait's invalidation id is read from the
# create call's output at run time; the plan shows it as <pending>.
def plan(bucket, distribution, site_dir, dry_run=False, present=None):
    site = pathlib.Path(site_dir)
    have = present if present is not None else {d for d in IMMUTABLE_DIRS if (site / d).is_dir()}
    dry = ['--dryrun'] if dry_run else []
    immutable = [['aws', 's3', 'sync', f"{site_dir}/{d}/", f"s3://{bucket}/{d}/",
                  '--cache-control', CACHE_IMMUTABLE] + dry
                 for d in IMMUTABLE_DIRS if d in have]
    cmds = [['aws', 's3', 'sync', f"{site_dir}/{GRAPHS}/", f"s3://{bucket}/{GRAPHS}/",
             '--delete', '--cache-control', CACHE_GRAPHS] + dry]
    cmds += immutable
    cmds.append(['aws', 's3', 'sync', f"{site_dir}/", f"s3://{bucket}/", '--delete']
                + [arg for d in (GRAPHS, *IMMUTABLE_DIRS) for arg in ('--exclude', f'{d}/*')]
                + ['--cache-control', CACHE_PAGE] + dry)
    if distribution:
        cmds.append(['aws', 'cloudfront', 'create-invalidation',
                     '--distribution-id', distribution, '--paths', '/*', '--output', 'json'])
        cmds.append(['aws', 'cloudfront', 'wait', 'invalidation-completed',
                     '--distribution-id', distribution, '--id', '<pending>'])
    cmds += [cmd[:5] + ['--delete'] + cmd[5:] for cmd in immutable]
    return cmds


def skipped_dirs(site_dir):
    return [d for d in IMMUTABLE_DIRS if not (pathlib.Path(site_dir) / d).is_dir()]


def deploy(env_path=ENV_FILE, do_publish=True, dry_run=False, headers_only=False):
    bucket, distribution, header, site_dir = settings(env_path)
    if not bucket:
        sys.exit(f"FRETWORK_BUCKET is not set - copy .env.example to {env_path} and fill it in")
    if shutil.which('aws') is None:
        sys.exit("the AWS CLI (`aws`) is not on PATH")

    if headers_only:
        set_headers(bucket, dry_run)
        if not dry_run:
            verify(bucket, site_dir)
        print("\nDry run - nothing was changed\n" if dry_run else "\nDone\n")
        return

    do_publish = do_publish and not dry_run
    check_site(site_dir, need_output=not do_publish)
    if do_publish:
        publish(header=header, out_dir=site_dir)
        check_site(site_dir, need_output=True)

    print(f"\nDeploying {site_dir}/ -> s3://{bucket}/" + ("  (dry run)" if dry_run else ""))
    for d in skipped_dirs(site_dir):
        print(f"    skipped: no {d}/ locally")
    invalidation = None
    for cmd in plan(bucket, distribution, site_dir, dry_run):
        if cmd[1:3] == ['cloudfront', 'create-invalidation']:
            out = run(cmd, dry_run, capture=True)
            if out:
                invalidation = json.loads(out)['Invalidation']['Id']
                print(f"    invalidation {invalidation}")
            continue
        if cmd[1:3] == ['cloudfront', 'wait']:
            run(cmd[:-1] + [invalidation or '<pending>'], dry_run or not invalidation)
            continue
        run(cmd, dry_run)
    if not dry_run:
        verify(bucket, site_dir)
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
