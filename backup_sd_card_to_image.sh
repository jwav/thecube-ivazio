#!/bin/bash

# usage:
#sudo ./backup_sd_card.sh /dev/sda cubebox1_sd_card_backup.img

# Function to create a full backup of an SD card
backup_sd_card() {
  local source_device=$1
  local backup_image=$2

  echo "Creating a backup of $source_device to $backup_image..."
  sudo dd if="$source_device" of="$backup_image" bs=4M status=progress conv=fsync
  echo "Backup completed: $backup_image"
}

# Check for correct usage
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <source_device> <backup_image>"
  exit 1
fi

SOURCE_DEVICE="$1"
BACKUP_IMAGE="$2"

# Create the backup
backup_sd_card "$SOURCE_DEVICE" "$BACKUP_IMAGE"
