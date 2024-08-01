#!/usr/bin/env bash

SKIP_UPDATE=false

for arg in "$@"; do
  case $arg in
    --skip-update)
      SKIP_UPDATE=true
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# hide mouse cursor
/usr/bin/unclutter -idle 1 -root &

cd "${HOME}/thecube-ivazio" || exit
source venv/bin/activate

if [ "$SKIP_UPDATE" = false ]; then
  bash ./update_version.sh
fi

bash ./launch_cubemaster.sh
