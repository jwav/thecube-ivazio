#!/usr/bin/env bash

cd "${HOME}/thecube-ivazio" || exit
bash ./update_version.sh
bash ./launch_cubebox.sh
