#!/usr/bin/env bash

THECUBE_SKIP_UPDATE=${THECUBE_SKIP_UPDATE:-false}

# hide mouse cursor
/usr/bin/unclutter -idle 1 -root &

cd "${HOME}/thecube-ivazio" || exit
source venv/bin/activate

if [ "$THECUBE_SKIP_UPDATE" = false ]; then
  bash ./update_thecube.sh
fi

bash ./launch_cubemaster.sh
