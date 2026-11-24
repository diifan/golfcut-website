# Controller Semrush handoff (2026-11-24 correction)

Controller owns `production/keyword-expansion`; executor never writes there.
Supply two absolute paths: `keywords.csv` and `source-manifest.json`. Bind them in:
`/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily-golfcut/input-binding.json`

```json
{"keywords_csv":"/absolute/path/keywords.csv","source_manifest":"/absolute/path/source-manifest.json"}
```

This is an input-path binding, not a second schedule configuration. Daily mutable settings remain exclusively in `config.json`.

CSV required fields: `keyword,kd,volume,source_url` (aliases `Keyword,Keyword Difficulty,Search Volume,URL` supported; `url` accepted). Metrics must be numeric. Accept only **0 <= KD < 30 and volume > 100**. Exactly 30 or 100 fail. No fabricated metrics, blank metrics, video titles masquerading as keyword research, or basketball substitutions.

Manifest contract:
```json
{
  "keywords_sha256":"SHA256 of keywords.csv",
  "sources":[{"provider":"semrush","local_path":"/original/export.csv","sha256":"SHA256 of export","database":"us","exported_at":"ISO date"}],
  "evidence":{
    "normalized keyword":{
      "url":"https://the-corresponding-ranking-source/page",
      "title":"Fetched source title",
      "text":"Fetched source text (at least 200 characters)",
      "sport":"golf",
      "tracer_relevance":"Specific relationship between the keyword intent, source and usable golf video/tracer workflow"
    }
  }
}
```
Evidence may instead be a list of records carrying `keyword`, or an external JSON specified by `evidence_file` and `evidence_sha256`. If controller already has another schema, provide a real sample and this executor adapter will map it; do not duplicate or modify the source exports to fit this proposal. Source hashes, keyword metrics and evidence references must remain traceable.

The executor normalizes NFKC/whitespace/case; preserves prior Semrush published/reserved states in `semrush-keyword-state.json`; excludes historical video identities without changing their states; checks metric thresholds, source hash integrity, URL consistency, golf relevance and keyword/evidence alignment. Missing evidence is counted separately from threshold failures and duplicates. Import result is `input-import-receipt.json`.

Current release status:
- 2026-11-24: 2,000 video-reference pages already published before correction; preserve them and their original receipts/pool states.
- 2026-11-25: 2,000 video-reference pages built/staged but **not promoted**; preserved under `2026-11-25-video-batch-preserved.json`. New policy blocks staging/promotion of this input kind, including manual release commands.
- Future accepted input must be `semrush_keywords_v1`. The first real CSV/evidence sample is needed to complete source-specific page-writer integration and verify it. Import validation is executable now; it is not a claim that a Semrush batch has been generated or published.

There is no video fallback. Do not promote legacy prebuilt versions to meet a quota. Keep existing domain/project, homepage, 25 styles, worker/API and privacy unchanged.
