#!/usr/bin/env bash
#set -x

# stop the service if it's running
sudo systemctl stop thecubeivazio.cubemaster.service

echo "Launching CubeMaster..."
cd "${HOME}/thecube-ivazio/thecubeivazio" || {
  echo "Failed to change directory"
  exit 1
}
source ../venv/bin/activate || {
  echo "Failed to activate virtual environment"
  exit 1
}
python3 ./cubeserver_cubemaster.py || {
  echo "Failed to start CubeMaster"
  exit 1
}
echo "CubeMaster started."
