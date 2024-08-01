#!/usr/bin/env bash

ARG=""

for arg in "$@"; do
  case $arg in
    --skip-update)
      ARG="--skip-update"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

sudo systemctl stop thecubeivazio.cubemaster.service
sudo systemctl start thecubeivazio.cubemaster.service $ARG
#sudo systemctl status thecubeivazio.cubemaster.service