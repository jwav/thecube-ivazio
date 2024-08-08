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


THECUBE_SKIP_UPDATE=${THECUBE_SKIP_UPDATE:-false}

# hide mouse cursor
/usr/bin/unclutter -idle 1 -root &

cd "${HOME}/thecube-ivazio" || exit
source venv/bin/activate

if [ "$THECUBE_SKIP_UPDATE" = false ]; then
  bash ./update_thecube.sh
fi

bash ./launch_cubebox.sh

