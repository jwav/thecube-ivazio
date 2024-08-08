#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

name=$(get_either_cubemaster_or_cubebox_str)
systemctl is-enabled "thecubeivazio.${name}.service"
sudo systemctl status "thecubeivazio.${name}.service"
