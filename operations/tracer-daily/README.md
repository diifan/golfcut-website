# GolfCut existing website: incremental SEO execution

**2026-11-24 correction:** only controller-supplied Semrush keywords may drive new batches. See [INPUT-CONTRACT.md](INPUT-CONTRACT.md). The video-catalog collector/renderer below describe the preserved historical release, not an authorized future keyword source. New generation awaits the real CSV/evidence handoff and source-specific writer adaptation; publication guards reject all video-title batches.

Installed executor: `/data/swi-algo/Swi-App-Factory/GolfCut/production/tracer-daily`.
This adds pages to `diifan/golfcut-website` and its existing `golfcut-website` Vercel project. It never creates a site/project, resets the inference worktree, changes DNS, or alters another app.

## Controller contract

Only mutable operator config: `/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily-golfcut/config.json`.
Fields: enabled, target, hour, minute, prepare_hour, prepare_minute, timezone.
The timer ticks every minute; Python reads the config at each invocation. All publication and preparation dates use the configured zone. The prepare time prepares the **next** calendar day's batch. At publication time only a ready, validated deployment is promoted; no new build is started by the publish action. Target changes invalidate a prepared batch for publication. Disabled means no publication or preparation.

Same directory holds `state.json` (heartbeat and runs), `<day>-receipt.json`, append-only `keywords.json`, `source-manifest.json`, and cached evidence. The original short-term report is synchronized at `reports/seo-expansion-20261124/golfcut-{receipt.json,progress.md}`. Page generation and live verification update every 50 pages. The controller owns MAC UI/API integration.

## Sources and editorial meaning

GolfCut started a new pool. `source_cache.py` reads the public PGA TOUR watch catalog using the same public read-only operation as its website. No paid Semrush requests, cookies, user keys, or subscription changes. Current entries are refreshed; a persisted archive cursor continues older collection. Cached pages expire after six hours. Each catalog response provides exact public video URLs and source metadata. Four collection threads, bounded retries, append-only normalized title/video-ID deduplication; reserved/published rows remain untouched. Raw unrelated NCSA exports are discovery-only and never enter this pool.

Candidates are real tee, approach, bunker and chip references, excluding putts, interviews and recap compilations. These are **source-derived topic candidates**, not claims of measured keyword volume. Each page is a source-linked recording worksheet: factual player/round/hole metadata, shot-specific filming guidance, interactive observation notes and the actual GolfCut trial limits. It explicitly does not claim visual analysis of the reference or editing the broadcast. No videos or copyrighted descriptions are republished. No affiliation or player endorsement is implied.

A finite archive cannot guarantee 2,000 new worthwhile topics forever. When candidates are exhausted or sources fail, report `insufficient_candidates` or source failures separately; never synthesize permutations or republish old candidates to meet a number.

## Execution

```
python3 production/tracer-daily/source_cache.py YYYY-MM-DD
python3 production/tracer-daily/prepare.py --day YYYY-MM-DD
python3 production/tracer-daily/release.py stage --day YYYY-MM-DD
python3 production/tracer-daily/release.py publish --day YYYY-MM-DD
python3 production/tracer-daily/scheduler.py
python3 production/tracer-daily/test_executor.py
```

`--immediate` on publish is for the explicitly authorized first-day release only, not ordinary scheduled operation. `--no-refresh` on prepare reuses the actual pool for recovery.

Preparation uses an isolated detached worktree from protected `website-tracer` origin/main. It reserves source IDs, renders pages and paginated hubs, adds one related link to the existing tracer article, updates the flat sitemap, runs the existing Bun SEO/build checks, then commits. Home page, branding, 25 styles, APIs and legal files remain unchanged.

Staging reuses the existing Vercel project, production environment, with `--skip-domain`. It reconciles uncertain uploads using unique batch/commit metadata before retrying. Publishing verifies immutable page/manifest hashes, target, main baseline, deployment identity and READY state before promotion. It then checks the live alias, every batch sitemap URL and every live page hash; only afterwards fast-forwards Git main and marks pool rows published. Git's subsequent integration build can create an equivalent deployment with the same commit; compare commit and content, not only deployment ID.

The scheduler checks ready baselines every 15 minutes outside the publish minute. Clean isolated rebases are rebuilt and restaged; conflicts are aborted and explicitly recorded, never overwritten. Transient failures retry with a 15-minute cooldown. An executor-wide flock prevents overlap. Source limits and content failures do not trigger partial publication.

## Operations

`golfcut-seo-daily.timer` invokes the sole executor. Read `systemctl status golfcut-seo-daily.timer`, `systemctl show golfcut-seo-daily.service -p Result -p ExecMainStatus`, and journal logs. Unit templates are in `systemd/`. Credentials are inherited from the existing restricted CLI login and never enter receipts or source control. Use verified 112:7890; source collection checks fallback 110:10808. Publication errors are recorded for retry; no group notifications are sent.
