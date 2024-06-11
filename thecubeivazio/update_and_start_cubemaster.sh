#!/usr/bin/env bash

cd "${HOME}/thecube-ivazio" || exit
source ../venv/bin/activate
bash ./update_version.sh
cd "${HOME}/thecube-ivazio/thecubeivazio" || exit
python3 cubeserver_master.py
