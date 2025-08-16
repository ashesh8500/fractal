#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/refactor_ui"
# Serve the Yew refactor_ui app from inside the refactor_ui directory
exec trunk serve "$@"
