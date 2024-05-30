#!/usr/bin/env bash

# if i omit the led-chain arg, it displays the same image on all panels
python3 ./my_display_text.py --led-cols=64 --led-rows=32 --led-chain=2 --led-slowdown=5
#python3 ./my_display_text_not_working.py --led-cols=64 --led-rows=32 --led-chain=2
#python3 ./my_display_text.py --led-cols=64 --led-rows=32 --led-chain=1

