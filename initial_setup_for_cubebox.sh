#!/usr/bin/env bash

source ./thecube_common_defines.sh || { echo "ERROR: Could not load thecube_common_defines.sh"; exit 1; }

# This script is meant to be run on a fresh Raspberry Pi OS installation
# once the git clone has been done.

# specify we need sudo
if [ "$EUID" -ne 0 ]; then
  echo_red "Please run with sudo"
  exit
fi

bash ./setup_sudo_no_password.sh
bash ./install_all_apt_packages.sh
bash ./install_required_apt_packages.sh
bash ./setup_python.sh
bash ./install_pip_requirements.sh --full-reinstall
bash ./install_libffi7.sh
bash ./update_thecube.sh
bash ./setup_raspberry_pi_system.sh

# prompt for reboot
echo_blue "Setup complete. Reboot now? (y/n)"
read -r do_reboot
if [ "$do_reboot" = "y" ]; then
  echo "Rebooting..."
  reboot
fi