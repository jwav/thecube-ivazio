#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

name=$(get_either_cubemaster_or_cubebox_str)

# stop the service if it's running
sudo systemctl stop "thecubeivazio.${name}.service"

echo "Launching $name..."
cd "$THECUBE_PROJECT_DIR/thecubeivazio" || {
  echo "Failed to change directory"
  exit 1
}
activate_thecube_venv || {
  echo "Failed to activate virtual environment"
  exit 1
}
python3 "$THECUBE_PROJECT_DIR/cubeserver_${name}.py" || {
  echo "Failed to start $name"
  exit 1
}
echo "$name started."
