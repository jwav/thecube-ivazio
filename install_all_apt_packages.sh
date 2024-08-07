#!/bin/bash

# Update and upgrade the system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install packages from package_list.txt
sudo apt-get install -y dselect
sudo dpkg --set-selections <./all_apt_packages.txt
sudo apt-get dselect-upgrade -y

# Additional setup commands can be added here
