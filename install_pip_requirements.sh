#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

activate_thecube_venv

pip install --upgrade pip
pip install --upgrade setuptools
pip install --upgrade wheel


if [[ "$1" == "--full-reinstall" ]]; then
  echo "Full reinstall requested. Forcing reinstallation of all requirements without cache..."
  yes | pip install --no-cache-dir --force-reinstall -r ./requirements.txt
  echo "pip install Raspberry Pi requirements..."
  yes | pip install --no-cache-dir --force-reinstall -r ./pip_requirements_rpi.txt
else
  echo_blue "pip install common requirements..."
  yes | pip install -r ./requirements.txt
  echo_blue "pip install Raspberry Pi requirements..."
  yes | pip install -r ./pip_requirements_rpi.txt
fi

if [ $? -ne 0 ]; then
  echo "ERROR: pip install requirements failed"
  exit 1
fi

echo "OK : pip install requirements succeeded"

# reinstall the project package
echo "Reinstalling the project package..."
yes | pip install .

deactivate
echo "Deactivated virtual environment"
