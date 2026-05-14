# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

SCP-cv is a Windows-first, single-host playback control platform for the Shanghai Polytechnic University 28#108 multimedia display system. It coordinates a Vue control console, Django REST/SSE/gRPC services, MediaMTX SRT streaming, and a PySide6/libVLC/PowerPoint player to control four output windows: big screen left/right and TV left/right.

## Required environment

- Windows 10/11 is the target runtime environment.
- Python 3.12+ is managed with `uv`; do not reintroduce `requirements*.txt`.
- Node.js 20+ is used for the Vue/Vite frontend.
- Microsoft PowerPoint is required for PPT playback.
- Runtime assets are expected at `tools/third_party/mediamtx/mediamtx.exe` and `tools/third_party/vlc/runtime/`; system VLC at `C:\Program Files\VideoLAN\VLC` is a fallback.

## Common commands

Setup:

```powershell
uv python install
uv sync
npm ci --prefix frontend
copy .env.example .env
copy frontend\.env.example frontend\.env
uv run python manage.py migrate
```

Run the full local stack:

```powershell
uv run python manage.py runall
uv run python manage.py runall --backend-host 0.0.0.0 --frontend-host 0.0.0.0
uv run python manage.py runall --skip-mediamtx
uv run python manage.py runall --skip-player
uv run python manage.py runall --skip-frontend
uv run python manage.py runall --headless
uv run python manage.py runall --headless --service
uv run python manage.py runall --headless --window1 1 --window2 2 --window3 3 --window4 4 --gpu 0
```

Run services separately for debugging:

```powershell
uv run python manage.py runserver
npm --prefix frontend run dev
uv run python manage.py run_player
uv run python manage.py run_player --headless --window1 1 --window2 2 --window3 3 --window4 4
.\tools\third_party\mediamtx\mediamtx.exe .\tools\third_party\mediamtx\mediamtx.yml
```

Validation:

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest tests/ -v
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Targeted tests:

```powershell
uv run pytest tests/test_runall_command.py -v
uv run pytest tests/test_playback_service.py -v
uv run pytest tests/test_rest_api.py -v
uv run pytest tests/test_grpc_servicers.py -v
uv run pytest tests/test_player_controller.py -v
uv run pytest tests/test_mediamtx_service.py -v
uv run pytest tests/test_ppt_adapter.py -v
uv run pytest tests/test_srt_stream_adapter.py -v
uv run pytest tests/test_volume_service.py -v
uv run pytest tests/test_device_service.py -v
uv run pytest tests/test_playback_service.py::TestOpenSource::test_open_existing_source -v
```

Frontend commands can also be run through root npm aliases:

```powershell
npm run frontend:dev
npm run frontend:typecheck
npm run frontend:build
```

## Architecture map

- `scp_cv/settings.py` configures Django, SQLite, logging, REST framework, django-socio-grpc, MediaMTX ports, and local static/media serving.
- `scp_cv/urls.py` mounts `admin/`, REST APIs under `api/`, dashboard pages, and local static/media file serving.
- `scp_cv/apps/dashboard/api_urls.py` is the REST API route table used by the Vue console.
- `scp_cv/apps/playback/models/` contains the playback domain models: media folders/sources/resources, sessions, runtime state, devices, scenarios, and enum constants.
- `scp_cv/services/` holds most business logic. Prefer adding backend behavior there instead of putting complex logic in Django views.
- `scp_cv/player/` is the PySide6 player. `controller.py` polls `PlaybackSession.pending_command`, dispatches work to the Qt main thread, and writes adapter state back to the database.
- `scp_cv/player/adapters/` contains source-specific playback adapters for images, video, streams, web, PPT-related paths, and shared adapter behavior.
- `scp_cv/apps/dashboard/management/commands/runall.py` orchestrates MediaMTX, gRPC-Web proxy, Django, Vite, and the PySide6 player. Related helpers live in `scp_cv/apps/dashboard/management/runall_*` modules.
- `protos/scp_cv/v1/control.proto` is the gRPC contract; generated Python code lives under `scp_cv/grpc_generated/` and compatibility stubs also exist under `scp_cv/v1/`.
- `frontend/src/services/api.ts` centralizes frontend REST types and request helpers.
- `frontend/src/stores/` contains Pinia stores for runtime, devices, displays, sessions, sources, and scenarios.
- `frontend/src/features/` contains page-level feature modules; `frontend/src/design-system/` contains reusable Fluent-style UI components; `frontend/src/styles/tokens.css` defines shared visual tokens.
- `tests/` contains pytest coverage for backend services, REST/gRPC APIs, player controller behavior, runall orchestration, MediaMTX, PPT, SRT, devices, volume, migrations, and middleware.

## Core control flow

The Vue frontend calls Django REST endpoints and listens to SSE updates. Backend services update SQLite-backed `PlaybackSession` rows, including `pending_command` and `command_args`. The PySide6 player polls those session rows, runs the command in the Qt main thread through the relevant source adapter, then writes playback state, position, duration, slide index, error details, mute, and volume back to the database. gRPC servicers expose compatibility automation around the same service layer.

## Configuration and ports

- Root `.env` is for Django, gRPC, MediaMTX, logging, and backend runtime configuration.
- `frontend/.env` is for Vite, especially `VITE_FRONTEND_PORT` and `VITE_BACKEND_TARGET`.
- `runall` clears inherited `VITE_*` variables before launching Vite. `frontend/.env` is the frontend source of truth; `runall` injects a backend target only when the frontend env file does not define one.
- Default ports: Vue `5173`, Django REST/admin/media `8000`, gRPC `50051`, MediaMTX SRT `8890`, MediaMTX API `9997`.

## Development rules from repository docs

- Follow `AGENTS.md`, `CONTRIBUTING.md`, and `STYLE.md`; they are authoritative for workflow, commit format, documentation sync, and style.
- Commit messages use `type(scope): 中文摘要` with types such as `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `perf`, `build`, `ci`, `chore`, and `revert`.
- Keep changes small and reviewable. Do not mix formatting, dependency updates, business fixes, and documentation rewrites in one change.
- Do not run `git push`, switch branches, create branches, open PRs, or rewrite remote history unless the user explicitly asks.
- Single files over 500 lines should be split where practical instead of continuing to accumulate implementation.
- Python code should use type annotations and explicit return types. New or edited Python files in this repo commonly use the project file header and reStructuredText-style function docstrings.
- Vue components should keep API types in services/stores, state in Pinia stores, and components focused on display and local interaction.
- CSS should use `frontend/src/styles/tokens.css`; avoid one-off hard-coded colors, shadows, and radii in business components.
- For API, config, route, platform, data-structure, deployment, or user-visible behavior changes, update the relevant docs under `docs/`, plus `README.md`, `STYLE.md`, or `docs/CHANGELOG.md` when applicable.

## Files and data not to commit

Do not commit `.env`, `frontend/.env`, `.claude/`, `.oms/`, `.playwright-cli/`, `.playwright-mcp/`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, uploaded media, generated logs, temporary test scripts, or `requirements*.txt`. Dependencies are tracked through `uv.lock`, root `package-lock.json` when needed, and `frontend/package-lock.json`.
