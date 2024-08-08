#!/usr/bin/env bash

this_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${this_script_dir}/thecube_common_defines.sh" || {
  echo "this_script_dir: $this_script_dir"
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

# stop the service if it's running
sudo systemctl stop thecubeivazio.cubebox.service

echo "Launching CubeBox..."
cd "${HOME}/thecube-ivazio/thecubeivazio" || {
  echo "Failed to change directory"
  exit 1
}
activate_thecube_venv || {
  echo "Failed to activate virtual environment"
  exit 1
}
python3 ./cubeserver_cubebox.py || {
  echo "Failed to start CubeBox"
  exit 1
}
echo "CubeBox started."
