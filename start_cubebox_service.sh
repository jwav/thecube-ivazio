#!/usr/bin/env bash

if [ -d "/home/ivazio/thecube-ivazio" ]; then
  scripts_dir="/home/ivazio/thecube-ivazio"
else
  scripts_dir="/mnt/shared/thecube-ivazio"
fi
echo "scripts_dir is set to: $scripts_dir"
source "${scripts_dir}/thecube_common_defines.sh" || {
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

sudo systemctl stop thecubeivazio.cubebox.service

if [ "$THECUBE_SKIP_UPDATE" = true ]; then
  sudo THECUBE_SKIP_UPDATE=true systemctl start thecubeivazio.cubebox.service
else
  sudo systemctl start thecubeivazio.cubebox.service
fi
#sudo systemctl status thecubeivazio.cubebox.service

