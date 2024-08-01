#!/usr/bin/env bash

cd "${HOME}/thecube-ivazio" || exit
source venv/bin/activate
bash ./update_thecube.sh
bash ./launch_cubebox.sh
