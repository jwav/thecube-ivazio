#!/usr/bin/env bash

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Activating virtual environment at ${SCRIPT_DIR}/venv/bin/activate"
cd "$SCRIPT_DIR" || exit 1
source "${SCRIPT_DIR}/venv/bin/activate"