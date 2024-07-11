#!/usr/bin/env bash

# hide mouse cursor
/usr/bin/unclutter -idle 1 -root &

sudo systemctl stop thecubeivazio.cubemaster.service
sudo systemctl start thecubeivazio.cubemaster.service
#sudo systemctl status thecubeivazio.cubemaster.service
