# GolfCut controller handoff — implemented contract

Controller-owned inputs (read-only):
- `/data/swi-algo/Swi-App-Factory/GolfCut/production/keyword-expansion/keywords.csv`
- same directory `manifest.json`, `config.json`, original CSV exports and `run.lock`.

CSV: `keyword,status,url,batch_id,source,volume,kd,evidence_url,metric_timestamp,source_sha256`.
Manifest `sources`: `path,sha256,rows`. Each preparation reads the current CSV/manifest and all referenced export hashes under a shared producer lock, then rechecks stability after evidence collection. No initial hash is pinned. Every accepted keyword/KD/volume/evidence_url tuple must exist in its original CSV export; a valid file hash alone cannot authenticate a forged row. Strict thresholds: `0 <= KD < 30`, `volume > 100`.

Use `evidence_url` to fetch, not `source` or `url`. Source is the immutable original export. Only HTTPS on domains registered in controller `config.json` (and their www variants) is allowed, with public DNS, no credentials/unusual ports, checked redirects, maximum five redirects and 2 MB decompressed response. Eight bounded fetch workers and cached errors prevent repeated pressure. Source/title/keyword intent and golf relevance are checked before capacity is counted. Equivalent normalized intents and source paths are deduplicated.

Own state: `/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily-golfcut/semrush-keyword-state.json` and `keyword-pool.lock`. Imports preserve published/reserved status; no producer CSV or manifest writes. The only permitted output inside the controller directory is `capacity.json` with Unix `checked_at` and verified unoccupied `eligible_available`.

`input-binding.json` binds paths; it is not a duplicate schedule. All mutable schedule/target settings remain in `config.json`. Empty/short pools produce `insufficient_keywords`, with `source_state=source_quota_blocked` when the producer reports report limits. They never generate, stage or publish a partial batch. The executor does not call Semrush or force retries; the producer owns its six-hour cooldown.

`keyword_pages.py` now renders actual accepted keywords into `/golf-guides`, paginated indexes, source references, recording worksheets and existing tracer links; runs the original Bun build; and commits in an isolated keyword worktree. `release.py` stages only exact validated Semrush batches to the original project, checks main and identity, then promotes and verifies sitemap/HTML before marking published. Existing worker, API, brand, privacy and legacy pages stay intact.

Fixtures live exclusively under `/tmp/golfcut-semrush-TEST-FIXTURE-*`. They carry fixture flags and visible HTML markers. Stage/publish reject them before network operations. The release-flow test separately mocks all Git/Vercel/HTTP transports; mocked publication is not a real deployment. See `semrush-fixture-build-result.json` and tests.

Historical state: 2,000 video-reference pages were already published before the correction and remain preserved. The unpublished 2,000-page next-day video batch is sealed. No additional video-title batch may publish.
