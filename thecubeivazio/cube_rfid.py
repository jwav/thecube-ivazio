"""
This module handles everything RFID-related for the CubeBox
"""
import re
import subprocess

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


def rfid_raw_test():
    import sys
    print("rfid_raw_test()")
    while True:
        line = sys.stdin.readline().strip()
        if line:
            print(f"RFID card UID: {line}")

def get_usb_device_name(vendor_id, product_id):
    # Run lsusb command and capture its output
    lsusb_output = subprocess.check_output(['lsusb']).decode('utf-8')
    print("lsusb_output:", lsusb_output)

    # Construct regex pattern to match the device line
    pattern = r'(\d+:\d+)\s+(.*?)\s+(.*?)$'

    # Search for the device line using regex
    match = re.search(pattern, lsusb_output, re.MULTILINE)

    # Loop through each line of lsusb output
    while match:
        # Check if the vendor and product IDs match
        if vendor_id in match.group(2) and product_id in match.group(2):
            # Extract the device name from the matched line
            device_name = match.group(3)

            # Replace spaces with underscores in device name
            device_name = device_name.replace(' ', '_')

            return device_name

        # Search for the next device line
        match = re.search(pattern, lsusb_output, re.MULTILINE)

    return None

def usb_get_test():
    print("usb_get_test()")
    # Example usage: Get the device name for a specific vendor and product ID
    vendor_id = 'ffff'  # Replace with your actual vendor ID
    product_id = '0035' # Replace with your actual product ID
    device_name = get_usb_device_name(vendor_id, product_id)

    if device_name:
        print(f"USB device name: {device_name}")
    else:
        print("USB device not found.")


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
    # rfid_raw_test()
    usb_get_test()
    exit(0)
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
