#!/usr/bin/env bash

this_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${this_script_dir}/thecube_common_defines.sh" || { echo "ERROR: Could not load thecube_common_defines.sh"; exit 1; }


# Check if pyenv is already installed
if command -v pyenv &> /dev/null; then
    echo "pyenv is already installed. Skipping installation."
else
    # Update package list and install dependencies
    sudo apt-get update
    sudo apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git

    # Install pyenv
    curl https://pyenv.run | bash

    # Add pyenv to the shell startup file
    if ! grep -q 'pyenv' ~/.bashrc; then
        echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
        echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
        echo 'eval "$(pyenv init -)"' >> ~/.bashrc
        echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
    fi

    # Apply changes to the current shell session
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
fi

# Install Python 3.9.19
pyenv install -s 3.9.19

# Set Python 3.9.19 as global version
pyenv global 3.9.19

# Verify installation
python --version

echo "pyenv and Python 3.9.19 have been installed and set up successfully."
