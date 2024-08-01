#!/bin/sh
cd ~
curl https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.sh >rgb-matrix.sh
sudo bash rgb-matrix.sh
sudo apt-get update && sudo apt-get install python3-dev python3-pillow -y
cd rpi-rgb-led-matrix/bindings/python
make build-python
sudo make install-python
cd bindings/python
sudo python3 setup.py install
