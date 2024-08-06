#!/bin/bash

# usage : sudo ./restore_sd_card.sh cubebox1_sd_card_backup.img /dev/sda

# Function to restore an SD card from a backup image
restore_sd_card() {
  local backup_image=$1
  local target_device=$2

  echo "Restoring $target_device from $backup_image..."
  sudo dd if="$backup_image" of="$target_device" bs=4M status=progress conv=fsync
  echo "Restoration completed: $target_device"
}

# Check for correct usage
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <backup_image> <target_device>"
  exit 1
fi

BACKUP_IMAGE="$1"
TARGET_DEVICE="$2"

# Restore the backup
restore_sd_card "$BACKUP_IMAGE" "$TARGET_DEVICE"
