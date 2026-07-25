#!/usr/bin/env bash
# Build the venv the MCP server is launched from, if it isn't there yet.
#
# Claude Code on the web clones this repo into a fresh container each session,
# so .venv never survives. Without this, .mcp.json points at a binary that does
# not exist and the trainingpeaks server fails to start with no clear reason.
#
# Local machines already have a .venv from the README setup, so this is a no-op
# there.

set -euo pipefail

cd "$(dirname "$0")/.."

if [ -x .venv/bin/tp-mcp ]; then
  exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "session-start: uv not found; skipping venv build." >&2
  echo "session-start: install uv, or create .venv manually per the README." >&2
  exit 0
fi

echo "session-start: building .venv for tp-mcp..." >&2
uv sync --quiet >&2

if [ -x .venv/bin/tp-mcp ]; then
  echo "session-start: tp-mcp ready." >&2
  if [ -z "${TP_AUTH_COOKIE:-}" ]; then
    echo "session-start: TP_AUTH_COOKIE is not set - the server will start but every call will fail auth." >&2
  fi
else
  echo "session-start: uv sync finished but .venv/bin/tp-mcp is missing." >&2
fi
