#!/usr/bin/bash

SKIP_APT=false
for arg in "$@"
do
  if [ "$arg" == "--skip-apt" ]; then
    SKIP_APT=true
    echo "Skipping APT update and install"
    break
  fi
done


if [ "$SKIP_APT" = false ]; then
  ./install_required_apt_packages.sh
  if [ $? -ne 0 ]; then
      echo "ERROR: APT udpate and install failed"
      exit 1
    else
      echo "OK : The script succeeded"
  fi
fi

git pull
pip install -r ./requirements.txt
python3 install .

echo "Update OK: APT packages installed, git pulled, project package pip installed."
