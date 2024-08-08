#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

# Stop the services
stop_thecube_service

# Run the update_thecube.sh script with the --full-update argument
bash "${THECUBE_DIR}/update_thecube.sh" --full-update || {
  echo_red "ERROR: Could not run the update_thecube.sh script"
  exit 1
}
