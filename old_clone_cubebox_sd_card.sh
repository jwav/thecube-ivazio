#!/bin/bash

# it takes about 13 minutes to copy

# Function to list potential source and destination partitions
list_partitions() {
  lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT | grep -E 'sd|mmcblk'
}

# Function to display a progress bar
copy_with_progress() {
  local src=$1
  local dst=$2

  rsync -a --info=progress2 --no-o --no-g "$src/" "$dst/"
}

# Function to force unmount all partitions of a device
force_unmount_device() {
  local device=$1
  local partitions=$(lsblk -ln -o NAME "$device" | grep -E '^sd|^mmcblk')

  for part in $partitions; do
    sudo umount "/dev/$part" 2>/dev/null
  done
}

if [ "$#" -eq 1 ]; then
  if [ "$1" == "--list" ]; then
    echo "Listing all potential source and destination partitions:"
    list_partitions
    exit 0
  elif [ "$1" == "--wipe" ]; then
    echo "Usage: $0 --wipe <target_device>"
    exit 1
  fi
elif [ "$#" -eq 2 ] && [ "$1" == "--wipe" ]; then
  TARGET_DEVICE="$2"
  echo "Wiping the partition table of the target device: $TARGET_DEVICE"
  force_unmount_device "$TARGET_DEVICE"
  sudo sgdisk --zap-all "$TARGET_DEVICE"
  sudo sgdisk --clear "$TARGET_DEVICE"
  sudo dd if=/dev/zero of="$TARGET_DEVICE" bs=1M count=10
  sudo partprobe "$TARGET_DEVICE"
  echo "Partition table wiped on $TARGET_DEVICE"
  exit 0
elif [ "$#" -ne 3 ]; then
  echo "Usage: $0 <source_device> <target_device> <new_hostname>"
  echo "       $0 --list  # to list potential source and destination partitions"
  echo "       $0 --wipe <target_device>  # to wipe all partitions on the target device"
  exit 1
fi

SOURCE_DEVICE="$1"
TARGET_DEVICE="$2"
NEW_HOSTNAME="$3"

# Source partition information
BOOT_SIZE="512MiB"
ROOT_START="514MiB" # Start root after 513 MiB
BOOT_TYPE="fat32"
ROOT_TYPE="ext4"

# Define mount points
SOURCE_BOOT_MOUNT="/mnt/source_boot"
SOURCE_ROOT_MOUNT="/mnt/source_root"
TARGET_BOOT_MOUNT="/mnt/target_boot"
TARGET_ROOT_MOUNT="/mnt/target_root"

# Unmount the partitions if they are automounted
sudo umount "${SOURCE_DEVICE}1" 2>/dev/null
sudo umount "${SOURCE_DEVICE}2" 2>/dev/null

# Force unmount the target device partitions
force_unmount_device "$TARGET_DEVICE"

# Display confirmation prompt
echo "Source Device: $SOURCE_DEVICE"
echo "Target Device: $TARGET_DEVICE"
echo ""
read -p "Do you want to proceed with copying and changing the hostname to $NEW_HOSTNAME? (yes/no): " CONFIRMATION

if [ "$CONFIRMATION" != "yes" ]; then
  echo "Operation aborted."
  exit 1
fi

# Wipe the partition table of the target device
echo "Wiping the partition table of the target device..."
force_unmount_device "$TARGET_DEVICE"
sudo sgdisk --zap-all "$TARGET_DEVICE"
sudo sgdisk --clear "$TARGET_DEVICE"
sudo dd if=/dev/zero of="$TARGET_DEVICE" bs=1M count=10
sudo partprobe "$TARGET_DEVICE"
sleep 2 # Give the kernel some time to refresh

# Create new partitions on the target device
echo "Creating new partitions on the target device..."
sudo parted "$TARGET_DEVICE" --script mklabel msdos
sudo parted "$TARGET_DEVICE" --script mkpart primary $BOOT_TYPE 1MiB $BOOT_SIZE
sudo parted "$TARGET_DEVICE" --script mkpart primary $ROOT_TYPE $ROOT_START 100%

# Inform the kernel of partition table changes
sudo partprobe "$TARGET_DEVICE"
sleep 2 # Give the kernel some time to refresh

# Check if the partitions exist
if [ ! -b "${TARGET_DEVICE}1" ] || [ ! -b "${TARGET_DEVICE}2" ]; then
  echo "Error: Partitions were not created successfully on $TARGET_DEVICE"
  exit 1
fi

# Format the partitions
echo "Formatting the new partitions..."
sudo mkfs.vfat -F 32 "${TARGET_DEVICE}1"
sudo mkfs.ext4 "${TARGET_DEVICE}2"

# Create mount points
sudo mkdir -p "$SOURCE_BOOT_MOUNT" "$SOURCE_ROOT_MOUNT" "$TARGET_BOOT_MOUNT" "$TARGET_ROOT_MOUNT"

# Mount source partitions
sudo mount "${SOURCE_DEVICE}1" "$SOURCE_BOOT_MOUNT"
sudo mount "${SOURCE_DEVICE}2" "$SOURCE_ROOT_MOUNT"

# Mount target partitions
sudo mount "${TARGET_DEVICE}1" "$TARGET_BOOT_MOUNT" -o rw
sudo mount "${TARGET_DEVICE}2" "$TARGET_ROOT_MOUNT" -o rw

# Start timing the copy process
START_TIME=$(date +%s)

# Copy contents from source to target with progress
echo "Copying /bootfs..."
copy_with_progress "$SOURCE_BOOT_MOUNT" "$TARGET_BOOT_MOUNT"
echo "Copying /rootfs..."
copy_with_progress "$SOURCE_ROOT_MOUNT" "$TARGET_ROOT_MOUNT"

# End timing the copy process
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))
echo "Total copy time: $TOTAL_TIME seconds"

# Change the hostname
echo "Changing the hostname to $NEW_HOSTNAME..."
echo "$NEW_HOSTNAME" | sudo tee "$TARGET_ROOT_MOUNT/etc/hostname"
sudo sed -i "s/$(hostname)/$NEW_HOSTNAME/g" "$TARGET_ROOT_MOUNT/etc/hosts"

# Unmount all partitions
sudo umount "$SOURCE_BOOT_MOUNT"
sudo umount "$SOURCE_ROOT_MOUNT"
sudo umount "$TARGET_BOOT_MOUNT"
sudo umount "$TARGET_ROOT_MOUNT"

# Remove mount points
sudo rmdir "$SOURCE_BOOT_MOUNT" "$SOURCE_ROOT_MOUNT" "$TARGET_BOOT_MOUNT" "$TARGET_ROOT_MOUNT"

echo "Done! The SD card has been copied and the hostname has been changed to $NEW_HOSTNAME."
echo "Total time taken: $TOTAL_TIME seconds."
