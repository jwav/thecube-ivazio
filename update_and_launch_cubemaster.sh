#!/usr/bin/env bash

cd "${HOME}/thecube-ivazio" || exit
source venv/bin/activate
bash ./update_version.sh
bash ./launch_cubemaster.sh