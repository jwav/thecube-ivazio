#!/usr/bin/env bash
#set -x

# stop the service if it's running
sudo systemctl stop thecubeivazio.cubebox.service

echo "Launching CubeBox..."
cd "${HOME}/thecube-ivazio/thecubeivazio" || {
  echo "Failed to change directory"
  exit 1
}
source ../venv/bin/activate || {
  echo "Failed to activate virtual environment"
  exit 1
}
python3 ./cubeserver_cubebox.py || {
  echo "Failed to start CubeBox"
  exit 1
}
echo "CubeBox started."
