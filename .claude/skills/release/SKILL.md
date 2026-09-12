---
name: release
description: Cut a fretladder site release after a deploy the maintainer has confirmed: verify the live site against the local bundle, write the tag message as release notes, tag the deployed commit, push the tag (the release workflow publishes it), and record it in the spec index. Use when the maintainer says a deploy is done and wants it released, or asks to tag or release the site.
---

# Releasing the site

A release is a `fretladder-vX.Y.Z` annotated tag at the commit whose sources produced
the bundle now live at https://fretladder.com, pushed to `origin`, which
`.github/workflows/release.yml` turns into a GitHub Release with the tag message as
its notes. Nothing else is published anywhere. The maintainer deploys; this skill
runs after they say it is done. Never run `deploy.py` from here.

## Before tagging

1. Confirm the deploy is the local bundle. From the repo root with the venv active:
   `python tools/check_site.py --site site/Local` must report every check ok, and
   the script name the live page references must be the one in `site/Local/static/`:
   `curl -s https://fretladder.com/ | grep -o 'static/app\.[0-9a-f]*\.js'` against
   `ls site/Local/static/app.*.js`. If they differ, the live site is not this bundle;
   stop and say so.
2. Find the commit. The bundle was published from the working tree at the time; the
   tag goes on the last commit whose sources are in it, normally the head of `main`
   when publish ran. Check nothing in `git status` is uncommitted that the bundle
   contains.
3. Pick the number. Releases are few and meaningful, not one per deploy: the
   maintainer collapsed eleven same-day tags into three on 2026-09-11. Bump the minor
   for a visible change to the site, the patch for a fix to a release already out,
   the major for a change to what the site is. Ask when unsure which. Upstream's
   `vX.Y` tags are a different namespace and never reused.

## The tag message is the release notes

Write it with `git tag -a fretladder-vX.Y.Z <sha> -F -` and a heredoc, in this shape:

```
fretladder vX.Y.Z: 11,904 charts, 10,873 official; deployed 2026-09-11 21:58 -0500

One sentence on what the release is.

- What a visitor sees, one bullet per thing, plainest first
- ...

**Underneath** (optional): what changed in the pipeline or the bundle, when it matters
```

The first line names the release with the chart count from the strapline and the
deploy time (the bucket's `index.html` timestamp, `aws s3 ls s3://fretladder-prod/index.html`,
in local time); a blank line; then prose or `-` bullets. House style: British
spelling, no em dashes, no exclamation marks, nothing about the process of building
it. GitHub renders the body as Markdown; `**bold**` and bullets are enough.

## Publish

`git push origin fretladder-vX.Y.Z`. The release workflow runs on the tag push and
creates the release with `--notes-from-tag`; check it with `gh run list --workflow
release --limit 1` and `gh release view fretladder-vX.Y.Z`.

Two gotchas:

- GitHub runs a tag push's workflows from the workflow files *at the tagged commit*.
  A tag on a commit older than `.github/workflows/release.yml` (before 7262c7b)
  publishes nothing; then create it by hand:
  `gh release create fretladder-vX.Y.Z --verify-tag --notes-from-tag --title "fretladder vX.Y.Z"`.
- `gh` in this clone resolved to the parent repository, `Staycation44/fretwork`,
  until `gh repo set-default ChaseFranz/fretwork` was run on 2026-09-11. Check
  `gh repo set-default --view` says `ChaseFranz/fretwork` before any `gh release`
  command, and pass `-R ChaseFranz/fretwork` when in doubt (`--notes-from-tag`
  does not accept `-R`, which is why the default matters). Never create a release
  or a tag on upstream.

## Afterwards

- `docs/spec/README.md`: the status row of each section the release took live gets
  `tag fretladder-vX.Y.Z`, and the "Where the site stands now" paragraph moves if a
  number it quotes changed.
- If the release retired something a rollback would need (a manifest, a file class),
  README section 7's rollback table gets the row.
- Say what went live, the tag, and the release URL. Do not announce it anywhere
  else: community posts are the maintainer's.
