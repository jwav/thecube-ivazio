#!/usr/bin/env bash

sudo apt-get update
sudo apt install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl git

sudo apt-get install software-properties-common
sudo apt-get install python3-pip
sudo apt-get install python3-venv
sudo apt-get install python3-is-python
sudo apt-get install git
sudo apt-get install xvfb
sudo apt-get install x11-utils
# todo: find the remaining packages with a fresh install and test routines

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

pyenv install 3.9.19
pyenv global 3.9.19