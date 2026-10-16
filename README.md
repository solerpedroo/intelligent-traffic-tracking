# Intelligent Traffic Tracking

Traffic video analysis with object detection, multi-object tracking, auditable
line crossing counts, zone analytics, and reproducible scientific evaluation.

**Status:** Waves 0–9 implemented. Jobs are queued in SQLite and run by a separate worker process.

The foundation includes an independent Python package, validated data contracts,
a versioned model catalog, FastAPI liveness, and a Next.js shell with API status.
The video extra adds PyAV/FFmpeg decoding and H.264 export, OpenCV preview,
metadata, original frame timestamps, and temporal selection. The detector extra
adds YOLO11n and ByteTrack with CPU inference, IDs, trajectories, and annotated
exports. Finite line counting adds directional events and media-time aggregates.
ROI visits and observed dwell stream to CSV; class/window heatmaps export raw
counts and smoothed previews. SQLite jobs and web analytics arrive in later waves. No HTTP upload,
worker, or database is implemented yet.

## Requirements

- [uv 0.13.1](https://docs.astral.sh/uv/getting-started/installation/) for Python
  environments and the committed lockfile. It provisions Python 3.12 if needed.
- Node.js 24 and npm. `frontend/.nvmrc` records the Node major version.
- GPU is not required. Video-only mode needs no model weights; detection requires
  an explicitly prepared checkpoint. The video extra uses FFmpeg libraries through
  PyAV; system `ffmpeg`/`ffprobe` executables are optional.

The foundation is tested on Python 3.12 and 3.14. Compatibility of future model
libraries will be validated separately; Python 3.12 is the development baseline.

## Quick start

From the repository root:

```bash
uv sync --locked --extra api --extra video
cp .env.example .env

# Terminal 1 — API
uv run --locked --extra api --extra video uvicorn backend.app.main:app \
  --reload --host 127.0.0.1 --port 8000 --env-file .env
```

In another terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

In a third terminal, after at least one job exists:

```bash
uv run --locked --extra api --extra video python -m backend.app.worker
```

The API returns 202 and does not run the video pipeline. The worker claims one
job at a time from SQLite. See [the API contract](docs/api-contract.md).

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). The shell displays API
availability; it remains usable when the API is offline. Check liveness directly
at [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) and the
schema at [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json).

`TRAFFIC_ALLOWED_ORIGINS` is a JSON array. `NEXT_PUBLIC_API_URL` is a public
HTTP(S) origin embedded at build time; rebuild after changing it. Settings and
local files are explained in [architecture](docs/architecture.md).

## Local video CLI

Generate original synthetic samples without downloading data:

```bash
uv run --locked --extra api --extra video python scripts/generate_sample.py data/sample.mp4
uv run --locked --extra api --extra video python scripts/generate_sample.py data/sample-vfr.mp4 --profile vfr
```

Inspect capabilities and metadata, then export a selected interval:

```bash
.venv/bin/traffic-video capabilities
.venv/bin/traffic-video probe data/sample-vfr.mp4
.venv/bin/traffic-video process data/sample-vfr.mp4 \
  --output-dir artifacts/sample-vfr --video-id sample-vfr --start-s 0.12 --end-s 0.61
```

The output directory must be new. Results: `video.mp4`, `preview.png`,
`frames.csv`, `metadata.json`, `config.json`, and `summary.json`. The preview
shows original frame 0; the selected video starts at its first selected frame.
CSV retains original frame indices/timestamps and their exported counterparts.
H.264 is lossy; the PNG preview retains the decoded BGR frame exactly.

Input: local MP4, one video stream, square pixels and no rotation. Default limits:
512 MiB, 300 seconds, 1920×1080 pixels per frame, and 36,000 frames. Override with
`--limits examples/video-limits.json` (edit a local copy). Video export requires
even dimensions and drops audio. Copy-only mode performs no inference; select
`--model` to enable detection.

PTS is required by default, including for VFR. Use `--cfr-fallback-fps 25` only
when asserting that the entire source is CFR: it overrides all timestamps and
records the fallback. A reported average FPS does not justify treating VFR as CFR.
Selection is `[start_s, end_s)` in original stream-relative time; exported time
starts at zero, with its final frame duration clamped to the requested end.
Failures retain `.partial` files and `failure.json`; they never produce a completed
summary. CLI returns JSON, exit 2 on expected error and 130 on interruption.

Data provenance, planned scenes and annotation gates: [datasets](docs/datasets.md).

## YOLO detection (Wave 2)

Install the optional CPU stack and explicitly prepare verified official weights:

```bash
uv sync --locked --extra api --extra video --extra detector
.venv/bin/traffic-video models
.venv/bin/traffic-video prepare-model yolo11n-coco --directory checkpoints
.venv/bin/traffic-video process data/sample-vfr.mp4 \
  --output-dir artifacts/yolo-sample --model yolo11n-coco \
  --checkpoint checkpoints/yolo11n.pt --device cpu --image-size 640 \
  --classes person bicycle car motorcycle bus truck
```

The synthetic sample may produce no detections; a valid empty result is expected.
To run an explicit positive smoke with an official example image:

```bash
.venv/bin/python scripts/smoke_detector.py --checkpoint checkpoints/yolo11n.pt \
  --output-dir artifacts/yolo-cpu-smoke --download-example
.venv/bin/pytest -m detector
```

The smoke downloads an explicitly requested pinned image and repeats it in a short
video. It proves integration and supplies no traffic accuracy benchmark. Use
`--image /path/to/authorized-image.jpg` instead to supply your own image.
Real tests expect the official example (override `TRAFFIC_TEST_IMAGE` and
`TRAFFIC_TEST_CHECKPOINT` paths if needed); missing assets fail rather than skip.

Detection runs additionally export `detections.csv`, `timings.csv`, and
`manifest.json`. Boxes are in original pixels. Counts in the summary represent
box observations across frames, not unique vehicles or crossings. The original
preview remains unannotated; boxes/scores are drawn on the exported video.
`--confidence` controls retained detections; `--visualization-confidence` only
controls drawing. Lower-confidence detections remain available for future tracking.

Inference operates offline after preparation; checkpoint hash and full class map
are verified. CPU wheels are selected by the committed uv configuration. CUDA
requires a compatible separately validated build; this CPU lock does not install
CUDA libraries. See [model provenance and methodology](docs/model-inventory.md)
for versions, licensing sources, coordinate conversion and timing definitions.

## Quality checks

After `uv sync --locked --extra api --extra video`:

```bash
.venv/bin/ruff check vision backend scripts
.venv/bin/ruff format --check vision backend scripts
.venv/bin/pytest
uv build
```

For the frontend:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
```

`npm run format` applies Biome formatting and safe fixes. `typecheck` generates
Next.js route types before running TypeScript, so it works on a clean checkout.
The production shell can be served with `npm run start` after a build.
GitHub Actions runs Python 3.12/3.14, an isolated installed-package check, and
the frontend checks without GPUs or model/data downloads. Model integration
tests are deselected in the default lightweight run; select `-m detector`
explicitly after preparing assets. A manual workflow_dispatch option enables
the separate CPU smoke job with explicit downloads.

To install only the independent core, use `uv sync --locked --no-default-groups`
(this removes API/development extras from that environment). To restore the
development environment, run `uv sync --locked --extra api --extra video` again.
Include `--extra detector` whenever synchronizing an environment that needs YOLO.

## Project documentation

- [Project scope](docs/project-scope.md)
- [Scope analysis and development pillars](docs/scope-analysis.md)
- [Implementation plan: waves 0–12](docs/implementation-plan.md)
- [Cursor and Codex entrypoint](AGENTS.md)
- [Development playbook](docs/agent-playbook.md)
- [Architecture decisions](docs/agentic/architecture-decisions.md)
- [Implemented architecture](docs/architecture.md)
- [Current API contract](docs/api-contract.md)
- [Video data and annotation plan](docs/datasets.md)
- [Model inventory and detection methodology](docs/model-inventory.md)
- [Current workboard](docs/agentic/workboard.md)
- [Implementation task cards](docs/agentic/tasks/README.md)

Planning documentation is in Portuguese. Code, API, CLI, and UI use English.

## Next implementation step

Continue with [Wave 6 — Exports and core integrity](docs/agentic/tasks/wave-6-exports.md).
The delivery order is Python core, scientific evaluation, then web.


## ByteTrack tracking (Wave 3)

After installing the detector extra and preparing the local checkpoint:

```bash
.venv/bin/traffic-video process input.mp4 --model yolo11n-coco \
  --checkpoint checkpoints/yolo11n.pt --tracker bytetrack-default \
  --output-dir artifacts/tracking-run
.venv/bin/pytest -m 'tracker or detector'
```

Optional `--tracker-config params.json` merges validated overrides with the catalog
preset. Outputs add tracks.csv (observed/lost states), trajectories.csv (observed
bottom centers), and track-lifetimes.csv (observed spans and analysis eligibility).
IDs reset per run; histories are bounded, complete observations stream to disk.
Buffer is measured in processed frames, including empty frames. Class is fixed
at the first detection per ID; association remains class agnostic.
See [tracking contracts, limits, and smoke commands](docs/tracking.md).


## Line counting (Wave 4)

```bash
.venv/bin/traffic-video process input.mp4 --model yolo11n-coco \
  --checkpoint checkpoints/yolo11n.pt --tracker bytetrack-default \
  --counting-config examples/counting/lines.json --output-dir artifacts/counting-run
.venv/bin/python scripts/smoke_counting.py --source data/vehicles.mp4 \
  --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/counting-smoke
```

Normalized finite lines, perpendicular hysteresis, stable sides, minimum track
observations, and explicit frame/time gaps govern crossing. Events count once
per run/line/ID/direction and export to crossing_events.csv; media-time windows
to crossing_windows.csv. The video displays oriented lines and directional totals.
See [counting contracts and explicit example preparation](docs/counting.md).
The small real traffic check is a development sanity check with visual labels,
not an independent benchmark. ROI and heatmaps are implemented in Wave 5.


## ROI and observation heatmaps (Wave 5)

```bash
.venv/bin/traffic-video process input.mp4 --model yolo11n-coco \
  --checkpoint checkpoints/yolo11n.pt --tracker bytetrack-default \
  --analytics-config examples/analytics/zones.json --output-dir artifacts/analytics-run
.venv/bin/python scripts/smoke_analytics.py --source data/vehicles.mp4 \
  --checkpoint checkpoints/yolo11n.pt --output-dir artifacts/analytics-smoke
```

Normalized simple polygons include their boundaries. Occupancy counts observed
IDs; visits distinguish geometric exit, observation loss, and censored boundaries.
Dwell sums only consecutive inside observations in original media time. CSV exports
include zone_events, zone_visits, zone_occupancy, and a heatmap_index referencing
raw/smoothed NPZ arrays and PNG previews per class/window. State and current grids
are bounded; trajectories remain streamed to disk.

See [ROI/heatmap configuration, units, and limits](docs/zones-heatmaps.md).
Visits are not unique physical vehicles; observation heatmaps are not physical
density or unique passages. Missing observations do not extend measured dwell.

## Reproducible exports (Wave 6)

```bash
.venv/bin/traffic-video process input.mp4 --output-dir artifacts/numeric \
  --no-annotated-video
```

Successful runs publish `config.json`, `manifest.json`, and `summary.json` with
schema `1.0`, plus the CSV tables that apply to the selected stages. Column order
and units live in `vision/pipeline/schemas.py`. `--no-annotated-video` skips the
MP4 and records `annotated_video_skipped`; counts, visits, and heatmap arrays
remain valid. An encoder or overlay failure does not delete those numeric files.
A decode, model, or table-write failure publishes `failure.json` instead of a
successful summary. Reload the resolved config with the JSON stored in
`config.json`. See [examples/sample_results/README.md](examples/sample_results/README.md).

## Evaluation (Wave 7)

```bash
uv sync --locked --extra api --extra video --extra evaluation
.venv/bin/python scripts/evaluate.py --help
```

Detection mAP, crossing events, and timing summaries are separate from HOTA/IDF1/MOTA.
TrackEval runs only when identity ground truth and the `evaluation` extra are present.
The frozen test sequence is `MOT15-PETS09-S2L1`. Other sequences exit 2 unless
`--allow-development` is set, and that report is not the benchmark.
See [evaluation](docs/evaluation.md) and [methodology](docs/methodology.md).
