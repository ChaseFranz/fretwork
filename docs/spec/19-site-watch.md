# 19. The live-site watch

**Status:** Ready. Written 2026-09-12 against `main` at `e23f592`.

**Effort:** S. One workflow file, one flag on an existing tool, a README paragraph. Plus one console check that is the maintainer's.

**Depends on:** 01 (`tools/check_site.py`), landed.

## Goal

If fretladder.com stops serving the page, its data, its script as JavaScript or its 404, someone hears about it within a day without anyone remembering to look, and hears again when it is well.

## Why

`tools/check_site.py` (twelve checks, `tools/check_site.py:90-226`) runs after a deploy, by hand, and never otherwise. The failure it was written for, `binary/octet-stream` on every object after a headers pass (CLAUDE.md), left the bucket looking fine from the AWS side and the page blank from the visitor's. The other ways a static site breaks between deploys are silent too: an expired certificate, a CloudFront configuration change, a bucket policy edit, compression switched off. The tool already knows what right looks like; it only needs a clock and somewhere to speak.

## Current state

- `check_site.py` with no arguments checks `https://fretladder.com` (`DEFAULT_URL`, `:32`), needs no strapline (`--site` and `--strapline` are optional, `:230-244`), makes ten to fifteen GETs, prints one line per check and a summary, and exits with the number of failures (`run()` returns `rep.failed`, `:226`).
- `.github/workflows/ci.yml` runs on push and pull request only; there is no scheduled workflow. `release.yml` publishes tags.
- The fork's issues carry the `song pack` label and the request form; no label for the site's health.

## Design

1. **A scheduled workflow, `watch.yml`.** `on: schedule: cron '23 11 * * *'` (daily, 06:23 in the maintainer's time zone, after the overnight CloudFront log rollover and before the day) and `workflow_dispatch`. Checkout, Python 3.12, `python tools/check_site.py`; no secrets, no AWS: it is the visitor's view or it is nothing. `permissions: issues: write, contents: read`.
2. **It speaks through one issue.** On failure, the job looks for an open issue labelled `site watch`; none: `gh issue create` titled `fretladder.com: N checks failed on <date>` with the tool's output in a code block; one: `gh issue comment` with the new output. On success with an open `site watch` issue, it comments `all N checks passed on <date>` and closes it. So there is at most one open thread per outage, with the history inside it, and a recovery closes it without a hand.
3. **The tool learns `--json`.** The workflow needs the count and the lines without parsing the terminal text: `--json` prints `{"failed": n, "lines": [...]}` after the same run. Nothing else changes for the hand-run case.
4. **A badge.** `README.md`'s banner gains the workflow's status badge beside CI's, so the repo's front page says whether the site was up this morning.
5. **The compression check is the maintainer's.** Check 2 already asks CloudFront for `content-encoding` and passes today, so `Compress` is on. This section records the command that confirms it from the console side, in README's "After it is live": `aws cloudfront get-distribution-config --id E3NI1OAP71NJHL --query 'DistributionConfig.DefaultCacheBehavior.Compress'`, and the watch is what says if it ever goes off.

Rejected: an external uptime service (another account, another dashboard, for a site with no SLA); running the watch hourly (it is a hobby site's early warning, and a daily issue is enough; the schedule is one line to change); paging (there is no one to page).

## Data and interfaces

- `.github/workflows/watch.yml`; the label `site watch` (created by the workflow with `gh label create --force`, so the repo needs no hand setup).
- `tools/check_site.py --json`.
- The issue title shape and the recovery comment, both in the workflow file, since they are not the site's text.

## Files touched

`.github/workflows/watch.yml` (new), `tools/check_site.py`, `README.md` (the badge; "After it is live"), `CLAUDE.md` (the workflows sentence), `docs/spec/README.md`.

## Steps

1. `--json` on the tool; run it by hand against the live site and against `serve.py`. Commit: `check_site: --json for a caller that is not a person`.
2. The workflow, run once by `workflow_dispatch` against the live site; then once with the URL pointed at a path that does not exist to see the issue open, and once more to see it close. Delete that issue. Commit: `watch.yml: check_site.py daily, one issue per outage, closed on recovery`.
3. The badge and the README paragraph. Commit: `spec index: 19 on main`.

## Verification

Step 2's three runs, and the badge rendering on the front page. There is no unit test of a workflow; the tool's own checks are already exercised by the pipeline test against the fixture's bundle through `serve`.

## Risks and gotchas

- `gh` in Actions authenticates with `GITHUB_TOKEN`; an issue it creates does not trigger other workflows, which is the intended quiet.
- A GitHub outage looks like a site outage from inside Actions; the issue says which checks failed, and a DNS or TLS failure on every check is the tell.
- The schedule runs on GitHub's clock, which slips by minutes to an hour under load; the date in the title is the run's, not the cron's.

## Out of scope

- Watching the bucket, the CloudFront metrics or the bill (README's "After it is live" has the CloudWatch commands for the maintainer); a status page; alerting anyone but the fork's issues.
