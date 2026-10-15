# Intelligent Traffic Tracking

Traffic video analysis with object detection, multi-object tracking, auditable
line crossing counts, zone analytics, and reproducible scientific evaluation.

**Status:** planning. No application code or implementation wave is complete.

Planned stack: Python, YOLO, ByteTrack, OpenCV/FFmpeg, FastAPI, SQLite, and
Next.js with TypeScript. Local CPU execution comes first; GPU is optional.

## Project documentation

- [Project scope](docs/project-scope.md)
- [Scope analysis and development pillars](docs/scope-analysis.md)
- [Implementation plan: waves 0–12](docs/implementation-plan.md)
- [Cursor and Codex entrypoint](AGENTS.md)
- [Development playbook](docs/agent-playbook.md)
- [Architecture decisions](docs/agentic/architecture-decisions.md)
- [Current workboard](docs/agentic/workboard.md)
- [Implementation task cards](docs/agentic/tasks/README.md)

Planning documentation is in Portuguese. Code, API, CLI, and UI use English.

## Next implementation step

Start [Wave 0 — Foundation](docs/agentic/tasks/wave-0-foundation.md).
Installation commands and quality checks will be established and verified in
that wave. The delivery order is Python core, scientific evaluation, then web.
