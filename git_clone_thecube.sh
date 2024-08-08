#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

cd /home/ivazio || exit 1
git clone https://github.com/jwav/thecube-ivazio.git
