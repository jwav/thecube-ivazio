#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

service_name="$(get_thecube_service_name)"

# Define the source and destination paths
SOURCE_PATH="${THECUBE_PROJECT_DIR}/${service_name}"
DESTINATION_PATH="/etc/systemd/system/${service_name}"

# Check if the source file exists
if [ ! -f "$SOURCE_PATH" ]; then
  echo "Source file does not exist: $SOURCE_PATH"
  exit 1
fi

# Copy the file to the destination, overwriting if it exists
sudo install -m 644 "$SOURCE_PATH" "$DESTINATION_PATH" || exit 1

# Reload systemd daemon to recognize the new service file
sudo systemctl daemon-reload || exit 1

# Enable the service to start on boot
sudo systemctl enable "${service_name}" || exit 1

# Disable the service to ensure it does not start on boot
#sudo systemctl disable "${service_name}"

# Start the service immediately
#sudo systemctl start "${service_name}"

echo_green "Service file $service_name copied and systemctl reloaded."

# reload systemd configuration
sudo systemctl daemon-reload || exit 1

# Output the status of the service
#sudo systemctl status thecubeivazio.cubemaster.service

# if the status is not enabled, print so
if ! sudo systemctl is-enabled --quiet "$service_name"; then
  echo_red "ERROR: Service is not enabled!"
fi

echo_green "Service setup complete for ${service_name}."
