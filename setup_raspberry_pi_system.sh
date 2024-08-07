#!/usr/bin/env bash

this_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${this_script_dir}/thecube_common_defines.sh" || { echo "ERROR: Could not load thecube_common_defines.sh"; exit 1; }


echo "Setting up Raspberry Pi system..."
echo "telling the system to boot to the console and not X11"
sudo raspi-config nonint do_boot_behaviour B2

echo "enable SPI"
sudo raspi-config nonint do_spi 0

# Function to check if a module is already loaded at boot
is_module_in_boot() {
    local module=$1
    if grep -q "$module" /etc/modules; then
        return 0
    else
        return 1
    fi
}

# Ensure SPI module is loaded at boot
SPI_MODULE="spi-bcm2835"
if is_module_in_boot "$SPI_MODULE"; then
    echo "$SPI_MODULE is already set to load at boot."
else
    echo "Adding $SPI_MODULE to /etc/modules..."
    echo "$SPI_MODULE" | sudo tee -a /etc/modules
fi

# Load the SPI module immediately
echo "Loading $SPI_MODULE module..."
sudo modprobe $SPI_MODULE

# Verify SPI device
SPI_DEVICE="/dev/spidev0.0"
if [ -e "$SPI_DEVICE" ]; then
    echo "SPI device $SPI_DEVICE is present."
else
    echo "ERROR: SPI device $SPI_DEVICE is not present."
    exit 1
fi

echo_blue "SPI setup completed successfully."

echo_blue "Setting up sound"
bash ./setup_rpi_audio.sh
