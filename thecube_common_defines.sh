#!/usr/bin/env bash

# This script defines common paths and functions for thecube scripts
THECUBE_USER_HOME="/home/ivazio"
# Define CUBE_HOSTNAME globally
CUBE_HOSTNAME=$(hostname)

# if the hostname contains "cube", use this defined directory
if [[ "$CUBE_HOSTNAME" == *"cube"* ]]; then
  THECUBE_PROJECT_DIR="$THECUBE_USER_HOME/thecube-ivazio"
else
  THECUBE_PROJECT_DIR="/mnt/shared/thecube-ivazio"
fi
THECUBE_SCRIPTS_DIR="$THECUBE_THECUBE_PROJECT_DIR"

THECUBE_SRC_DIR="$THECUBE_PROJECT_DIR/thecubeivazio"
#echo "===== src dir: $THECUBE_SRC_DIR"

# Colors
TC_COLOR_RED='\033[0;31m'
TC_COLOR_GREEN='\033[0;32m'
TC_COLOR_BLUE='\033[0;34m'
TC_COLOR_YELLOW='\033[0;33m'
TC_COLOR_NC='\033[0m' # No Color

# Functions for colored echo: red, green blue, yellow
echo_red() {
  echo -e "${TC_COLOR_RED}$1${TC_COLOR_NC}"
}

echo_green() {
  echo -e "${TC_COLOR_GREEN}$1${TC_COLOR_NC}"
}

echo_blue() {
  echo -e "${TC_COLOR_BLUE}$1${TC_COLOR_NC}"
}

echo_yellow() {
  echo -e "${TC_COLOR_YELLOW}$1${TC_COLOR_NC}"
}

# returns true if the hostname contains "cubebox"
is_cubebox() {
  if [[ "$CUBE_HOSTNAME" == *"cubebox"* ]]; then
    return 0
  else
    return 1
  fi
}

# returns true if the hostname contains "cubemaster"
is_cubemaster() {
  if [[ "$CUBE_HOSTNAME" == *"cubemaster"* ]]; then
    return 0
  else
    return 1
  fi
}

# returns "cubebox" if is_cubebox() is true, "cubemaster" if is_cubemaster() is true, "error" if neither
get_either_cubemaster_or_cubebox_str() {
  if is_cubebox; then
    echo "cubebox"
  elif is_cubemaster; then
    echo "cubemaster"
  else
    echo "error"
  fi
}

get_thecube_service_name() {
#  echo "thecubeivazio.$(get_either_cubemaster_or_cubebox_str).service"
  echo "thecubeivazio.thecube.service"

}

setup_thecube_service() {
  service_name="$(get_thecube_service_name)"
  echo_blue "Setting up $service_name ..."
  bash "$THECUBE_PROJECT_DIR/setup_thecube_service.sh"
  if [ $? -ne 0 ]; then
    echo_red "Failed to setup $service_name"
    return 1
  fi
  echo_green "$service_name setup successfully"
  return 0
}

stop_thecube_service() {
  service_name="$(get_thecube_service_name)"
  echo_blue "Stopping $service_name ..."
  sudo systemctl stop "$service_name"
  if [ $? -ne 0 ]; then
    echo_red "Failed to stop $service_name"
    return 1
  fi
  echo_green "Stopped $service_name"
  return 0
}

start_thecube_service() {
  service_name="$(get_thecube_service_name)"
  if [ "$THECUBE_SKIP_UPDATE" = true ]; then
    echo_blue "Starting $service_name without updating ..."
    sudo THECUBE_SKIP_UPDATE=true systemctl start "$service_name"
  else
    echo_blue "Starting $service_name ..."
    sudo systemctl start "$service_name"
  fi
  if [ $? -ne 0 ]; then
    echo_red "Failed to start $service_name"
    return 1
  fi
  echo_green "Started $service_name"
  return 0
}

activate_thecube_venv() {
  source "${THECUBE_PROJECT_DIR}/venv/bin/activate"
  if [ $? -ne 0 ]; then
    echo_red "Failed to activate virtual environment in ${THECUBE_PROJECT_DIR}/venv"
    return 1
  fi
  echo_green "Activated virtual environment"
  return 0
}

create_thecube_venv() {
  if [ -d "${THECUBE_PROJECT_DIR}/venv" ]; then
    echo_yellow "Virtual environment already exists"
    return 0
  fi
  echo_blue "Creating virtual environment..."
  python3 -m venv "${THECUBE_PROJECT_DIR}/venv"
  if [ $? -ne 0 ]; then
    echo_red "Failed to create virtual environment"
    return 1
  fi
  echo_green "Created virtual environment"
  return 0
}

recreate_thecube_venv() {
  echo_blue "Deleting existing virtual environment at ${THECUBE_PROJECT_DIR}/venv..."
  rm -rf "${THECUBE_PROJECT_DIR}/venv"
  create_thecube_venv
}

update_thecube() {
  bash "$THECUBE_PROJECT_DIR/update_thecube.sh"
  if [ $? -ne 0 ]; then
    echo_red "Failed to update thecube"
    return 1
  fi
  echo_green "Updated thecube"
  return 0

}

launch_thecube() {
  # enter the venv first
  activate_thecube_venv
  script_fullpath="$THECUBE_SRC_DIR/cubeserver_$(get_either_cubemaster_or_cubebox_str).py"
  python3 "$script_fullpath"
  if [ $? -ne 0 ]; then
    echo_red "Failed to launch $script_fullpath"
    return 1
  fi
  echo_green "Launched $script_fullpath"
}

THECUBE_COMMON_DEFINES_LOADED=1
export THECUBE_COMMON_DEFINES_LOADED
export THECUBE_USER_HOME
export THECUBE_PROJECT_DIR
export THECUBE_SCRIPTS_DIR
export CUBE_HOSTNAME

#THECUBE_SERVICE_NAME="$(get_thecube_service_name)"
#export THECUBE_SERVICE_NAME
#THECUBE_SERVERTYPE_NAME="$(get_either_cubemaster_or_cubebox_str)"
#export THECUBE_SERVERTYPE_NAME
