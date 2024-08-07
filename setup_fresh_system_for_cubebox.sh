#!/usr/bin/env bash

# specify we need sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo"
  exit
fi

bash ./setup_sudo_no_password.sh
bash ./install_all_apt_packages.sh
bash ./install_required_apt_packages.sh
bash ./install_libffi7.sh
bash ./setup_python.sh
bash ./install_pip_requirements.sh --full-reinstall
bash ./update_thecube.sh
