#!/usr/bin/env bash

DEBUG=true

# if the hostname contains "cube", use this defined directory
if [[ $(hostname) == *"cube"* ]]; then
  THECUBE_DIR="${HOME}/thecube-ivazio"
else
  THECUBE_DIR="/mnt/shared/thecube-ivazio"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Functions for colored echo
echo_red() {
    echo -e "${RED}$1${NC}"
}

echo_green() {
    echo -e "${GREEN}$1${NC}"
}


# Get the directory of the script
#SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="${THECUBE_DIR}"

cd "$SCRIPT_DIR" || exit 1
source "${SCRIPT_DIR}/venv/bin/activate"

# Run the script logic inside a subshell
(
  cd "$SCRIPT_DIR" || exit 1
  echo "Current working directory: $(pwd)"

  # stop the services (no, dont do that, it causes an infinite loop when this script is run from the systemctl)
#  echo "Stopping the services..."
#  sudo systemctl stop thecubeivazio.cubemaster.service
#  sudo systemctl stop thecubeivazio.cubebox.service

  # if debug, skip apt and pip
  if [ "$DEBUG" = true ]; then
    echo "DEBUG: Skipping APT and pip updates"
    SKIP_APT=true
    SKIP_PIP_REQ=true
  fi

  for arg in "$@"
  do
    if [ "$arg" == "--full-update" ]; then
      SKIP_APT=false
      SKIP_PIP_REQ=false
      echo "Full update"
      break
    elif [ "$arg" == "--skip-apt" ]; then
      SKIP_APT=true
      echo "Skipping APT update and install"
    elif [ "$arg" == "--skip-pip" ]; then
      SKIP_PIP_REQ=true
      echo "Skipping pip install"
    fi
  done

  echo "Stashing local changes..."
  git stash
  echo "Pulling git..."
  git pull
  if [ $? -ne 0 ]; then
    echo_red "ERROR: git pull failed"
    exit 1
  else
    echo_green "OK : git pull succeeded"
  fi

  if [ "$SKIP_APT" = false ]; then
    echo "Updating APT and installing required packages.."
    bash ./install_required_apt_packages.sh
    if [ $? -ne 0 ]; then
      echo_red "ERROR: APT update and install failed"
      exit 1
    else
      echo_green "OK : APT update and install succeeded"
    fi
  fi

  if [ "$SKIP_PIP_REQ" = false ]; then
    echo "pip install requirements..."
    pip install -r ./requirements.txt
    if [ $? -ne 0 ]; then
      echo_red "ERROR: pip install requirements failed"
      exit 1
    else
      echo_green "OK : pip install requirements succeeded"
    fi
  fi

  echo "Installing the project package..."
  pip install .
  if [ $? -ne 0 ]; then
    echo_red "ERROR: project package install failed"
    exit 1
  else
    echo_green "OK : project package install succeeded"
  fi

  echo "Generating cubeboxes scripts from the cubemaster scripts..."
  bash ./generate_cubebox_scripts.sh
  echo "Copying scripts..."
  HOSTNAME=$(hostname)
  if [[ "$HOSTNAME" == "cubemaster" ]]; then
    echo "Hostname is cubemaster. Copying cubemaster scripts..."
    for file in *cubemaster*.sh; do
      echo "Copying $file to home directory and making it executable."
      cp "$file" ~/
      chmod +x ~/"$file"
    done
  elif [[ "$HOSTNAME" == *"cubebox"* ]]; then
    echo "Hostname contains cubebox. Copying cubebox scripts..."
    for file in *cubebox*.sh; do
      echo "Copying $file to home directory and making it executable."
      cp "$file" ~/
      chmod +x ~/"$file"
    done
  else
    echo "Hostname does not match cubemaster or cubebox patterns."
  fi
  # copy all scripts containing `update`
  for file in *update*.sh; do
    echo "Copying $file to home directory and making it executable."
    cp "$file" ~/
    chmod +x ~/"$file"
  done

  # setup the service, according to the hostname
  if [[ "$HOSTNAME" == "cubemaster" ]]; then
    echo "Setting up cubemaster service..."
    bash ./setup_cubemaster_service.sh
  elif [[ "$HOSTNAME" == *"cubebox"* ]]; then
    echo "Setting up cubebox service..."
    bash ./setup_cubebox_service.sh
  else
    echo "Hostname does not match cubemaster or cubebox patterns."
  fi


  echo_green "Update OK: APT packages installed, git pulled, project package pip installed, scripts copied, service set up."


) # End of subshell

