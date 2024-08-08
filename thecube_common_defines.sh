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

# Colors
TC_COLOR_RED='\033[0;31m'
TC_COLOR_GREEN='\033[0;32m'
TC_COLOR_BLUE='\033[0;34m'
TC_COLOR_YELLOW='\033[0;33m'
TC_COLOR_NC='\033[0m' # No Color

activate_thecube_venv() {
  source "${THECUBE_PROJECT_DIR}/venv/bin/activate"
  if [ $? -ne 0 ]; then
    echo_red "Failed to activate virtual environment"
    return 1
  fi
  return a
}

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

THECUBE_COMMON_DEFINES_LOADED=1
