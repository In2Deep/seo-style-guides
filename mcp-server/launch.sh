#!/usr/bin/env bash
# Launch the google_seo_and_style_guides MCP server (stdio); the plugin and .mcp.json run this script.
#
# Why a launcher: an MCP client starts servers with whatever PATH it has, often a bare
# /usr/bin:/bin where python3 is macOS's own 3.9, older than the 3.10 the server needs. This runs
# server.py with the first Python 3.10 or newer it finds, also looking where Homebrew, python.org,
# pyenv, asdf, mise, conda and uv put theirs. The server uses the standard library only, so there
# is nothing to install. -B keeps it from writing __pycache__ folders into the repo.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATH="${PATH:+$PATH:}$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"
PATH="$PATH:/Library/Frameworks/Python.framework/Versions/Current/bin:$HOME/.pyenv/shims:$HOME/.asdf/shims"
PATH="$PATH:$HOME/.local/share/mise/shims:$HOME/miniconda3/bin:$HOME/anaconda3/bin:$HOME/miniforge3/bin"
candidates=(python3 python3.14 python3.13 python3.12 python3.11 python3.10)
# Installers that keep each version in its own folder, newest first.
while IFS= read -r folder; do
  candidates+=("$folder/python3")
done < <(ls -d "$HOME"/.pyenv/versions/*/bin "$HOME"/.local/share/uv/python/*/bin \
  /Library/Frameworks/Python.framework/Versions/3.*/bin 2>/dev/null | sort -rV)
for candidate in "${candidates[@]}"; do
  if command -v "$candidate" >/dev/null 2>&1 \
    && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    exec "$candidate" -B "$HERE/server.py" "$@"
  fi
done
echo "google_seo_and_style_guides MCP server: no Python 3.10 or newer found." \
  "Install one (for example: brew install python), then restart Claude." >&2
exit 1
