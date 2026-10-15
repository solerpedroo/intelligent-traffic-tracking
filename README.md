# Intelligent Traffic Tracking

Traffic video analysis with object detection, multi-object tracking, auditable
line crossing counts, zone analytics, and reproducible scientific evaluation.

**Status:** Wave 0 foundation implemented. Video processing starts in Wave 1.

The foundation includes an independent Python package, validated data contracts,
an empty model catalog, FastAPI liveness, and a Next.js shell with API status.
YOLO, ByteTrack, OpenCV/FFmpeg, SQLite jobs, and analytics arrive in later waves.
No video upload, inference, worker, or database is implemented yet.

## Requirements

- [uv 0.13.1](https://docs.astral.sh/uv/getting-started/installation/) for Python
  environments and the committed lockfile. It provisions Python 3.12 if needed.
- Node.js 24 and npm. `frontend/.nvmrc` records the Node major version.
- No GPU, model weights, datasets, or FFmpeg needed for Wave 0.

The foundation is tested on Python 3.12 and 3.14. Compatibility of future model
libraries will be validated separately; Python 3.12 is the development baseline.

## Quick start

From the repository root:

```bash
uv sync --locked --extra api
cp .env.example .env

# Terminal 1 — API
uv run --locked --extra api uvicorn backend.app.main:app \
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

## Quality checks

After `uv sync --locked --extra api`:

```bash
.venv/bin/ruff check vision backend
.venv/bin/ruff format --check vision backend
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
development environment, run `uv sync --locked --extra api` again.

## Project documentation

- [Project scope](docs/project-scope.md)
- [Scope analysis and development pillars](docs/scope-analysis.md)
- [Implementation plan: waves 0–12](docs/implementation-plan.md)
- [Cursor and Codex entrypoint](AGENTS.md)
- [Development playbook](docs/agent-playbook.md)
- [Architecture decisions](docs/agentic/architecture-decisions.md)
- [Implemented architecture](docs/architecture.md)
- [Current API contract](docs/api-contract.md)
- [Current workboard](docs/agentic/workboard.md)
- [Implementation task cards](docs/agentic/tasks/README.md)

Planning documentation is in Portuguese. Code, API, CLI, and UI use English.

## Next implementation step

Continue with [Wave 1 — Video, timestamps, CLI, and data](docs/agentic/tasks/wave-1-video-cli.md).
The delivery order is Python core, scientific evaluation, then web.
