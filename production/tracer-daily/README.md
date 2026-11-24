# GolfCut existing website: Semrush daily executor

Production entrypoints live in `/data/swi-algo/Swi-App-Factory/GolfCut/production/tracer-daily`; versioned copies are `operations/tracer-daily` in `diifan/golfcut-website`. This is an incremental existing-site pipeline, never a replacement site or a new Vercel project.

## Current input and ownership

[INPUT-CONTRACT.md](INPUT-CONTRACT.md) is the implemented controller interface. The controller owns `production/keyword-expansion`, its Semrush collector and its six-hour quota cooldown. The executor only reads its CSV/manifest/config/original exports and writes the expressly permitted `capacity.json`. It never calls Semrush.

Single runtime schedule: `/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily-golfcut/config.json`, fields `enabled,target,hour,minute,prepare_hour,prepare_minute,timezone`. `input-binding.json` binds the two producer paths. Independent keyword reservations, evidence cache, receipts and locks live in this same executor data directory, not the producer pool. `state.json` exposes heartbeat and runs for the controller UI.

## Pipeline

1. `keyword_input.py`: shared producer-lock snapshot; reread latest export hashes; exact keyword/KD/volume/evidence URL tuple match against original exports; strict KD<30 and volume>100; normalized keyword/intent/source dedupe; preserve reserved/published state. Fetch evidence only from registered HTTPS domains with safe redirects, public addresses and bounded streaming. Incomplete fetching is distinct from unsuitable/duplicate/threshold-rejected candidates.
2. `keyword_pages.py`: select exactly the configured target, reserve own state, render accepted keywords and corresponding source-linked recording guides in `/golf-guides`, add hubs and one existing tracer-article link, extend sitemap, run the original Bun build and commit in an isolated `website-seo-keywords-<day>` worktree. Existing home page, legacy references, worker/API, branding, styles and privacy stay unchanged. No partial batch is built when capacity is short.
3. `release.py stage`: verify immutable manifests and file hashes, then deploy to the existing `golfcut-website` project with production environment and `--skip-domain`. Reconcile uncertain uploads by batch and commit metadata.
4. At the configured publish minute, `release.py publish` only promotes a ready version with the matching target/main/project/commit. Verify production alias, every batch sitemap URL and every live HTML hash. Fast-forward Git main without force, then mark pool rows published. Fixtures and legacy video-title batches are rejected before any network call.
5. `scheduler.py` runs each minute, reads settings anew, checks production baseline between release ticks, prepares the next calendar day after configured prepare time and retries failures with cooldown. A clean isolated rebase is rebuilt/restaged; conflicts remain explicit. `golfcut-seo-daily.timer` is enabled. Controller expansion timers remain separate.

Empty input yields `insufficient_keywords` and, when reported by the producer, `source_quota_blocked`. Empty, incomplete or fixture batches never stage or publish. A source quota is not a completed production acceptance. Current Semrush error `-32107 Report limits exceeded` is handled by the producer's cooldown; no forced retries are performed here.

## Commands and evidence

```
python3 production/tracer-daily/prepare.py --day YYYY-MM-DD
python3 production/tracer-daily/release.py stage --day YYYY-MM-DD
python3 production/tracer-daily/release.py publish --day YYYY-MM-DD
python3 production/tracer-daily/scheduler.py
python3 -m unittest discover -s production/tracer-daily -p 'test_*.py'
python3 production/tracer-daily/test_build_fixture.py
```

The fixture test uses synthetic, labelled CSVs, mocked source fetches and an isolated temporary clone, then runs the actual original Bun build. It produces three visibly marked pages and proves stage/publish reject them. The release-flow test mocks **all** Git/Vercel/HTTP operations to check stage/promote/verification/finalization/idempotency; it is not an external deployment. Results: `semrush-fixture-build-result.json`, `semrush-fixture-browser-checks.json`, per-day receipts and `input-import-receipt.json` in executor data.

Systemd evidence: `systemctl show golfcut-seo-daily.timer -p ActiveState -p UnitFileState -p LastTriggerUSec`; service `Result` and `ExecMainStatus`; receipt `schedule`. No group messages or notifications are sent.

## Preserved history

Before the user's Semrush correction, 2,000 video-reference pages were published on 2026-11-24. They and their statuses remain intact. Another 2,000-page video batch was built/staged but not promoted; it is sealed in `2026-11-25-video-batch-preserved.json`. The old `source_cache.py`/video renderer are historical material only and are not wired into prepare/schedule/release. Official video titles are not a substitute for Semrush keywords.
