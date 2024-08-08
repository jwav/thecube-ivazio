#!/usr/bin/env bash

this_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${this_script_dir}/thecube_common_defines.sh" || {
  echo "this_script_dir: $this_script_dir"
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

