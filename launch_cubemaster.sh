#!/usr/bin/env bash
#set -x

echo "Launching CubeMaster service..."
cd "${HOME}/thecube-ivazio/thecubeivazio" || { echo "Failed to change directory"; exit 1; }
source ../venv/bin/activate || { echo "Failed to activate virtual environment"; exit 1; }
python3 ./cubeserver_cubemaster.py || { echo "Failed to start CubeMaster"; exit 1; }
echo "CubeMaster service started."