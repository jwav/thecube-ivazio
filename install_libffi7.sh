#!/bin/bash

# Define the URL and the package name
PACKAGE_URL="http://launchpadlibrarian.net/470457775/libffi7_3.3-4_armhf.deb"
PACKAGE_NAME="libffi7_3.3-4_armhf.deb"
DOWNLOAD_DIR="${HOME:-/home/ivazio}"

# Ensure the download directory exists
mkdir -p "$DOWNLOAD_DIR"

# Download the package to the home directory
echo "Downloading $PACKAGE_NAME to $DOWNLOAD_DIR..."
wget $PACKAGE_URL -O "$DOWNLOAD_DIR/$PACKAGE_NAME"

# Check if the download was successful
if [ $? -ne 0 ]; then
  echo "ERROR: Failed to download $PACKAGE_NAME"
  exit 1
fi

# Install the package
echo "Installing $PACKAGE_NAME..."
sudo dpkg -i "$DOWNLOAD_DIR/$PACKAGE_NAME"

# Fix any broken dependencies
echo "Fixing dependencies..."
sudo apt-get install -f -y

# Verify installation
echo "Verifying installation..."
if ldconfig -p | grep -q libffi.so.7; then
  echo "libffi7 installed successfully"
else
  echo "ERROR: libffi7 installation failed"
  exit 1
fi

# Cleanup
echo "Cleaning up..."
rm "$DOWNLOAD_DIR/$PACKAGE_NAME"

echo "Done."
