# HuskyHacks Backend

Boilerplate Python API for the web dashboard and Chrome extension.

## Setup

Install or select Python 3.12, then create the virtual environment with `uv`:

```powershell
cd backend
uv python install 3.12
uv venv --python 3.12
uv sync
```

The backend currently targets Python 3.12 because the pinned FastAPI/Pydantic versions can fail to build under Python 3.13.

Optional activation:

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Bash on macOS/Linux:

```bash
source .venv/bin/activate
```

Bash on Windows:

```bash
source .venv/Scripts/activate
```

## Run

Without activating the environment:

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If the environment is already activated:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Health Check

```txt
GET http://127.0.0.1:8000/health
```
