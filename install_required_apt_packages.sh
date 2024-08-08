#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

# List of packages
packages=(
    make build-essential libssl-dev zlib1g-dev libbz2-dev openssl
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev
    libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev
    python3-openssl git libgdbm-dev libnss3-dev
    vim software-properties-common python3-pip python3-venv
    python-is-python3 xvfb x11-utils
    libgraphicsmagick++-dev libwebp-dev libjpeg-dev libpng-dev
    libtiff-dev libgif-dev libossp-uuid-dev chromium-browser
    alsa-utils pcmanfm lxsession rustc libssl-dev
)

# Check for missing packages
missing_packages=()
for pkg in "${packages[@]}"; do
    if ! dpkg -l | grep -qw "$pkg"; then
        missing_packages+=("$pkg")
    fi
done

# Install missing packages if any
if [ ${#missing_packages[@]} -gt 0 ]; then
    echo "The following packages are missing and will be installed:"
    for pkg in "${missing_packages[@]}"; do
        echo "- $pkg"
    done
    sudo apt update
    sudo apt install -y "${missing_packages[@]}" || {
        echo "ERROR: Failed to install missing packages."
        exit 1
    }
else
    echo "All packages are already installed."
fi

echo "All required APT packages have been installed successfully."
