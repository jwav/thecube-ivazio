#!/usr/bin/env bash

# Stop the services
sudo systemctl stop thecubeivazio.cubebox.service
sudo systemctl stop thecubeivazio.cubemaster.service

# Determine the directory based on the hostname
if [[ $(hostname) == *"cube"* ]]; then
  THECUBE_DIR="${HOME}/thecube-ivazio"
else
  THECUBE_DIR="/mnt/shared/thecube-ivazio"
fi

# Ensure the update_version.sh script exists
if [[ ! -f "${THECUBE_DIR}/update_version.sh" ]]; then
  echo "Error: ${THECUBE_DIR}/update_version.sh not found"
  exit 1
fi

# Run the update_version.sh script with the --full-update argument
bash "${THECUBE_DIR}/update_version.sh" --full-update