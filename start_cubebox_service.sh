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

sudo systemctl stop thecubeivazio.cubebox.service

if [ "$THECUBE_SKIP_UPDATE" = true ]; then
  sudo THECUBE_SKIP_UPDATE=true systemctl start thecubeivazio.cubebox.service
else
  sudo systemctl start thecubeivazio.cubebox.service
fi
#sudo systemctl status thecubeivazio.cubebox.service
