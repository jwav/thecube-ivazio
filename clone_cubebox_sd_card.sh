#!/bin/bash

# Global variables
TARGET_BOOTFS_SIZE="512M"
BOOTFS_PARTITION_TYPE="vfat"
ROOTFS_PARTITION_TYPE="ext4"
PARTITION_BUFFER_SIZE="1M"
SKIP_CHECK=false
SOURCE_BOOTFS=""
SOURCE_ROOTFS=""
TARGET_ROOTFS=""
TARGET_BOOTFS=""
SOURCE_DEVICE=""
TARGET_DEVICE=""
BOOT_DIR_NAME="bootfs"
ROOT_DIR_NAME="rootfs"
NEW_HOSTNAME=""
RPI_IMAGE=""
KEEP_TARGET_PARTITIONS=false
DONT_COPY=false
DONT_CHANGE_HOSTNAME=false
STOP_CHECK_AT_FIRST_DIFF=true
SKIP_SOUND=false
AUTO_CONFIRM=false
RPI_ROOTFS_NEW_SIZE="12G"

# ---------------------
# FUNCTIONS DEFINITIONS
# ---------------------

echo_blue() {
  echo -e "\033[34m$1\033[0m"
}

echo_red() {
  echo -e "\033[31m$1\033[0m"
}

echo_green() {
  echo -e "\033[32m$1\033[0m"
}

echo_yellow() {
  echo -e "\033[33m$1\033[0m"
}

resize_partition() {
  local partition="$1"
  local size="$2"
  local fs_size="$3"

  echo_blue "resize_partition $partition $size $fs_size"

  if [ -z "$partition" ] || [ -z "$size" ] || [ -z "$fs_size" ]; then
    echo_red "Usage: resize_partition <partition> <size> <fs_size>"
    return 1
  fi

  # check that the fs_size is smaller than the size
  if [ "$fs_size" -gt "$size" ]; then
    echo_red "ERROR: The new filesystem size is larger than the partition size."
    return 1
  fi

  # Unmount the partition
  echo_blue "Unmounting $partition..."
  sudo umount "$partition"

  # Check the filesystem
  echo_blue "Checking the filesystem on $partition..."
  sudo e2fsck -f "$partition"

  # Resize the filesystem to the specified size
  echo_blue "Resizing the filesystem on $partition to $fs_size..."
  sudo resize2fs "$partition" "$fs_size"
  if [ $? -ne 0 ]; then
    echo_red "Error resizing the filesystem."
    return 1
  fi

  # Resize the partition
  echo_blue "Resizing the partition $partition to $size..."
  sudo parted "${partition%[0-9]*}" --script resizepart "${partition##*[!0-9]}" "$size"
  if [ $? -ne 0 ]; then
    echo_red "Error resizing the partition."
    return 1
  fi

  echo_green "Partition resize completed."
  return 0
}

auto_set_target_dirs() {
  local rootfs_found=false
  local bootfs_found=false

  for dir in /home/*/media /home/*/mnt; do
    if [ -d "$dir" ]; then
      for subdir in "$dir"/*; do
        if [ -d "$subdir" ]; then
          if [[ "$subdir" == *"rootfs"* && "$subdir" != "$SOURCE_ROOTFS" ]]; then
            TARGET_ROOTFS="$subdir"
            echo_green "Found TARGET_ROOTFS: $TARGET_ROOTFS"
            rootfs_found=true
            break 2
          fi
        fi
      done
    fi
  done

  for dir in /home/*/media /home/*/mnt; do
    if [ -d "$dir" ]; then
      for subdir in "$dir"/*; do
        if [ -d "$subdir" ]; then
          if [[ "$subdir" == *"bootfs"* ]]; then
            TARGET_BOOTFS="$subdir"
            echo_green "Found TARGET_BOOTFS: $TARGET_BOOTFS"
            bootfs_found=true
            break 2
          fi
        fi
      done
    fi
  done

  if [ "$rootfs_found" = false ]; then
    echo_red "Error: rootfs directory not found or is the same as SOURCE_ROOTFS"
  fi

  if [ "$bootfs_found" = false ]; then
    echo_red "Error: bootfs directory not found"
  fi
}

handle_arguments() {
  echo_blue "handle_arguments $@"
  while [ "$#" -gt 0 ]; do
    case $1 in
    --list)
      echo_blue "Listing all potential source and destination partitions:"
      list_partitions
      exit 0
      ;;
    --wipe-target=*)
      TARGET_DEVICE="${1#*=}"
      echo_blue "Wiping the partition table of the target device: $TARGET_DEVICE"
      wipe_partitions_on_device "$TARGET_DEVICE"
      echo_green "Partition table wiped on $TARGET_DEVICE"
      exit 0
      ;;
    --find-target-dirs)
      auto_set_target_dirs
      exit 0
      ;;
    --skip-check)
      SKIP_CHECK=true
      ;;
    --keep-target-partitions)
      KEEP_TARGET_PARTITIONS=true
      ;;
    --dont-copy)
      DONT_COPY=true
      ;;
    --src-boot-dir=*)
      SOURCE_BOOTFS="${1#*=}"
      ;;
    --src-root-dir=*)
      SOURCE_ROOTFS="${1#*=}"
      ;;
    --source-device=*)
      SOURCE_DEVICE="${1#*=}"
      ;;
    --target-device=*)
      TARGET_DEVICE="${1#*=}"
      ;;
    --new-hostname=*)
      NEW_HOSTNAME="${1#*=}"
      ;;
    --rpi-image=*)
      RPI_IMAGE="${1#*=}"
      ;;
    --dont-change-hostname)
      DONT_CHANGE_HOSTNAME=true
      ;;
    --skip-sound)
      SKIP_SOUND=true
      ;;
    --auto-confirm)
      AUTO_CONFIRM=true
      ;;
    --just-check)
      KEEP_TARGET_PARTITIONS=true
      DONT_COPY=true
      SKIP_CHECK=false
      DONT_CHANGE_HOSTNAME=true
      ;;
    --quickdo)
      SOURCE_BOOTFS="/home/vee/cubebox1_backups/bootfs"
      SOURCE_ROOTFS="/home/vee/cubebox1_backups/rootfs"
      TARGET_DEVICE="/dev/sdc"
      SOURCE_DEVICE=""
      NEW_HOSTNAME="cubebox2"
      #                RPI_IMAGE="/home/vee/Downloads/2024-03-15-raspios-bookworm-armhf.img"
      #                SKIP_CHECK=true
      KEEP_TARGET_PARTITIONS=true
      DONT_COPY=true
      # do a --just-check
      TARGET_DEVICE=""
      TARGET_ROOTFS="/media/vee/rootfs"
      TARGET_BOOTFS="/media/vee/bootfs"
      DONT_COPY=true
      KEEP_TARGET_PARTITIONS=true
      SKIP_CHECK=false
      DONT_CHANGE_HOSTNAME=true
      SKIP_SOUND=true
      AUTO_CONFIRM=true
      STOP_CHECK_AT_FIRST_DIFF=false
      ;;
    --help)
      echo "Usage: $0 [--source-device=<source_device>] [--target-device=<target_device>] [--new-hostname=<hostname>] [--skip-check] [--src-boot-dir=<boot_dir>] [--src-root-dir=<root_dir>] [--rpi-image=<image_file>] [--quickdo]"
      exit 0
      ;;
    *)
      echo_red "Usage: $0 [--source-device=<source_device>] [--target-device=<target_device>] [--new-hostname=<hostname>] [--skip-check] [--src-boot-dir=<boot_dir>] [--src-root-dir=<root_dir>] [--rpi-image=<image_file>] [--quickdo]"
      exit 1
      ;;
    esac
    shift
  done

  if [ -z "$TARGET_DEVICE" ]; then
    if [ -z "$TARGET_ROOTFS" ] || [ -z "$TARGET_BOOTFS" ]; then
      echo_red "ERROR: Either --target-device or (--target-root-dir and --target-boot-dir) must be specified"
      exit 1
    fi
  fi

  if [ -z "$NEW_HOSTNAME" ]; then
    echo_red "ERROR: New hostname must be specified with --new-hostname"
    exit 1
  fi

  if [ -n "$RPI_IMAGE" ]; then
    echo_blue "Using Raspberry Pi Imager to write the image to $TARGET_DEVICE"
  else
    if [ -n "$SOURCE_DEVICE" ] && [ "$SOURCE_DEVICE" != "quickdo_placeholder" ]; then
      SOURCE_BOOTFS="/mnt/$BOOT_DIR_NAME"
      SOURCE_ROOTFS="/mnt/$ROOT_DIR_NAME"
      echo_blue "Source device: $SOURCE_DEVICE"
      echo_blue "Source boot directory: $SOURCE_BOOTFS"
      echo_blue "Source root directory: $SOURCE_ROOTFS"
    elif [ -n "$SOURCE_BOOTFS" ] && [ -n "$SOURCE_ROOTFS" ]; then
      echo_blue "Manually set source boot directory: $SOURCE_BOOTFS"
      echo_blue "Manually set source root directory: $SOURCE_ROOTFS"
    else
      echo_red "ERROR: Either --source-device or both --src-boot-dir and --src-root-dir must be specified"
      exit 1
    fi

    if ! check_source_directories_contents "$SOURCE_BOOTFS" "$SOURCE_ROOTFS"; then
      echo_red "Directory contents of $SOURCE_BOOTFS:"
      ls "$SOURCE_BOOTFS"
      echo_red "Directory contents of $SOURCE_ROOTFS:"
      ls "$SOURCE_ROOTFS"
      exit 1
    fi
  fi
}

mount_source_device() {
  echo_blue "mount_source_device : $SOURCE_DEVICE to $SOURCE_BOOTFS and $SOURCE_ROOTFS"
  local source_device=$SOURCE_DEVICE
  local source_bootfs=$SOURCE_BOOTFS
  local source_rootfs=$SOURCE_ROOTFS

  # check that all variables are set
  if [ -z "$source_device" ] || [ -z "$source_bootfs" ] || [ -z "$source_rootfs" ]; then
    echo_red "ERROR: Source device and directories must be set before mounting."
    exit 1
  fi

  echo_blue "Mounting ${source_device}1 to $source_bootfs"
  sudo mount "${source_device}1" "$source_bootfs"
  echo_blue "Mounting ${source_device}2 to $source_rootfs"
  sudo mount "${source_device}2" "$source_rootfs"

  echo_blue "Newly mounted source boot directory: $source_bootfs"
  ls "$source_bootfs"
  echo_blue "Newly mounted source root directory: $source_rootfs"
  ls "$source_rootfs"
}

mount_target_device() {
  echo_blue "mount_target_device : $TARGET_DEVICE to $TARGET_BOOTFS and $TARGET_ROOTFS"
  local target_device=$TARGET_DEVICE
  local target_bootfs=$TARGET_BOOTFS
  local target_rootfs=$TARGET_ROOTFS

  # check that all variables are set
  if [ -z "$target_device" ] || [ -z "$target_bootfs" ] || [ -z "$target_rootfs" ]; then
    echo_red "ERROR: Target device and directories must be set before mounting."
    exit 1
  fi

  echo_blue "Mounting ${target_device}1 to $target_bootfs"
  sudo mount "${target_device}1" "$target_bootfs"
  echo_blue "Mounting ${target_device}2 to $target_rootfs"
  sudo mount "${target_device}2" "$target_rootfs"

  echo_blue "Newly mounted target boot directory: $target_bootfs"
  ls "$target_bootfs"
  echo_blue "Newly mounted target root directory: $target_rootfs"
  ls "$target_rootfs"
  return 0
}

# Function to use Raspberry Pi Imager to write an image to the target device
create_with_rpi_imager() {
  local image_file=$1
  local target_device=$2

  echo_blue "create_with_rpi_imager $image_file $target_device"

  echo "Writing image $image_file to $target_device using rpi-imager..."
  sudo rpi-imager --cli "$image_file" "$target_device"

  if [ $? -ne 0 ]; then
    echo_red "Failed to write image to $target_device using rpi-imager."
    exit 1
  else
    echo_green "Image successfully written to $target_device using rpi-imager."
  fi

  #    echo "Running partprobe to update the kernel..."
  #    sudo partprobe "$target_device"
  #    if [ $? -ne 0 ]; then
  #        echo_red "Error running partprobe on $target_device."
  #        exit 1
  #    fi
  #
  #    echo "Running kpartx to ensure partitions are recognized..."
  #    sudo kpartx -u "$target_device"
  #    if [ $? -ne 0 ]; then
  #        echo_red "Error running kpartx on $target_device."
  #        exit 1
  #    fi

  echo_green "Image written and device partitions updated successfully."
}

# Function to list potential source and destination partitions
list_partitions() {
  echo_blue "list_partitions"
  lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT | grep -E 'sd|mmcblk'
}

# Function to display a progress bar for dd and handle size mismatch gracefully
copy_device_with_dd() {
  echo_blue "copy_device_with_dd"
  echo_blue "Source device: $SOURCE_DEVICE , Target device: $TARGET_DEVICE"
  local src_dev=$SOURCE_DEVICE
  local dst_dev=$TARGET_DEVICE
  local sec_img=$SOURCE_IMAGE

  # source device defined ? use this dd command
  if [ -n "$src_dev" ]; then
    echo_blue "Source device $src_dev defined. Using dd to copy... to $dst_dev"
    time sudo dd if="$src_dev" of="$dst_dev" bs=4M status=progress conv=fsync iflag=fullblock oflag=direct 2>&1 | grep -v 'No space left on device' || true
  # source image defined ? use this pv command
  elif [ -n "$src_img" ]; then
    echo_blue "Source image $src_img defined. Using pv to copy... to $dst_dev"
    time sudo pv "$src_img" | sudo dd of="$dst_dev" bs=4M

  # no source device or image defined ? error
  else
    echo_red "ERROR: No source device or image defined. Cannot copy"
    exit 1
  fi

  # ensure all data written to the device
  sync

  # check that the source and dest folders are identical
  if ! check_copy_correct; then
    echo_red "ERROR: Copy verification failed"
    return 1
  fi
  return 0
}

resize_partition() {
  local partition="$1"
  local size="$2"

  echo_blue "Function: resize_partition, Arguments: partition=$partition, size=$size"

  if [ -z "$partition" ] || [ -z "$size" ]; then
    echo "Usage: resize_partition <partition> <size>"
    return 1
  fi

  # Unmount the partition
  echo "Unmounting $partition..."
  sudo umount "$partition"

  # Check the filesystem
  echo "Checking the filesystem on $partition..."
  sudo e2fsck -f "$partition"

  # Resize the filesystem to the specified size
  echo "Resizing the filesystem on $partition to $size..."
  sudo resize2fs "$partition" "$size"
  if [ $? -ne 0 ]; then
    echo "Error resizing the filesystem."
    return 1
  fi

  # Resize the partition
  echo "Resizing the partition $partition to $size..."
  sudo parted "${partition%[0-9]*}" --script resizepart "${partition##*[!0-9]}" "$size"
  if [ $? -ne 0 ]; then
    echo "Error resizing the partition."
    return 1
  fi

  echo "Partition resize completed."
  return 0
}

# Example call to the function
# resize_partition /dev/sda2 10GB

# Function to force unmount all partitions of a device
force_unmount_device() {
  echo_blue "force_unmount_device $@"
  local device=$1
  local partitions=$(lsblk -ln -o NAME "$device" | grep -E '^sd|^mmcblk')

  for part in $partitions; do
    mountpoint=$(lsblk -o MOUNTPOINT -n "/dev/$part")
    if [ -n "$mountpoint" ]; then
      echo_blue "Unmounting /dev/$part..."
      sudo umount "/dev/$part" 2>/dev/null || echo_red "Failed to unmount /dev/$part"
    fi
  done
}

# Function to play a finish sound
play_finish_sound() {
  echo_blue "play_finish_sound"
  ffplay -nodisp -autoexit -loop 0 copy_finished.mp3
}

# Function to check the hostname of the target device
check_hostname() {
  echo_blue "check_hostname"
  local target_mount=$TARGET_ROOTFS
  local expected_hostname=$NEW_HOSTNAME
  local actual_hostname=$(sudo cat "$target_mount/etc/hostname")
  if [ "$actual_hostname" != "$expected_hostname" ]; then
    echo_red "ERROR: Hostname mismatch! Expected: '$expected_hostname', but found: '$actual_hostname'"
    return 1
  fi
  echo_green "The hostname on the target device is correct: '$actual_hostname' == '$expected_hostname'"

  # Check the last line of /etc/hosts
  last_line=$(tail -n 1 /etc/hosts)

  # Verify the last line with a regular expression
  if echo "$last_line" | grep -qE "^127\.0\.1\.1[[:space:]]+$new_hostname$"; then
    echo "The last line is correct: '$last_line'"
  else
    echo "The last line is incorrect. : '$last_line' should be '127.0.1.1 $new_hostname'"
    return 1
  fi

  echo_green "hostname check OK"
  return 0
}

# Function to display a confirmation prompt with summary information
confirmation_prompt() {
  echo_blue "confirmation_prompt"
  local source_device=$SOURCE_DEVICE
  local target_device=$TARGET_DEVICE
  local new_hostname=$NEW_HOSTNAME

  # Get summary information for source and target devices
  local source_info=$(lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT "$source_device")
  local target_info=$(lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT "$target_device")

  # Display confirmation prompt
  echo_yellow "The following actions will be performed:"
  # if source device, mount it to the source directories
  if [ -n "$source_device" ]; then
    echo_yellow "- Mount source device $source_device to $SOURCE_BOOTFS and $SOURCE_ROOTFS"
    echo_yellow "Source Device Summary:"
    echo_yellow "$source_info"
  else
    echo_yellow "- (No source device specified. Will read from $SOURCE_BOOTFS and $SOURCE_ROOTFS)"
  fi
  # if KEEP_TARGET_PARTITIONS, keep the target partitions
  if [ "$KEEP_TARGET_PARTITIONS" = true ]; then
    echo_yellow "- (Keep existing partitions on target device $target_device)"
  # if RPI_IMAGE, write it to the target device
  elif [ -n "$RPI_IMAGE" ]; then
    echo_yellow "- Write image $RPI_IMAGE to target device $target_device"
    echo_yellow "- Resize root partition to $RPI_ROOTFS_NEW_SIZE"
  # if target device, wipe it, create partitions, mount them
  elif [ -n "$target_device" ]; then
    echo_yellow "- Wipe all partitions on target device $target_device"
    echo_yellow "- Create new partitions on target device $target_device"
  else
    echo_yellow "- (No target device specified.)"
  fi

  # if TARGET_DEVICE, display info
  if [ -n "$TARGET_DEVICE" ]; then
    echo_yellow "Target Device Summary:"
    echo_yellow "$target_info"
  fi

  # if not DONT_COPY, copy the source to the target
  if [ "$DONT_COPY" = false ]; then
    echo_yellow "- Copy data from $SOURCE_BOOTFS and $SOURCE_ROOTFS to $TARGET_BOOTFS and $TARGET_ROOTFS"
  else
    echo_yellow "- (Skipping the copy process.)"
  fi

  # if not SKIP_CHECK, check the copy correctness
  if [ "$SKIP_CHECK" = false ]; then
    echo_yellow "- Verify the copy correctness"
  else
    echo_yellow "- (Skipping the copy verification.)"
  fi

  # if not DONT_CHANGE_HOSTNAME, change the hostname
  if [ "$DONT_CHANGE_HOSTNAME" = false ]; then
    echo_yellow "- Change the hostname to $new_hostname"
  fi

  if [ "$AUTO_CONFIRM" = false ]; then
    read -p "Do you want to proceed with these steps ? (yes/no): " confirmation
  else
    confirmation="yes"
  fi
  if [ "$confirmation" != "yes" ]; then
    echo_red "Operation aborted."
    exit 0
  fi
}
# Function to wipe all partitions on the target device using parted
wipe_partitions_on_device() {
  echo_blue "wipe_partitions_on_device $@"
  local target_device=$1

  # List contents of the target device
  echo "Current partitions and data on $target_device:"
  lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT "$target_device"

  # Confirmation prompt
  echo "You are about to wipe all partitions on the target device: $target_device."
  echo "This will remove all data from the device and cannot be undone."
  echo "The following steps will be performed:"
  echo "1. Force unmount all partitions on $target_device."
  echo "2. Create a new partition table using parted."
  read -p "Do you want to proceed? (yes/no): " confirmation

  if [ "$confirmation" != "yes" ]; then
    echo "Operation aborted."
    exit 0
  fi

  echo_blue "Forcing unmount of all partitions on $target_device..."
  force_unmount_device "$target_device"

  echo_blue "Creating a new partition table using parted..."
  sudo parted "$target_device" mklabel gpt
  if [ $? -ne 0 ]; then
    echo_red "Error creating new partition table with parted."
    exit 1
  fi

  echo_blue "Running partprobe..."
  sudo partprobe "$target_device"
  if [ $? -ne 0 ]; then
    echo_red "Error running partprobe on $target_device."
    exit 1
  fi

  echo_blue "Running kpartx..."
  sudo kpartx -u "$target_device"
  if [ $? -ne 0 ]; then
    echo_red "Error running kpartx on $target_device."
    exit 1
  fi

  echo_blue "Checking the target device after wiping..."
  sudo parted "$target_device" print
  if sudo parted "$target_device" print | grep -q "Error"; then
    echo_red "Error: Partitions were not successfully wiped on $target_device."
    sudo parted "$target_device" print
    exit 1
  else
    echo_green "Partitions successfully wiped on $target_device."
  fi
}

create_target_partitions() {
  echo_blue "create_target_partitions $@"
  local target_device=$1

  echo_blue "Creating new GPT partition table on $target_device..."
  sudo parted "$target_device" --script mklabel gpt
  if [ $? -ne 0 ]; then
    echo_red "Error creating new partition table with parted."
    exit 1
  fi

  echo_blue "Creating boot partition..."
  sudo parted "$target_device" --script mkpart primary fat32 1MiB ${TARGET_BOOTFS_SIZE}
  if [ $? -ne 0 ]; then
    echo_red "Error creating boot partition with parted."
    exit 1
  fi

  echo_blue "Creating root partition..."
  sudo parted "$target_device" --script mkpart primary ext4 ${TARGET_BOOTFS_SIZE} 100%
  if [ $? -ne 0 ]; then
    echo_red "Error creating root partition with parted."
    exit 1
  fi

  echo_blue "Running partprobe to update the kernel..."
  sudo partprobe "$target_device"
  if [ $? -ne 0 ]; then
    echo_red "Error running partprobe on $target_device."
    exit 1
  fi

  echo_blue "Checking if partitions are available..."
  while ! lsblk -o NAME | grep -q "$(basename $target_device)1"; do
    echo_red "Partition ${target_device}1 not yet found, waiting..."
    sleep 1
  done

  while ! lsblk -o NAME | grep -q "$(basename $target_device)2"; do
    echo_red "Partition ${target_device}2 not yet found, waiting..."
    sleep 1
  done

  echo_blue "Ensuring partitions are not in use..."
  sudo umount "${target_device}1" || true
  sudo umount "${target_device}2" || true

  echo_blue "Making filesystems on new partitions..."
  for i in {1..5}; do
    sudo mkfs.vfat "${target_device}1" && break
    echo_red "Error creating FAT32 filesystem on ${target_device}1, retrying ($i/5)..."
    sleep 2
  done
  if [ $? -ne 0 ]; then
    echo_red "Error creating FAT32 filesystem on ${target_device}1."
    exit 1
  fi

  for i in {1..5}; do
    sudo mkfs.ext4 "${target_device}2" && break
    echo_red "Error creating ext4 filesystem on ${target_device}2, retrying ($i/5)..."
    sleep 2
  done
  if [ $? -ne 0 ]; then
    echo_red "Error creating ext4 filesystem on ${target_device}2."
    exit 1
  fi

  echo_blue "Running partprobe again to ensure the partitions are recognized..."
  sudo partprobe "$target_device"
  if [ $? -ne 0 ]; then
    echo_red "Error running partprobe on $target_device."
    exit 1
  fi

  sudo kpartx -u "$target_device"
  if [ $? -ne 0 ]; then
    echo_red "Error running kpartx on $target_device."
    exit 1
  fi

  echo_blue "Checking the target device partitions..."
  if lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT "$target_device" | grep -q "vfat"; then
    echo_green "Boot partition successfully created on $target_device."
  else
    echo_red "Failed to create boot partition on $target_device."
    exit 1
  fi

  if lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT "$target_device" | grep -q "ext4"; then
    echo_green "Root partition successfully created on $target_device."
  else
    echo_red "Failed to create root partition on $target_device."
    exit 1
  fi
}

fast_copy_directory() {
  echo_blue "fast_copy_directory $@"
  local source_dir=$1
  local target_dir=$2

  # remove the `/` at the end if there is one
  source_dir=${source_dir%/}
  target_dir=${target_dir%/}

  # wipe the destination's contents
  sudo rm -rf "$target_dir"/*
  #  sudo rsync -aHAX --info=progress2 "$source_dir/" "$target_dir/"
  #  sudo rsync -a --progress "$source_dir/" "$target_dir/"
  sudo rsync -a --delete --log-file=rsync_log.txt "$source_dir" "$target_dir" >/dev/null 2>&1 | tee rsync_errors.txt

}

# Function to copy data from source to target with progress indication
fast_copy_device() {
  echo_blue "fast_copy_device $@"
  local source_device=$1
  local target_device=$2

  wipe_partitions_on_device "$target_device"
  create_target_partitions "$target_device"

  local source_bootfs="$SOURCE_BOOTFS"
  local source_rootfs="$SOURCE_ROOTFS"
  local target_bootfs="$TARGET_BOOTFS"
  local target_rootfs="$TARGET_ROOTFS"

  local source_bootfs_size=$(df -B1 --output=used "$source_bootfs" | tail -n1)
  local source_rootfs_size=$(df -B1 --output=used "$source_rootfs" | tail -n1)
  local target_bootfs_size=$(lsblk -bn -o SIZE "$target_bootfs")
  local target_rootfs_size=$(lsblk -bn -o SIZE "$target_rootfs")

  if [ "$source_bootfs_size" -gt "$target_bootfs_size" ] || [ "$source_rootfs_size" -gt "$target_rootfs_size" ]; then
    echo_red "ERROR: The target device does not have enough space to accommodate the source data."
    exit 1
  fi

  mount_source_device

  # Check the mounted source directories
  check_source_directories_contents "$source_bootfs" "$source_rootfs" "$target_bootfs" "$target_rootfs"

  mount_target_device

  echo_blue "Copying boot partition..."
  fast_copy_directory "$source_bootfs" "$target_bootfs" || exit 1

  echo_blue "Copying root partition..."
  fast_copy_directory "$source_rootfs" "$target_rootfs" || exit 1
}

compare_dirs_by_file_checksums() {
  local src_dir=$1
  local dst_dir=$2

  # Define checksum file paths
  local script_dir=$(dirname "$0")
  # Memorize current directory
  local current_dir=$(pwd)
  local checksums_dir="/tmp"
  local src_checksum_file="$checksums_dir/src_checksums.txt"
  local dst_checksum_file="$checksums_dir/dst_checksums.txt"

  # Generate checksums for the source directory with relative paths
  cd "$src_dir"
  echo_blue "Building checksums for $src_dir..."
  sudo find . -type f -exec sha256sum {} + | sort >"$src_checksum_file"
  # Generate checksums for the destination directory with relative paths
  cd "$dst_dir"
  echo_blue "Building checksums for $dst_dir..."
  sudo find . -type f -exec sha256sum {} + | sort >"$dst_checksum_file"

  # Return to the original directory
  cd "$current_dir"

  # Compare the checksum files
  diff "$src_checksum_file" "$dst_checksum_file"

  # Check for differences and print appropriate message
  if [ $? -ne 0 ]; then
    echo_red "ERROR: Differences found between $src_dir and $dst_dir."
    return 1
  fi
  echo_green "$src_dir and $dst_dir are identical."
  return 0
}

check_copy_correct() {
  echo_blue "check_copy_correct"
  local source_bootfs=$SOURCE_BOOTFS
  local source_rootfs=$SOURCE_ROOTFS
  local target_bootfs=$TARGET_BOOTFS
  local target_rootfs=$TARGET_ROOTFS

  # use compare_dirs_by_file_checksums to check the contents of the source and destination directories
  if ! compare_dirs_by_file_checksums "$source_bootfs" "$target_bootfs"; then
    echo_red "Boot partition contents differ."
    return 1
  fi

  # use compare_dirs_by_file_checksums to check the contents of the source and destination directories
  if ! compare_dirs_by_file_checksums "$source_rootfs" "$target_rootfs"; then
    echo_red "Root partition contents differ."
    return 1
  fi

  echo_green "Boot and root partition contents are identical."
  return 0
}

# Function to check if the contents of the source and destination are the same
old_check_copy_correct() {
  echo_blue "check_copy_correct"
  local source_bootfs=$SOURCE_BOOTFS
  local source_rootfs=$SOURCE_ROOTFS
  local target_bootfs=$TARGET_BOOTFS
  local target_rootfs=$TARGET_ROOTFS

  # boot partitions should be the same
  echo_blue "Checking boot partition copy correctness..."
  if diff -rq "$source_bootfs" "$target_bootfs"; then
    echo_green "Boot partition contents are identical."
  else
    echo_red "Boot partition contents differ."
    return 1
  fi

  # root partitions should be the same except for the file /etc/hostname, which should have the new hostname
  echo_blue "Checking root partition copy correctness..."
  local diff_found=false

  if [ "$STOP_CHECK_AT_FIRST_DIFF" = true ]; then
    echo_yellow "Stopping at the first difference found."

    while read -r line; do
      echo_red "Root partition contents differ: $line"
      diff_found=true
      break
    done < <(diff -r "$source_rootfs" "$target_rootfs" --exclude=hostname 2>&1)
  else
    if ! diff -rq "$source_rootfs" "$target_rootfs" --exclude=hostname; then
      echo_red "Root partition contents differ."
      diff_found=true
    fi
  fi

  if [ "$diff_found" = true ]; then
    return 1
  fi

  echo_green "No differences found."
  echo_green "Copy verification completed successfully."
  return 0
}

# Function to check and display contents of mounted directories
check_source_directories_contents() {
  echo_blue "check_source_directories_contents $@"
  local bootfs_dir=$1
  local rootfs_dir=$2
  local fail=false

  echo "Checking source directories in $bootfs_dir and $rootfs_dir:"

  # if a source device a specified, mount
  if [ -n "$SOURCE_DEVICE" ]; then
    mount_source_device
  fi

  # Check root directory for required directories
  for dir in boot bin dev home; do
    if [ ! -d "$rootfs_dir/$dir" ]; then
      echo_red "ERROR: Directory $dir is missing in $rootfs_dir"
      fail=true
    fi
  done

  # Check boot directory for required files
  for file in kernel_2712.img kernel8.img; do
    if [ ! -f "$bootfs_dir/$file" ]; then
      echo_red "ERROR: File $file is missing in $bootfs_dir"
      fail=true
    fi
  done

  if [ "$fail" = true ]; then
    echo_red "ERROR: Required directories or files are missing"
    exit 1
  else
    echo_green "All required directories and files are present"
  fi
}

change_target_hostname() {
  echo_blue "change_target_hostname"
  local target_mount=$TARGET_ROOTFS
  local new_hostname=$NEW_HOSTNAME

  echo "Changing the hostname to $new_hostname..."
  echo "$new_hostname" | sudo tee "$target_mount/etc/hostname"
  sudo sed -i "s/$(hostname)/$new_hostname/g" "$target_mount/etc/hosts"

  # change the /etc/hosts file: the last line should be the new hostname
  # example of /etc/hosts file:
  #  127.0.0.1	localhost
  #  ::1		localhost ip6-localhost ip6-loopback
  #  ff02::1		ip6-allnodes
  #  ff02::2		ip6-allrouters
  #
  #  127.0.1.1	cubebox1
  # in this example, we should replace the last line with "127.0.1.1 $new_hostname"
  # we can do this by using sed to replace the last line
  # the command to do this is:
  sudo sed -i '$s/.*/127.0.1.1\tcubebox2/' /etc/hosts

  check_hostname "$target_mount" "$new_hostname"
}

# -------------
# MAIN FUNCTION
# -------------
main_function() {
  echo_blue "main_function"
  confirmation_prompt || exit 0

  # if SOURCE_DEVICE is set, we mount it
  if [ -n "$SOURCE_DEVICE" ]; then
    echo_blue "Mounting source device $SOURCE_DEVICE..."
    mount_source_device
  fi

  echo_blue "Checking source boot and root directories..."
  check_source_directories_contents "$SOURCE_BOOTFS" "$SOURCE_ROOTFS" || exit 1
  echo_blue "Checking target boot and root directories..."
  check_source_directories_contents "$TARGET_BOOTFS" "$TARGET_ROOTFS" || exit 1

  if [ "$KEEP_TARGET_PARTITIONS" = false ]; then
    if [ -n "$RPI_IMAGE" ]; then
      create_with_rpi_imager "$RPI_IMAGE" "$TARGET_DEVICE"
      resize_partition "${TARGET_DEVICE}2" "$RPI_ROOTFS_NEW_SIZE"
    else
      # Wipe partitions on the target device
      wipe_partitions_on_device "$TARGET_DEVICE"

      # Create new partitions on the target device
      create_target_partitions "$TARGET_DEVICE"
    fi
  fi

  # Start timing the copy process
  START_TIME=$(date +%s)

  if [ "$DONT_COPY" = true ]; then
    echo_blue "Skipping the copy process."
  elif [ -n "$SOURCE_DEVICE" ]; then
    echo_blue "Copying $SOURCE_SOURCE_DEVICE to $TARGET_DEVICE..."
    # Copy contents from source to target with progress
    fast_copy_device "$SOURCE_DEVICE" "$TARGET_DEVICE"
  else
    echo_blue "Copying source bootfs..."
    fast_copy_directory "$SOURCE_BOOTFS" "$TARGET_BOOTFS"
    echo_blue "Copying source rootfs..."
    fast_copy_directory "$SOURCE_ROOTFS" "$TARGET_ROOTFS"

  fi

  if [ "$DONT_CHANGE_HOSTNAME" = false ]; then
    echo_blue "Changing the hostname to $NEW_HOSTNAME..."
    change_target_hostname
  fi

  # End timing the copy process
  END_TIME=$(date +%s)
  TOTAL_TIME=$((END_TIME - START_TIME))
  echo "Total copy time: $TOTAL_TIME seconds"

  # Verify the copy if not skipped
  if [ "$SKIP_CHECK" = false ]; then

    if check_copy_correct; then
      echo_green "The data has been copied correctly."
    else
      echo_red "The data copy has some differences."
      exit 1
    fi
    if check_hostname; then
      echo_green "The hostname is correct."
    else
      echo_red "The hostname is incorrect"
      exit 1
    fi
  fi

  echo_green "Done! The SD card has been copied and the hostname has been changed to $NEW_HOSTNAME."
  echo "Total time taken: $TOTAL_TIME seconds."

  # Play a finish sound
  if [ "$SKIP_SOUND" = false ]; then
    play_finish_sound
  fi
}

# Create necessary directories for mounts
echo_blue "Creating necessary directories for mounts"
# wtf is this shit doing here still
#sudo mkdir -p /mnt/source_boot /mnt/source_root /mnt/target_boot /mnt/target_root

# Run the script
handle_arguments "$@"
main_function
