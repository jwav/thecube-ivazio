#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

THECUBE_SKIP_UPDATE=false

for arg in "$@"; do
  case $arg in
  --skip-update)
    THECUBE_SKIP_UPDATE=true
    shift
    ;;
  *)
    shift
    ;;
  esac
done

export THECUBE_SKIP_UPDATE

stop_thecube_service

start_thecube_service
