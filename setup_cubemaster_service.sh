#!/bin/bash

# Define the source and destination paths
SOURCE_PATH="${HOME}/thecube-ivazio/thecubeivazio/thecubeivazio.cubemaster.service"
DESTINATION_PATH="/etc/systemd/system/thecubeivazio.cubemaster.service"

# Check if the source file exists
if [ ! -f "$SOURCE_PATH" ]; then
    echo "Source file does not exist: $SOURCE_PATH"
    exit 1
fi

# Copy the file to the destination, overwriting if it exists
sudo cp "$SOURCE_PATH" "$DESTINATION_PATH"

# Reload systemd daemon to recognize the new service file
sudo systemctl daemon-reload

# Enable the service to start on boot
#sudo systemctl enable thecubeivazio.cubemaster.service

# Start the service immediately
#sudo systemctl start thecubeivazio.cubemaster.service

# Output the status of the service
sudo systemctl status thecubeivazio.cubemaster.service

echo "Service file copied and systemctl reloaded."
