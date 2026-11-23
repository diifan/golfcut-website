# GolfCut website tracer on 112

Live entry: https://golfcut.goswie.com/try-tracer

## Request path
Browser → same-origin Vercel `/api/tracer` → Supabase function `golfcut-web-tracer` → private job queue → 112 `golfcut-web-tracer.service` → private signed result.
The worker calls `/api/tracer-worker` on the app domain; artifact transfer uses temporary Supabase storage URLs. No inbound 112 port is exposed. Both bridges use the existing AceCut Supabase project but separate app tables, buckets and credentials. Native analytics tables are unchanged.

## Limits and access
512 MB upload, 10-minute source, selected clip at most 30 seconds. One worker per app, 900-second processing deadline, 8 GB memory cap. Per-app capacity: 20 unexpired tasks / 2 GB sources; 6 creates per keyed IP per hour. Jobs expire after 24 hours; worker cleanup runs every 5 minutes. Capability IDs and signed URLs are private; do not put them in logs or public reports. The browser keeps the capability in sessionStorage and reconnects after refresh. Cancellation invalidates the worker lease. Incomplete uploads can be retried.

Vercel production secret: `WEB_TRACER_SECRET` (encrypted). Worker configuration: `/var/lib/swi-codex/.local/state/web-tracer/golfcut.json` (0600), with app, root, endpoint, worker_key, web_key. Do not copy credentials into the repo. Supabase migrations/functions: `bridge/`; worker and web secrets are separate. API authenticates worker credentials in the cloud bridge, origin-checks browser calls, and derives rate keys only from Vercel's trusted ingress IP.

## Deployment
Website: `bun install --frozen-lockfile && bun run build`, then existing Vercel project `golfcut-website`, scope `diifans-projects`. Keep `bun.lock` and the Node type dev dependency: an empty dependency graph caused the cloud function builder to fall back to unavailable npm. No global tools or other app deployments need changing.

112 Python: `/data/envs/torch-cu130/bin/python`; service WorkingDirectory is this directory. Requires ffmpeg/ffprobe, OpenCV, NumPy, ONNX Runtime. Video and compute thread counts are bounded. Environment `WEB_TRACER_CONFIG` points to the private config. Task-scoped egress proxy is `http://127.0.0.1:18199`; do not replace company/global routes. `systemctl status golfcut-web-tracer` checks the service; restart after changing worker.py. Model subprocesses receive only approved runtime variables, no worker secrets.

Runtime files: `/var/lib/swi-codex/web-tracer/golfcut/<private-job-id>`. `observations.json` records measured points; `result.json` records artifact SHA/size. Do not publish raw job directories. Local and cloud cleanup remove expired footage. On a failed render, inspect inference.log locally, then retry the user's task; do not report queue acceptance as a finished video.

## Validation (2026-11-24)
Real public API create/upload/probe/process/status/download passed against 112, with MP4 downloaded and decoded. Unauthorized origins, malformed IDs, invalid actions, forged worker credentials, cross-app task access and cancellation were tested. Responsive layout checked at 1440/768/390/320 pixels. Local evidence stays in `/tmp/web-tracer-validation` (private task IDs omitted from committed report).

## Experience limitations
This is an online trial, not a claim of native-app parity or a broad accuracy benchmark. Only detected points are rendered; unreliable clips return no trajectory. No generated landing path or distance is added. Use steady, well-lit footage with a visible ball. A short clip is best; tennis processing is slower than golf and can take minutes.

### GolfCut models
Original native `/Users/soda/Swi-app/Models/TrackNet.mlpackage` on 109, compiled with CoreML then converted using the existing model recovery ONNX converter. On 112: `/var/lib/swi-codex/web-tracer/models/GolfCut-TrackNet.onnx`; override with `GOLFCUT_TRACKNET`. Runtime uses TrackNet and `golf_chains.select_device`, ported from native chain regression logic. `golf.py`/`golf_detector.py` are comparison adapters, not active runtime detectors. Existing swing/pose preview service is untouched.

User must mark ball position at impact. Model runs near impact (up to ~1.5 seconds after impact), renders only reliable visible flight. An 8-frame ONNX/CoreML comparison had mean absolute heatmap difference 0.000096236 and maximum 0.0372063 (FP16/FP32 conversion); not bit-exact. Real down-the-line fixture passed with 12 observed points; late/incorrect impact selection can correctly reject a clip.
