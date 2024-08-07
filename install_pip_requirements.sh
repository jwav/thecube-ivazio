#!/bin/bash

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR" || exit 1
source "${SCRIPT_DIR}/venv/bin/activate"
echo "Activating virtual environment at ${SCRIPT_DIR}/venv/bin/activate"

if [[ "$1" == "--full-reinstall" ]]; then
  echo "Full reinstall requested. Forcing reinstallation of all requirements without cache..."
  yes | pip install --no-cache-dir --force-reinstall -r ./requirements.txt
else
  echo "pip install requirements..."
  yes | pip install -r ./requirements.txt
fi

if [ $? -ne 0 ]; then
  echo "ERROR: pip install requirements failed"
  deactivate
  exit 1
else
  echo "OK : pip install requirements succeeded"
fi

deactivate
echo "Deactivated virtual environment"
