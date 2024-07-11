#!/bin/bash

# Vendor ID and Product ID of the RFID reader
RFID_VENDOR_ID="ffff"
RFID_PRODUCT_ID="0035"

# Function to disable a device by its path
disable_device() {
  local device_path="$1"
  echo "Disabling device at $device_path"
  echo "0" | sudo tee "$device_path/authorized" > /dev/null
}

# Disable existing devices
for device_path in /sys/bus/usb/devices/*; do
  if [ -f "$device_path/idVendor" ] && [ -f "$device_path/idProduct" ]; then
    vendor_id=$(cat "$device_path/idVendor")
    product_id=$(cat "$device_path/idProduct")
    if [ "$vendor_id" != "$RFID_VENDOR_ID" ] || [ "$product_id" != "$RFID_PRODUCT_ID" ]; then
      disable_device "$device_path"
    fi
  fi
done
