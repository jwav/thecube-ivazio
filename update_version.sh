#!/usr/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color


# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR" || exit 1
source venv/bin/activate

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

#SKIP_PIP_REQ=false
SKIP_PIP_REQ=true
for arg in "$@"
do
  if [ "$arg" == "--skip-pip" ]; then
    SKIP_PIP_REQ=true
    echo "Skipping pip install"
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

echo "Stashing local changes..."
git stash
echo "Pulling git..."
git pull
if [ $? -ne 0 ]; then
  echo "ERROR: git pull failed"
  exit 1
else
  echo "OK : git pull succeeded"
fi

if [ "$SKIP_PIP_REQ" = false ]; then
echo "pip install requirements..."
pip install -r ./requirements.txt
if [ $? -ne 0 ]; then
  echo "ERROR: pip install requirements failed"
  exit 1
else
  echo "OK : pip install requirements succeeded"
fi
fi

echo "Installing the project package..."
pip install .
if [ $? -ne 0 ]; then
  echo "ERROR: project package install failed"
  exit 1
else
  echo "OK : project package install succeeded"
fi

echo "Copying scripts..."
# if the hostname is cubemaster, copy the cubemaster scripts, otherwise copy the cubebox scripts
if [ "$(hostname)" == "cubemaster" ]; then
  cp update_and_start_cubemaster.sh ~/update_and_start_cubemaster.sh
  chmod +x ~/update_and_start_cubemaster.sh
  cp view_cubemaster_logs.sh ~/view_cubemaster_logs.sh
  chmod +x ~/view_cubemaster_logs.sh
  cp setup_cubemaster_service.sh ~/setup_cubemaster_service.sh
  chmod +x ~/setup_cubemaster_service.sh
  cp start_cubemaster_service.sh ~/start_cubemaster_service.sh
  chmod +x ~/start_cubemaster_service.sh
  cp stop_cubemaster_service.sh ~/stop_cubemaster_service.sh
  chmod +x ~/stop_cubemaster_service.sh
else
  cp update_and_start_cubebox.sh ~/update_and_start_cubebox.sh
  chmod +x ~/update_and_start_cubebox.sh
  cp view_cubebox_logs.sh ~/view_cubebox_logs.sh
  chmod +x ~/view_cubebox_logs.sh
  cp setup_cubebox_service.sh ~/setup_cubebox_service.sh
  chmod +x ~/setup_cubebox_service.sh
fi


echo -e "${GREEN}Update OK: APT packages installed, git pulled, project package pip installed.${NC}"

)