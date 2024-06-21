#!/usr/bin/env bash

cd "${HOME}/thecube-ivazio/thecubeivazio" || exit
source ../venv/bin/activate
bash ../update_version.sh
python3 cubeserver_cubebox.py
