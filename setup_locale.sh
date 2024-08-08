#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

# Global variable for locale
LOCALE="en_US"

# Check if locale is already generated
if locale -a | grep -q "${LOCALE}.utf8"; then
    echo_green "Locale ${LOCALE}.UTF-8 is already generated."
else
    echo_blue "Generating locale ${LOCALE}.UTF-8..."

    # Uncomment the locale in /etc/locale.gen
    sudo sed -i "/^#.* ${LOCALE}.UTF-8/s/^#//" /etc/locale.gen

    # Generate the locale
    sudo locale-gen
fi

# Set locale environment variables in /etc/default/locale
echo_blue "Setting locale environment variables..."

sudo tee /etc/default/locale > /dev/null <<EOL
LANG=${LOCALE}.UTF-8
LANGUAGE=${LOCALE}:en
LC_ALL=${LOCALE}.UTF-8
EOL

# Export the variables to the current session
echo_blue "Exporting locale variables to the current session..."
export LANG=${LOCALE}.UTF-8
export LANGUAGE=${LOCALE}:en
export LC_ALL=${LOCALE}.UTF-8

# Add locale settings to .bashrc
echo_blue "Adding locale settings to .bashrc..."
if ! grep -q "export LANG=${LOCALE}.UTF-8" ~/.bashrc; then
    echo "export LANG=${LOCALE}.UTF-8" >> ~/.bashrc
fi
if ! grep -q "export LANGUAGE=${LOCALE}:en" ~/.bashrc; then
    echo "export LANGUAGE=${LOCALE}:en" >> ~/.bashrc
fi
if ! grep -q "export LC_ALL=${LOCALE}.UTF-8" ~/.bashrc; then
    echo "export LC_ALL=${LOCALE}.UTF-8" >> ~/.bashrc
fi

# Verify the locale settings
echo_blue "Verifying locale settings..."
locale

echo_green "Locale setup completed. Please restart your terminal session or source /etc/default/locale to apply the changes system-wide."
