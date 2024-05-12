"""
This module handles everything RFID-related for the CubeBox
"""

import thecubeivazio.cube_logger as cube_logger
from thecubeivazio.cube_utils import XvfbManager

import threading
import time
from typing import Union
from collections import deque

# pynput requires an X server to run, so we start a virtual one with XVFB if it's not already running
if not XvfbManager.has_x_server():
    XvfbManager.start_xvfb()
from pynput import keyboard

AZERTY_DICT = {
    '&': '1', 'é': '2', '"': '3', "'": '4', '(': '5',
    '-': '6', 'è': '7', '_': '8', 'ç': '9', 'à': '0'}


class CubeRfidLine:
    UID_LENGTH = 10
    """Represents a line of RFID data entered by the user with a timestamp"""

    def __init__(self, timestamp: float, uid: str):
        self.timestamp = timestamp
        self.uid = uid

    def is_valid(self):
        return len(self.uid) == self.UID_LENGTH and all([char.isdigit() for char in self.uid])


class CubeRfidListener:
    def __init__(self):
        self.log = cube_logger.make_logger("RFID Listener")
        self.current_chars_buffer = deque()  # Use deque for efficient pop/append operations
        self.completed_lines = deque()  # Store completed lines with their timestamps
        self.lock = threading.Lock()  # Lock for thread-safe access to keycodes
        self.listener = keyboard.Listener(on_press=self.on_press)

    def on_press(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        try:
            keycode = key.vk  # Get the virtual key code
        except AttributeError:
            keycode = key.value.vk if key.value else None  # Handle special keys
        if keycode is None:
            return
        with self.lock:  # Ensure thread-safe modification of the deque
            # noinspection PyBroadException
            try:
                # Signal that a new line has been entered
                if key == keyboard.Key.enter:
                    newline = CubeRfidLine(time.time(), "".join(self.current_chars_buffer))
                    self.current_chars_buffer.clear()
                    if newline.is_valid():
                        self.completed_lines.append(newline)
                        self.log.info(f"Valid RFID line entered: {newline.uid}")
                    else:
                        self.log.error(f"Invalid RFID line entered: {newline.uid}")
                else:

                    # convert azerty to qwerty is need be
                    char = key.char if key.char not in AZERTY_DICT else AZERTY_DICT[key.char]
                    self.current_chars_buffer.append(char)
            except:
                pass

    def run(self):
        self.listener.start()

    def stop(self):
        print("Stopping RFID listener...")
        self.listener.stop()
        print("RFID listener stopped")

    def get_completed_lines(self):
        with self.lock:
            return list(self.completed_lines)

    def remove_line(self, rfid_line: CubeRfidLine):
        with self.lock:
            self.completed_lines.remove(rfid_line)


if __name__ == "__main__":
    rfid = CubeRfidListener()
    rfid.run()
    rfid.log.info("RFID listener test. Press Ctrl+C to stop.")
    try:
        while True:
            if lines := rfid.get_completed_lines():
                for line in lines:
                    print(f"Line entered at {line.timestamp}: {line.uid} : {'valid' if line.is_valid() else 'invalid'}")
                rfid.completed_lines.clear()
    except KeyboardInterrupt:
        print("Stopping listener...")
    finally:
        rfid.stop()
