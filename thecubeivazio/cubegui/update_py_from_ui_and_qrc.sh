#!/bin/sh

pyuic5 cubegui.ui -o cubegui_ui.py
pyrcc5 -o resources_rc.py resources.qrc
