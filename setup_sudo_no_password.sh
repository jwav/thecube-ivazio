#!/bin/bash

# This script will add the configuration for passwordless sudo

$USERNAME="ivazio"

# Ensure script is run as root
if [ "$(id -u)" -ne "0" ]; then
  echo "This script must be run as root" 1>&2
  exit 1
fi

# Backup the sudoers file
cp /etc/sudoers /etc/sudoers.bak

# Add the configuration for passwordless sudo
echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >>/etc/sudoers

# Validate the sudoers file
visudo -c

# Check if the visudo command was successful
if [ $? -eq 0 ]; then
  echo "Configuration successful. User 'ivazio' can now run sudo without a password."
else
  echo "Configuration failed. Restoring the original sudoers file."
  cp /etc/sudoers.bak /etc/sudoers
fi

# Clean up
rm /etc/sudoers.bak
