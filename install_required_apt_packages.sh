#!/usr/bin/env bash

current_locale=$(locale | grep LANG | cut -d= -f2)
if ! grep -q "en_US.UTF-8" /etc/locale.gen; then
  sudo locale-gen en_US.UTF-8
fi

if [[ "$current_locale" != "en_US.UTF-8" ]]; then
  echo "Setting locale to en_US.UTF-8"
  sudo update-locale LANG=en_US.UTF-8
fi

sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git libgdbm-dev libnss3-dev \
vim software-properties-common python3-pip python3-venv python-is-python3 xvfb x11-utils \
libgraphicsmagick++-dev libwebp-dev libjpeg-dev libpng-dev libtiff-dev libgif-dev \
libossp-uuid-dev chromium-browser alsa-utils



if [ -d "venv" ]; then
    echo "The venv folder exists."
else
    echo "The venv folder does not exist. Creating."
    python3 -m venv venv
fi
# enter the venv
source myenv/bin/activate
pip install --upgrade pip
pip install --upgrade setuptools
pip install --upgrade wheel
pip install pip_search


if command -v pyenv >/dev/null 2>&1; then
  echo "pyenv is installed"
else
  echo "pyenv is not installed"
  curl https://pyenv.run | bash
  export PATH="$HOME/.pyenv/bin:$PATH"
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
fi

if python3.9 --version &> /dev/null
then
  echo "Python 3.9 is installed"
else
  echo "Python 3.9 is not installed"
  pyenv install -v 3.9.19
fi

pyenv global 3.9.19

#deactivate