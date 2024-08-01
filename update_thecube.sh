#!/usr/bin/env bash

DEBUG=true

# Define CUBE_HOSTNAME globally
CUBE_HOSTNAME=$(hostname)

# if the hostname contains "cube", use this defined directory
if [[ "$CUBE_HOSTNAME" == *"cube"* ]]; then
  THECUBE_DIR="${HOME}/thecube-ivazio"
else
  THECUBE_DIR="/mnt/shared/thecube-ivazio"
fi
export THECUBE_DIR

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

generate_cubebox_scripts_from_cubemaster_scripts() {
  echo "Generating cubeboxes scripts from the cubemaster scripts..."

  # Define a function to replace cubemaster with cubebox in a file
  replace_cubemaster_with_cubebox() {
    local tmpfile=$(mktemp)
    sed 's/cubemaster/cubebox/g' "$1" >"$tmpfile"
    sed 's/CubeMaster/CubeBox/g' "$tmpfile" >"$2"
    rm "$tmpfile"
  }

  # List of files to process
  local files=(
    "thecubeivazio.cubemaster.service"
    "launch_cubemaster.sh"
    "start_cubemaster_service.sh"
    "setup_cubemaster_service.sh"
    "check_cubemaster_status.sh"
    "update_and_launch_cubemaster.sh"
    "stop_cubemaster_service.sh"
    "view_cubemaster_logs.sh"
  )

  # Loop through the files and create new files with the replacements
  for file in "${files[@]}"; do
    local new_file=$(echo "$file" | sed 's/cubemaster/cubebox/g')
    replace_cubemaster_with_cubebox "$file" "$new_file"
  done
}

copy_relevant_scripts_to_home() {
  # Initialize an array for scripts to copy
  local scripts_to_copy=(
    "activate_venv.sh"
    "install_required_apt_packages.sh"
    "*update*.sh"
    "configure_ssh_firewall.sh"
  )

  # Initialize an array for the filtered scripts
  local filtered_scripts=()

  # Function to add scripts based on pattern
  add_scripts() {
    local pattern=$1
    for file in $pattern; do
      if [[ -f "$file" ]]; then
        filtered_scripts+=("$file")
      fi
    done
  }

  # Function to exclude scripts based on pattern
  exclude_scripts() {
    local pattern=$1
    local temp_array=()
    for script in "${filtered_scripts[@]}"; do
      if [[ "$script" != "$pattern" ]]; then
        temp_array+=("$script")
      fi
    done
    filtered_scripts=("${temp_array[@]}")
  }

  # Add the general scripts
  for script in "${scripts_to_copy[@]}"; do
    add_scripts "$script"
  done

  # Modify the list based on the hostname
  if [[ "$CUBE_HOSTNAME" == "cubemaster" ]]; then
    echo "Hostname is cubemaster. Adding cubemaster scripts and excluding cubebox scripts..."
    add_scripts "*cubemaster*.sh"
    exclude_scripts "*cubebox*.sh"
  elif [[ "$CUBE_HOSTNAME" == *"cubebox"* ]]; then
    echo "Hostname contains cubebox. Adding cubebox scripts and excluding cubemaster scripts..."
    add_scripts "*cubebox*.sh"
    exclude_scripts "*cubemaster*.sh"
  fi

  # Copy and chmod+x the filtered scripts
  for script in "${filtered_scripts[@]}"; do
    echo "Copying $script to home directory and making it executable."
    cp "$script" ~/
    chmod +x ~/"$script"
  done
}

setup_relevant_service() {
  # Setup the service according to the hostname
  if [[ "$CUBE_HOSTNAME" == "cubemaster" ]]; then
    echo "Setting up cubemaster service..."
    bash ./setup_cubemaster_service.sh
  elif [[ "$CUBE_HOSTNAME" == *"cubebox"* ]]; then
    echo "Setting up cubebox service..."
    bash ./setup_cubebox_service.sh
  else
    echo "Hostname does not match cubemaster or cubebox patterns."
  fi
}

# Get the directory of the script
# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="${THECUBE_DIR}"

cd "$SCRIPT_DIR" || exit 1
source "${SCRIPT_DIR}/venv/bin/activate"

# ACTUAL SCRIPT LOGIC :

# Run the script logic inside a subshell
(
  cd "$SCRIPT_DIR" || exit 1
  echo "Current working directory: $(pwd)"

  # If debug, skip apt and pip
  if [ "$DEBUG" = true ]; then
    echo "DEBUG: Skipping APT and pip updates"
    SKIP_APT=true
    SKIP_PIP_REQ=true
  fi

  for arg in "$@"; do
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

  generate_cubebox_scripts_from_cubemaster_scripts

  copy_relevant_scripts_to_home

  setup_relevant_service

  echo_green "Update OK: APT packages installed, git pulled, project package pip installed, scripts copied, service set up."

)
# End of subshell
