#!/usr/bin/env bash

cd "${HOME}/thecube-ivazio/thecubeivazio" || exit
source ../venv/bin/activate || exit
python3 cubeserver_master.py || exit
