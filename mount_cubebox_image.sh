#!/bin/bash

# Usage: ./mount_cubebox_image.sh <image_file> <mount_base_dir> [--no-umount]

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <image_file> <mount_base_dir> [--no-umount]"
  exit 1
fi

IMAGE_FILE="$1"
MOUNT_BASE_DIR="$2"
NO_UMOUNT=false

# Check for --no-umount argument
if [ "$#" -eq 3 ] && [ "$3" == "--no-umount" ]; then
  NO_UMOUNT=true
fi

# Ensure the mount base directory exists
sudo mkdir -p "$MOUNT_BASE_DIR"

# Create a loop device
LOOP_DEVICE=$(sudo losetup -fP --show "$IMAGE_FILE")

if [ -z "$LOOP_DEVICE" ]; then
  echo "Failed to create a loop device."
  exit 1
fi

echo "Loop device created: $LOOP_DEVICE"

# Get the partitions of the loop device
PARTITIONS=$(ls ${LOOP_DEVICE}p*)

if [ -z "$PARTITIONS" ]; then
  echo "No partitions found in the image."
  sudo losetup -d "$LOOP_DEVICE"
  exit 1
fi

# Create and mount each partition
for PARTITION in $PARTITIONS; do
  PARTITION_NAME=$(basename "$PARTITION")
  MOUNT_POINT="$MOUNT_BASE_DIR/$PARTITION_NAME"
  sudo mkdir -p "$MOUNT_POINT"
  sudo mount "$PARTITION" "$MOUNT_POINT"

  if [ "$?" -ne 0 ]; then
    echo "Failed to mount $PARTITION"
    sudo losetup -d "$LOOP_DEVICE"
    exit 1
  else
    echo "Mounted $PARTITION at $MOUNT_POINT"
    echo "Contents of $MOUNT_POINT:"
    ls -l "$MOUNT_POINT" | head -n 10
  fi
done

echo "All partitions mounted successfully."

# Function to unmount and detach loop device
cleanup() {
  if [ "$NO_UMOUNT" = false ]; then
    echo "Unmounting partitions and detaching loop device..."

    for PARTITION in $PARTITIONS; do
      MOUNT_POINT="$MOUNT_BASE_DIR/$(basename "$PARTITION")"
      sudo umount "$MOUNT_POINT"
      if [ "$?" -eq 0 ]; then
        echo "Unmounted $MOUNT_POINT"
      else
        echo "Failed to unmount $MOUNT_POINT"
      fi
    done

    sudo losetup -d "$LOOP_DEVICE"
    if [ "$?" -eq 0 ]; then
      echo "Detached loop device $LOOP_DEVICE"
    else
      echo "Failed to detach loop device $LOOP_DEVICE"
    fi

    # Remove the mount base directory
    # sudo rmdir "$MOUNT_BASE_DIR"
    # no, force remove
    sudo rm -rf "$MOUNT_BASE_DIR"
    if [ "$?" -eq 0 ]; then
      echo "Removed mount base directory $MOUNT_BASE_DIR"
    else
      echo "Failed to remove mount base directory $MOUNT_BASE_DIR"
    fi
  else
    echo "Skipping unmount and removal of mount base directory due to --no-umount argument."
  fi
}

# Trap exit to cleanup
trap cleanup EXIT

echo "To unmount and detach the loop device, run: sudo umount $MOUNT_BASE_DIR/* && sudo losetup -d $LOOP_DEVICE"
