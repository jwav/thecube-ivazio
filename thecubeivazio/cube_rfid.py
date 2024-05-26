#!/usr/bin/python3

"""
This module handles everything RFID-related for the CubeBox
"""
import logging
import os
import re
import subprocess

import thecubeivazio.cube_logger as cube_logger
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_utils import XvfbManager

import threading
import time
from typing import Union, List, Optional
from collections import deque

import evdev

# pynput requires an X server to run, so we start a virtual one with XVFB if it's not already running
if not XvfbManager.has_x_server():
    XvfbManager.start_xvfb()
from pynput import keyboard


class CubeRfidLine:
    VALID_UID_LENGTH = 10
    """Represents a line of RFID data entered by the user with a timestamp:
    timestamp: float, the time the line was entered
    uid: str, the RFID data entered by the user
    """

    def __init__(self, timestamp: Seconds=None, uid: str=None):
        self.timestamp:Seconds = timestamp
        self.uid:str = uid

    def is_valid(self):
        return len(self.uid) == self.VALID_UID_LENGTH and all([char.isdigit() for char in self.uid])

    # TODO: testme
    def to_string(self):
        return f"CubeRfidLine(timestamp={self.timestamp}, uid={self.uid})"

    def to_dict(self):
        return {"timestamp": self.timestamp, "uid": self.uid}

    @classmethod
    def make_from_dict(cls, d: dict) -> Optional['CubeRfidLine']:
        """Create a CubeRfidLine object from a dictionary"""
        try:
            return CubeRfidLine(float(d["timestamp"]), d["uid"])
        except Exception as e:
            logging.error(f"Error creating CubeRfidLine from dict: {e}")
            return None

    #TODO: testme
    @staticmethod
    def make_from_string(string: str) -> Optional['CubeRfidLine']:
        """Create a CubeRfidLine object from a string"""
        try:
            # Extract the timestamp and uid from the string
            timestamp, uid = re.findall(r"\d+\.\d+|\d+", string)
            return CubeRfidLine(Seconds(timestamp), uid)
        except Exception as e:
            logging.error(f"Error creating CubeRfidLine from string: {e}")
            return None

    def __repr__(self):
        return f"CubeRfidLine(timestamp={self.timestamp}, uid={self.uid})"

    def copy(self):
        return CubeRfidLine(self.timestamp, self.uid)

    def __copy__(self):
        return self.copy()


class CubeRfidListenerBase:
    """Base class for RFID listeners. Implementations should override the run, stop, setup methods."""

    def __init__(self):
        self._is_setup = False
        self._current_chars_buffer = deque()
        self._completed_lines = deque()  # Store completed lines with their timestamps
        self._lines_lock = threading.Lock()  # Lock for thread-safe access to keycodes

    def run(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def setup(self):
        raise NotImplementedError

    def is_setup(self):
        return self._is_setup

    def get_completed_lines(self) -> List[CubeRfidLine]:
        with self._lines_lock:
            return list(self._completed_lines)

    def add_completed_line(self, rfid_line: CubeRfidLine):
        with self._lines_lock:
            self._completed_lines.append(rfid_line)

    def has_new_lines(self):
        with self._lines_lock:
            return len(self._completed_lines) > 0

    def remove_line(self, rfid_line: CubeRfidLine):
        with self._lines_lock:
            self._completed_lines.remove(rfid_line)

    def simulate_read(self, uid: str):
        self.add_completed_line(CubeRfidLine(time.time(), uid))



class CubeRfidEventListener(CubeRfidListenerBase):
    """Listens for RFID events and stores the entered lines. Only works on Linux."""
    BY_ID_PATH = "/dev/input/by-id/"
    DEV_INPUT_PATH = "/dev/input/"
    ECODES_TO_STR_DIGIT_DICT = {
        evdev.ecodes.KEY_1: '1', evdev.ecodes.KEY_2: '2', evdev.ecodes.KEY_3: '3', evdev.ecodes.KEY_4: '4',
        evdev.ecodes.KEY_5: '5',
        evdev.ecodes.KEY_6: '6', evdev.ecodes.KEY_7: '7', evdev.ecodes.KEY_8: '8', evdev.ecodes.KEY_9: '9',
        evdev.ecodes.KEY_0: '0'
    }

    def __init__(self):
        super().__init__()
        self.log = cube_logger.CubeLogger("RFID Event Listener")
        self.log.setLevel(logging.INFO)

        self._thread = threading.Thread(target=self._event_read_loop)
        self._keep_running = True

        self._device_path: str = None
        self._device = None
        self._is_setup = False

    def is_setup(self):
        return self._is_setup

    def setup(self) -> bool:
        try:
            self._device_path = self._get_input_device_path_from_device_name("RFID")
            if self._device_path is None:
                raise Exception("No RFID input device found")
            # Create an InputDevice object for the specified device
            self._device = evdev.InputDevice(self._device_path)
            self.log.info(f"RFID listener setup successful: {self._device_path}")
            self._is_setup = True
            return True
        except Exception as e:
            self.log.error(f"Could not create InputDevice object for RFID reader : {e}")
            self._is_setup = False
            return False

    def run(self):
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self.log.info("Stopping RFID Event listener...")
        self._keep_running = False
        self._thread.join(timeout=0.5)
        self.log.info("RFID Event listener stopped")

    def _event_read_loop(self):
        while self._keep_running:
            try:
                if not self.is_setup():
                    self.log.error("RFID listener not set up. Setting up...")
                    if not self.setup():
                        self.log.error("RFID listener setup failed. Retrying in 1 second...")
                        time.sleep(1)
                        continue
                # Continuously read events from the device
                for event in self._device.read_loop():
                    # Check if the event is a key event
                    if event.type == evdev.ecodes.EV_KEY:
                        # Print the key event for debug
                        # print(evdev.categorize(event))
                        # we only care about key up events
                        if self._is_event_key_up(event):
                            # if the event is the enter key, we have a complete line
                            if self._is_event_enter_key(event):
                                newline = CubeRfidLine(time.time(), "".join(self._current_chars_buffer))
                                self._current_chars_buffer.clear()
                                if newline.is_valid():
                                    self.add_completed_line(newline)
                                    self.log.info(f"Valid RFID line entered: {newline.uid}")
                                else:
                                    self.log.error(f"Invalid RFID line entered: {newline.uid}")
                            # if the event is a digit key, we add it to the buffer
                            elif self._is_event_digit_key(event):
                                digit_str = self._event_to_digit_str(event)
                                self._current_chars_buffer.append(digit_str)
            except Exception as e:
                self.log.error(f"Error reading RFID events: {e}")
                self._is_setup = False

    @staticmethod
    def _get_input_device_path_from_device_name(name):
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

    @staticmethod
    def _is_event_enter_key(event: evdev.InputEvent):
        # return event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.KEY_ENTER and event.value == evdev.events.KeyEvent.key_up
        return event.type == evdev.ecodes.EV_KEY and event.code == evdev.ecodes.KEY_ENTER

    @staticmethod
    def _is_event_digit_key(event: evdev.InputEvent):
        return event.type == evdev.ecodes.EV_KEY and event.code in CubeRfidEventListener.ECODES_TO_STR_DIGIT_DICT

    @staticmethod
    def _is_event_key_up(event):
        return event.type == evdev.ecodes.EV_KEY and event.value == evdev.events.KeyEvent.key_up

    @staticmethod
    def _event_to_digit_str(event: evdev.InputEvent):
        if not event.code in CubeRfidEventListener.ECODES_TO_STR_DIGIT_DICT:
            return None
        return CubeRfidEventListener.ECODES_TO_STR_DIGIT_DICT[event.code]


class CubeRfidKeyboardListener(CubeRfidListenerBase):
    """Reacts to RFID characters entered as if by a keyboard and stores the entered lines"""

    AZERTY_DICT = {
        '&': '1', 'é': '2', '"': '3', "'": '4', '(': '5',
        '-': '6', 'è': '7', '_': '8', 'ç': '9', 'à': '0'}

    def __init__(self):
        super().__init__()
        self.log = cube_logger.CubeLogger(name="RFID Keyboard Listener")
        self.current_chars_buffer = deque()  # Use deque for efficient pop/append operations
        self._completed_lines = deque()  # Store completed lines with their timestamps
        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self.setup()

    def setup(self):
        self._is_setup = True
        return True

    def run(self):
        self._keyboard_listener.start()

    def stop(self):
        self.log.info("Stopping RFID listener...")
        self._keyboard_listener.stop()
        self.log.info("RFID listener stopped")

    def _on_press(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        try:
            keycode = key.vk  # Get the virtual key code
        except AttributeError:
            keycode = key.value.vk if key.value else None  # Handle special keys
        if keycode is None:
            return
        # noinspection PyBroadException
        try:
            # Signal that a new line has been entered
            if key == keyboard.Key.enter:
                newline = CubeRfidLine(time.time(), "".join(self.current_chars_buffer))
                self.current_chars_buffer.clear()
                if newline.is_valid():
                    self.add_completed_line(newline)
                    self.log.info(f"Valid RFID line entered: {newline.uid}")
                else:
                    self.log.error(f"Invalid RFID line entered: {newline.uid}")
            # if it's not a newline
            else:
                # convert azerty to qwerty is need be
                char = key.char if key.char not in self.AZERTY_DICT else self.AZERTY_DICT[key.char]
                if char.isdigit():
                    self.current_chars_buffer.append(char)
        except:
            pass


def test_rfid_keyboard_listener():
    rfid = CubeRfidKeyboardListener()
    rfid.log.info("RFID listener test. Press Ctrl+C to stop.")
    rfid.setup()
    rfid.run()
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


def test_rfid_event_listener():
    rfid = CubeRfidEventListener()
    rfid.log.info("RFID Event listener test. Press Ctrl+C to stop.")
    if rfid.is_setup():
        print("RFID listener setup successful:", rfid._device_path)
    rfid.run()
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


def test_rfid_read_simulation():
    print("Testing RFID read simulation for CubeRfidKeyboardListener")
    rfid = CubeRfidKeyboardListener()
    rfid.simulate_read("1234567890")
    print(rfid.get_completed_lines())

    print("Testing RFID read simulation for CubeRfidEventListener")
    rfid = CubeRfidEventListener()
    rfid.simulate_read("1234567891")
    print(rfid.get_completed_lines())


if __name__ == "__main__":

    print("Testing RFID Line Simulation")
    test_rfid_read_simulation()
    exit(0)

    print("Testing RFID Keyboard Listener")
    test_rfid_keyboard_listener()
    print("Testing RFID Event Listener")
    test_rfid_event_listener()
