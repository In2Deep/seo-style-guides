#!/usr/bin/env bash
# Launch the google_seo_and_style_guides MCP server (stdio); .mcp.json runs this script.
#
# Why a launcher: an MCP client starts servers with whatever PATH it has, and macOS's own
# /usr/bin/python3 is 3.9, older than the 3.10 the server needs. This runs server.py with the
# first Python 3.10 or newer it finds. The server uses the standard library only, so there is
# nothing to install. -B keeps it from writing __pycache__ folders into the repo.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATH="${PATH:+$PATH:}$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"
for candidate in python3 python3.14 python3.13 python3.12 python3.11 python3.10; do
  if command -v "$candidate" >/dev/null 2>&1 \
    && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    exec "$candidate" -B "$HERE/server.py" "$@"
  fi
done
echo "google_seo_and_style_guides MCP server: no Python 3.10 or newer found" >&2
exit 1
