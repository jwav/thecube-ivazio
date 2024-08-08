#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

echo_blue "Launching $THECUBE_SERVERTYPE_NAME..."

stop_thecube_service || exit 1

activate_thecube_venv || exit 1

launch_thecube || exit 1

echo "${THECUBE_SERVERTYPE_NAME} launched successfully"
