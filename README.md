# Intelligent Traffic Tracking

Traffic video analysis with object detection, multi-object tracking, auditable
line crossing counts, zone analytics, and reproducible scientific evaluation.

**Status:** Waves 0–1 implemented: foundation and local video CLI.

The foundation includes an independent Python package, validated data contracts,
an empty model catalog, FastAPI liveness, and a Next.js shell with API status.
The video extra adds PyAV/FFmpeg decoding and H.264 export, OpenCV preview,
metadata, original frame timestamps, and temporal selection. YOLO, ByteTrack,
SQLite jobs, and analytics arrive in later waves. No HTTP upload, inference,
worker, or database is implemented yet.

## Requirements

- [uv 0.13.1](https://docs.astral.sh/uv/getting-started/installation/) for Python
  environments and the committed lockfile. It provisions Python 3.12 if needed.
- Node.js 24 and npm. `frontend/.nvmrc` records the Node major version.
- No GPU or model weights needed. The video extra uses FFmpeg libraries through
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
even dimensions and drops audio. It performs no detection or annotation yet.

PTS is required by default, including for VFR. Use `--cfr-fallback-fps 25` only
when asserting that the entire source is CFR: it overrides all timestamps and
records the fallback. A reported average FPS does not justify treating VFR as CFR.
Selection is `[start_s, end_s)` in original stream-relative time; exported time
starts at zero, with its final frame duration clamped to the requested end.
Failures retain `.partial` files and `failure.json`; they never produce a completed
summary. CLI returns JSON, exit 2 on expected error and 130 on interruption.

Data provenance, planned scenes and annotation gates: [datasets](docs/datasets.md).

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
the frontend checks without GPUs or model/data downloads.

To install only the independent core, use `uv sync --locked --no-default-groups`
(this removes API/development extras from that environment). To restore the
development environment, run `uv sync --locked --extra api --extra video` again.

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
- [Current workboard](docs/agentic/workboard.md)
- [Implementation task cards](docs/agentic/tasks/README.md)

Planning documentation is in Portuguese. Code, API, CLI, and UI use English.

## Next implementation step

Continue with [Wave 2 — YOLO detector and baseline](docs/agentic/tasks/wave-2-detection.md).
The delivery order is Python core, scientific evaluation, then web.
