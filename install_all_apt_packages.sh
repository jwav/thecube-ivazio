#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

echo_blue "Installing all APT packages..."

# Update and upgrade the system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install packages from package_list.txt
sudo apt-get install -y dselect
sudo cat ./all_apt_packages.txt | sudo dpkg --set-selections
sudo apt-get dselect-upgrade -y

# Additional setup commands can be added here

echo_green "All APT packages installed."