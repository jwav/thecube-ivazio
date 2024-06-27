#!/usr/bin/env bash

cd "${HOME}/thecube-ivazio" || exit 1
bash ./update_version.sh
bash ./launch_cubebox.sh
