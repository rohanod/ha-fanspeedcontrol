#!/usr/bin/env bash
# Run in a local or Codex Cloud checkout; never touches a live HA instance.
set -euo pipefail
cd "$(dirname "$0")/.."
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements-test.txt
.venv/bin/python -c 'from homeassistant.const import __version__; assert __version__ == "2026.11.0", __version__'
.venv/bin/pytest
