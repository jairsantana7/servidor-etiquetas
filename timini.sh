#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export TIMINIPRINT_NO_UPDATE_CHECK=1
exec "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/vendor/TiMini-Print/timiniprint_command_line.py" "$@"
