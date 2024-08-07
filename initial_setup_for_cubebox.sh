#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

# This script is meant to be run on a fresh Raspberry Pi OS installation
# once the git clone has been done.



cd "$THECUBE_PROJECT_DIR" || exit 1

# Save the start time
start_time=$(date +%s)

bash ./setup_sudo_no_password.sh || exit 1
bash ./setup_locale.sh || exit 1
bash ./install_all_apt_packages.sh || exit 1
bash ./install_required_apt_packages.sh || exit 1
bash ./setup_python.sh || exit 1
create_thecube_venv || exit 1
bash ./install_libffi7.sh || exit 1
bash ./install_pip_requirements.sh --full-reinstall || exit 1
bash ./update_thecube.sh --full-update || exit 1
bash ./setup_raspberry_pi_system.sh || exit 1
bash ./setup_rpi_audio.sh || exit 1


# Save the end time
end_time=$(date +%s)
# Calculate the duration
duration=$((end_time - start_time))
# Convert duration to hours, minutes, and seconds
hours=$((duration / 3600))
minutes=$(( (duration % 3600) / 60))
seconds=$((duration % 60))

echo_green "Total execution time: ${hours} hours, ${minutes} minutes, and ${seconds} seconds."

# prompt for reboot
echo_blue "Setup complete. Reboot now? (y/n)"
read -r do_reboot
if [ "$do_reboot" = "y" ]; then
  echo "Rebooting..."
  reboot
else
  echo "Not rebooting."
fi
