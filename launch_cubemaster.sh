#!/usr/bin/env bash

cd "${HOME}/thecube-ivazio" || exit
source ../venv/bin/activate
cd "${HOME}/thecube-ivazio/thecubeivazio" || exit
python3 cubeserver_cubebox.py
