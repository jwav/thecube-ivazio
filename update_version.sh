#!/usr/bin/bash
source ./install_required_apt_packages.sh
git pull && pip install -r ./requirements.txt && python3 install .
echo "Update OK: APT packages installed, git pulled, project package pip installed."
