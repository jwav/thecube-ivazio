#!/usr/bin/python3

"""
This module handles everything RFID-related for the CubeBox
"""
import logging
import os
import re
import subprocess

import thecubeivazio.cube_logger as cube_logger
from thecubeivazio.cube_utils import XvfbManager

import threading
import time
from typing import Union
from collections import deque

import evdev

# pynput requires an X server to run, so we start a virtual one with XVFB if it's not already running
if not XvfbManager.has_x_server():
    XvfbManager.start_xvfb()
from pynput import keyboard



AZERTY_DICT = {
    '&': '1', 'é': '2', '"': '3', "'": '4', '(': '5',
    '-': '6', 'è': '7', '_': '8', 'ç': '9', 'à': '0'}









def test_evdev():
    from evdev import InputDevice, categorize, ecodes
    device_path = "/dev/input/event258"

    # Create an InputDevice object for the specified device
    device = InputDevice(device_path)

    try:
        # Continuously read events from the device
        for event in device.read_loop():
            # Check if the event is a key event
            if event.type == ecodes.EV_KEY:
                # Print the key event
                print(categorize(event))

    except KeyboardInterrupt:
        # Stop the function if KeyboardInterrupt (Ctrl+C) is detected
        pass

class CubeRfidLine:
    UID_LENGTH = 10
    """Represents a line of RFID data entered by the user with a timestamp"""

    def __init__(self, timestamp: float, uid: str):
        self.timestamp = timestamp
        self.uid = uid

    def is_valid(self):
        return len(self.uid) == self.UID_LENGTH and all([char.isdigit() for char in self.uid])


class CubeRfidEventListener:
    """Listens for RFID events and stores the entered lines"""
    BY_ID_PATH = "/dev/input/by-id/"
    DEV_INPUT_PATH = "/dev/input/"
    ECODES_TO_STR_DIGIT_DICT = {
        evdev.ecodes.KEY_1: '1', evdev.ecodes.KEY_2: '2', evdev.ecodes.KEY_3: '3', evdev.ecodes.KEY_4: '4', evdev.ecodes.KEY_5: '5',
        evdev.ecodes.KEY_6: '6', evdev.ecodes.KEY_7: '7', evdev.ecodes.KEY_8: '8', evdev.ecodes.KEY_9: '9', evdev.ecodes.KEY_0: '0'
    }

    def __init__(self):
        self._is_setup = False
        self.log = cube_logger.make_logger("RFID Event Listener")
        self.log.setLevel(logging.INFO)

        self._current_chars_buffer = deque()
        self._completed_lines = deque()  # Store completed lines with their timestamps
        self._lines_lock = threading.Lock()  # Lock for thread-safe access to keycodes

        self._thread = None
        self._keep_running = True

        self._device_path = self.get_input_device_path_from_device_name("RFID")
        if self._device_path is None:
            self.log.error("No RFID input device found")
            raise FileNotFoundError("No RFID input device found")

        # Create an InputDevice object for the specified device
        try:
            self._device = evdev.InputDevice(self._device_path)
        except:
            self.log.error("Could not create InputDevice object for RFID reader")
            raise

        self._is_setup = True

    def is_setup(self):
        return self._is_setup

    def run(self):
        self._thread = threading.Thread(target=self._event_read_loop)
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self._keep_running = False
        self._thread.join(timeout=0.5)

    def get_completed_lines(self):
        with self._lines_lock:
            return list(self._completed_lines)

    def remove_line(self, rfid_line: CubeRfidLine):
        with self._lines_lock:
            self._completed_lines.remove(rfid_line)

    def _event_read_loop(self):
        while self._keep_running:
            try:
                # Continuously read events from the device
                for event in self._device.read_loop():
                    # Check if the event is a key event
                    if event.type == evdev.ecodes.EV_KEY:
                        # Print the key event for debug
                        #print(evdev.categorize(event))
                        # we only care about key up events
                        if self.is_event_key_up(event):
                            # if the event is the enter key, we have a complete line
                            if self.is_event_enter_key(event):
                                newline = CubeRfidLine(time.time(), "".join(self._current_chars_buffer))
                                self._current_chars_buffer.clear()
                                if newline.is_valid():
                                    with self._lines_lock:
                                        self._completed_lines.append(newline)
                                    self.log.info(f"Valid RFID line entered: {newline.uid}")
                                else:
                                    self.log.error(f"Invalid RFID line entered: {newline.uid}")
                            # if the event is a digit key, we add it to the buffer
                            elif self.is_event_digit_key(event):
                                digit_str = self.event_to_digit_str(event)
                                self._current_chars_buffer.append(digit_str)
            except Exception as e:
                self.log.error(f"Error reading RFID events: {e}")



    @staticmethod
    def is_event_enter_key(event: evdev.InputEvent):
        # return event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.KEY_ENTER and event.value == evdev.events.KeyEvent.key_up
        return event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.KEY_ENTER

    @staticmethod
    def is_event_digit_key(event: evdev.InputEvent):
        return event.type == evdev.ecodes.EV_KEY and event.code in CubeRfidEventListener.ECODES_TO_STR_DIGIT_DICT

    @staticmethod
    def is_event_key_up(event):
        return event.type == evdev.ecodes.EV_KEY and event.value == evdev.events.KeyEvent.key_up

    @staticmethod
    def event_to_digit_str(event : evdev.InputEvent):
        if not event.code in CubeRfidEventListener.ECODES_TO_STR_DIGIT_DICT:
            return None
        return CubeRfidEventListener.ECODES_TO_STR_DIGIT_DICT[event.code]

    @staticmethod
    def get_input_device_path_from_device_name(name):
        import os
        import fnmatch
        by_id_path = CubeRfidEventListener.BY_ID_PATH
        dev_input_path = CubeRfidEventListener.DEV_INPUT_PATH
        for filename in os.listdir(by_id_path):
            if fnmatch.fnmatch(filename, f'*{name}*'):
                symlink_path = os.path.join(by_id_path, filename)
                if os.path.islink(symlink_path):
                    full_input_path = os.path.join(dev_input_path, os.path.basename(os.readlink(symlink_path)))
                    return full_input_path
        return None


class CubeRfidKeyboardListener:
    def __init__(self):
        self.log = cube_logger.make_logger("RFID Keyboard Listener")
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
    #rfid = CubeRfidKeyboardListener()
    rfid = CubeRfidEventListener()
    if rfid.is_setup():
        print("RFID listener setup successful:", rfid._device_path)
    rfid.run()
    rfid.log.info("RFID listener test. Press Ctrl+C to stop.")
    try:
        while True:
            if lines := rfid.get_completed_lines():
                for line in lines:
                    print(f"Line entered at {line.timestamp}: {line.uid} : {'valid' if line.is_valid() else 'invalid'}")
                rfid._completed_lines.clear()
    except KeyboardInterrupt:
        print("Stopping listener...")
    finally:
        rfid.stop()
