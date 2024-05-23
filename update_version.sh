#!/usr/bin/bash
source venv/bin/activate && git pull && pip install -r requirements.txt && python3 install .
