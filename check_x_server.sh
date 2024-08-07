#!/usr/bin/env bash

# Get the directory of the current script
this_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the common defines script from the same directory
source "${this_script_dir}/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

# Check if an X server or Xvfb is running
check_x_server() {
  echo_blue "Checking for running X server processes..."

  x_process=$(pgrep -x "X")
  xvfb_process=$(pgrep -x "Xvfb")

  if [ ! -z "$x_process" ]; then
    echo_green "X server is running with PID(s): $x_process"
  else
    echo_red "X server is not running."
  fi

  if [ ! -z "$xvfb_process" ]; then
    echo_green "Xvfb is running with PID(s): $xvfb_process"
  else
    echo_red "Xvfb is not running."
  fi
}

# Check the DISPLAY environment variable
check_display_variable() {
  echo_blue "Checking DISPLAY environment variable..."

  if [ ! -z "$DISPLAY" ]; then
    echo_green "DISPLAY is set to: $DISPLAY"
  else
    echo_red "DISPLAY is not set."
  fi
}

# Verbose check for X server using xdpyinfo
check_xdpyinfo() {
  echo_blue "Running xdpyinfo to check for X server..."

  if command -v xdpyinfo &>/dev/null; then
    xdpyinfo 2>&1 | tee xdpyinfo_output.log
    if [ $? -eq 0 ]; then
      echo_green "X server is running according to xdpyinfo."
    else
      echo_red "xdpyinfo indicates no X server running."
    fi
  else
    echo_red "xdpyinfo command not found."
  fi
}

# Check for Wayland display server
check_wayland() {
  echo_blue "Checking for Wayland display server..."

  if [ ! -z "$WAYLAND_DISPLAY" ]; then
    echo_green "Wayland display server is running with display: $WAYLAND_DISPLAY"
  else
    echo_red "Wayland display server is not running."
  fi
}

# Main function to run all checks
main() {
  check_x_server
  check_display_variable
  check_xdpyinfo
  check_wayland
}

# Run the main function
main
