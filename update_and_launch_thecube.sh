#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

THECUBE_SKIP_UPDATE=${THECUBE_SKIP_UPDATE:-false}
export THECUBE_SKIP_UPDATE

activate_thecube_venv || {
  echo "Failed to activate virtual environment"
  exit 1
}

if [ "$THECUBE_SKIP_UPDATE" = false ]; then
  update_thecube || exit 1
  fi

name=$(get_either_cubemaster_or_cubebox_str)
echo_green "Launching $name..."
launch_thecube || exit 1

