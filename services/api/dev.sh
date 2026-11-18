#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec uv run uvicorn --app-dir src devflow_rag.main:app --reload --host 127.0.0.1 --port 8000
