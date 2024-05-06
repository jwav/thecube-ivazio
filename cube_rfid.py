"""
This module handles everything RFID-related for the CubeBox
"""

import threading
import time
from pynput import keyboard
from collections import deque

AZERTY_DICT = {
    '&': '1', 'é': '2', '"': '3', "'": '4', '(': '5',
    '-': '6', 'è': '7', '_': '8', 'ç': '9', 'à': '0'}


def on_press(key):
    try:
        print(f'Key {key.char} pressed')
    except AttributeError:
        print(f'Key {key} with keycode {key.value.vk} pressed')


class CubeRfidLine:
    UID_LENGTH = 10
    """Represents a line of RFID data entered by the user with a timestamp"""
    def __init__(self, timestamp:float, line: str):
        self.timestamp = timestamp
        self.line = line

    def is_valid(self):
        return len(self.line) == self.UID_LENGTH and all([char.isdigit() for char in self.line])

class CubeRfidListener:
    def __init__(self):
        self.current_chars_buffer = deque()  # Use deque for efficient pop/append operations
        self.completed_lines = deque()  # Store completed lines with their timestamps
        self.lock = threading.Lock()  # Lock for thread-safe access to keycodes
        self.listener = keyboard.Listener(on_press=self.on_press)

    def on_press(self, key):
        try:
            keycode = key.vk  # Get the virtual key code
        except AttributeError:
            keycode = key.value.vk if key.value else None  # Handle special keys
        if keycode is None:
            return
        with self.lock:  # Ensure thread-safe modification of the deque
            # Signal that a new line has been entered
            if key == keyboard.Key.enter:
                self.completed_lines.append(CubeRfidLine(time.time(), "".join(self.current_chars_buffer)))
                self.current_chars_buffer.clear()
            else:
                try:
                    # convert azerty to qwerty is need be
                    char = key.char if key.char not in AZERTY_DICT else AZERTY_DICT[key.char]
                    self.current_chars_buffer.append(char)
                except:
                    pass

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()

    def get_completed_lines(self):
        with self.lock:
            lines = list(self.completed_lines)
            self.completed_lines.clear()
        return lines


if __name__ == "__main__":
    rfid = CubeRfidListener()
    rfid.start()
    try:
        while True:
            if lines := rfid.get_completed_lines():
                for line in lines:
                    print(f"Line entered at {line.timestamp}: {line.line} : {'valid' if line.is_valid() else 'invalid'}")
    except KeyboardInterrupt:
        print("Stopping listener...")
    finally:
        rfid.stop()
