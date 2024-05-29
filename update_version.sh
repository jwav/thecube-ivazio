#!/usr/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color


# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"



# Run the script logic inside a subshell
(
  cd "$SCRIPT_DIR" || exit 1
  echo "Current working directory: $(pwd)"

# TODO: while debugging, i'm skipping the APT update and install
#SKIP_APT=false
SKIP_APT=true
for arg in "$@"
do
  if [ "$arg" == "--skip-apt" ]; then
    SKIP_APT=true
    echo "Skipping APT update and install"
    break
  fi
done


if [ "$SKIP_APT" = false ]; then
  echo "Updating APT and installing required packages.."
  ./install_required_apt_packages.sh
  if [ $? -ne 0 ]; then
      echo "ERROR: APT udpate and install failed"
      exit 1
  else
    echo "OK : The script succeeded"
  fi
fi

echo "Pulling git..."
git pull
if [ $? -ne 0 ]; then
  echo "ERROR: git pull failed"
  exit 1
else
  echo "OK : git pull succeeded"
fi

echo "pip install requirements..."
pip install -r ./requirements.txt
if [ $? -ne 0 ]; then
  echo "ERROR: pip install requirements failed"
  exit 1
else
  echo "OK : pip install requirements succeeded"
fi

echo "Installing the project package..."
pip install .
if [ $? -ne 0 ]; then
  echo "ERROR: project package install failed"
  exit 1
else
  echo "OK : project package install succeeded"
fi

echo -e "${GREEN}Update OK: APT packages installed, git pulled, project package pip installed.${NC}"

)