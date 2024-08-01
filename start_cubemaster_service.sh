#!/usr/bin/env bash

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

# hide mouse cursor
/usr/bin/unclutter -idle 1 -root &

sudo systemctl stop thecubeivazio.cubemaster.service

if [ "$THECUBE_SKIP_UPDATE" = true ]; then
  sudo THECUBE_SKIP_UPDATE=true systemctl start thecubeivazio.cubemaster.service
else
  sudo systemctl start thecubeivazio.cubemaster.service
fi
#sudo systemctl status thecubeivazio.cubemaster.service
