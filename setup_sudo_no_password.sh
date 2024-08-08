#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

# This script will add the configuration for passwordless sudo

USERNAME="ivazio"

# Backup the sudoers file
sudo cp /etc/sudoers /etc/sudoers.bak

# Add the configuration for passwordless sudo if not already present
if grep -q "^$USERNAME ALL=(ALL) NOPASSWD:ALL" /etc/sudoers; then
  echo "Configuration already present. Exiting."
  exit 0
else
echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >>/etc/sudoers
fi
# Validate the sudoers file
sudo visudo -c

# Check if the visudo command was successful
if [ $? -eq 0 ]; then
  echo "Configuration successful. User 'ivazio' can now run sudo without a password."
else
  echo "Configuration failed. Restoring the original sudoers file."
  sudo cp /etc/sudoers.bak /etc/sudoers
fi

# Clean up
sudo rm /etc/sudoers.bak
