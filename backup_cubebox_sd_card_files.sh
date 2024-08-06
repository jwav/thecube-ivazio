#!/bin/bash

# Define source and destination directories
SOURCE_BOOTFS="/media/vee/bootfs"
SOURCE_ROOTFS="/media/vee/rootfs"
DEST_BASE_DIR="/home/vee"
DEST_DIR="$DEST_BASE_DIR/cubebox1_backups"
DEST_BOOTFS="$DEST_DIR/bootfs"
DEST_ROOTFS="$DEST_DIR/rootfs"

# Create the cubebox1_backups directory if it doesn't exist
sudo mkdir -p "$DEST_DIR"

# Function to display a progress bar for rsync
copy_with_rsync() {
  local src=$1
  local dst=$2

  sudo mkdir -p "$dst"

  # Copy files with progress
  sudo rsync -a --info=progress2 "$src/" "$dst"
}

# Check if destination directories already exist
if [ -d "$DEST_BOOTFS" ] || [ -d "$DEST_ROOTFS" ]; then
  echo "ERROR: Destination directories already exist. Please remove them first."
  echo "To remove them, run: "
  echo "sudo rm -rf $DEST_BOOTFS $DEST_ROOTFS"
  exit 1
fi

# Create destination directories
sudo mkdir -p "$DEST_BOOTFS"
sudo mkdir -p "$DEST_ROOTFS"

# Copy bootfs and rootfs with progress
echo "Copying bootfs..."
copy_with_rsync "$SOURCE_BOOTFS" "$DEST_BOOTFS"
echo "Copying bootfs completed successfully."

echo "Copying rootfs..."
copy_with_rsync "$SOURCE_ROOTFS" "$DEST_ROOTFS"
echo "Copying rootfs completed successfully."

echo "All files copied successfully."
echo "Backup completed: $DEST_DIR"
