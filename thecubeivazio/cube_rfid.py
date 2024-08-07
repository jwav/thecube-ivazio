#!/usr/bin/python3

"""
This module handles everything RFID-related for the CubeBox
"""
import json
import logging
import subprocess
import threading
import time
from collections import deque
from typing import List

import serial

from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_config import CubeConfig
from thecubeivazio.cube_utils import XvfbManager, is_windows, is_raspberry_pi

if is_raspberry_pi():
    import evdev

    # pynput requires an X server to run, so we start a virtual one with XVFB if it's not already running
    if not XvfbManager.is_x_server_already_running():
        XvfbManager.start_xvfb()

from pynput import keyboard


class CubeRfidLine:
    """Represents a line of RFID data entered by the user with a timestamp:
    timestamp: float, the time the line was entered
    uid: str, the RFID data entered by the user
    """
    # valid length for the "Windows" RFID reader
    # VALID_UID_LENGTH = 10
    # valid length for the "Prison Island" RFID reader (sometimes it's 9)
    VALID_UID_LENGTH = 8
    MAX_UID_LENGTH = 20
    MIN_UID_LENGTH = 4
    # if set to True, the length of the RFID UID will be checked to determine if it's valid
    # if set to False, the UID will be considered valid if it's all hex characters
    # TODO: ideally, CHECK_FOR_LENGTH should be set to True, but we need to assert that all RFIDs read are the same length
    CHECK_FOR_LENGTH = False
    # if set to True, we'll check if the UID is within the range of MIN_UID_LENGTH and MAX_UID_LENGTH
    CHECK_FOR_LENGTH_RANGE = True

    def __init__(self, timestamp: Seconds = None, uid: str = None):
        self.timestamp: Seconds = timestamp
        self.uid: str = uid

    @classmethod
    def is_char_valid_uid_char(cls, char: str) -> bool:
        return char in "0123456789abcdefABCDEF"

    @classmethod
    def is_valid_uid(cls, uid: str) -> bool:
        if not all([CubeRfidLine.is_char_valid_uid_char(char) for char in uid]):
            return False
        if CubeRfidLine.CHECK_FOR_LENGTH:
            return len(uid) == CubeRfidLine.VALID_UID_LENGTH
        if CubeRfidLine.CHECK_FOR_LENGTH_RANGE:
            return CubeRfidLine.MIN_UID_LENGTH <= len(uid) <= CubeRfidLine.MAX_UID_LENGTH
        return True

    @classmethod
    def are_uids_the_same(cls, uid1: str, uid2: str) -> bool:
        if not CubeRfidLine.is_valid_uid(uid1) or not CubeRfidLine.is_valid_uid(uid2):
            return False
        if len(uid1) < len(uid2):
            shorter = uid1.lower()
            longer = uid2.lower()
        else:
            shorter = uid2.lower()
            longer = uid1.lower()
        return longer.startswith(shorter)

    def is_resetter(self) -> bool:
        return CubeRfidLine.is_uid_in_resetter_list(self.uid)

    def is_valid(self):
        try:
            return self.is_valid_uid(self.uid) and self.timestamp is not None
        except Exception as e:
            logging.error(f"Error checking if CubeRfidLine is valid: {e}")
            return False

    # TODO: testme
    def to_string(self):
        return f"CubeRfidLine(timestamp={self.timestamp}, uid={self.uid})"

    @cubetry
    def to_dict(self):
        return {"timestamp": self.timestamp, "uid": self.uid}

    @cubetry
    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    @cubetry
    def make_from_json(cls, json_str: str) -> Optional['CubeRfidLine']:
        return cls.make_from_dict(json.loads(json_str))

    @classmethod
    def make_from_dict(cls, d: dict) -> Optional['CubeRfidLine']:
        """Create a CubeRfidLine object from a dictionary"""
        try:
            return CubeRfidLine(float(d["timestamp"]), d["uid"])
        except Exception as e:
            logging.error(f"Error creating CubeRfidLine from dict: {e}")
            return None

    @cubetry
    def __eq__(self, other: 'CubeRfidLine'):
        return self.timestamp == other.timestamp and self.uid == other.uid

    @cubetry
    def __repr__(self):
        return f"CubeRfidLine(timestamp={self.timestamp}, uid={self.uid})"

    @cubetry
    def copy(self):
        return CubeRfidLine(self.timestamp, self.uid)

    def __copy__(self):
        return self.copy()

    @classmethod
    def generate_random_rfid_line(cls) -> 'CubeRfidLine':
        import random
        import string
        return CubeRfidLine(time.time(), "".join(random.choices(string.digits, k=cls.VALID_UID_LENGTH)))

    @classmethod
    def is_uid_in_resetter_list(cls, uid: str) -> bool:
        """Check if the given RFID UID is in the resetter list"""
        try:
            resetters = cls.get_resetter_uids_list()
            for resetter_uid in resetters:
                if cls.are_uids_the_same(uid, resetter_uid):
                    return True
            return False
        except Exception as e:
            logging.error(f"Error checking RFID UID in resetter list: {e}")
            return False

    @classmethod
    def get_resetter_uids_list(cls) -> List[str]:
        """Get the list of resetter UIDs from the config"""
        try:
            config = CubeConfig()
            return config.get_resetter_rfids()
        except Exception as e:
            logging.error(f"Error getting resetter UIDs list: {e}")
            return []



class CubeRfidListenerBase:
    """Base class for RFID listeners. Implementations should override the run, stop, setup methods."""

    def __init__(self):
        self._is_setup = False
        self._current_chars_buffer = deque()
        self._completed_lines = deque()  # Store completed lines with their timestamps
        self._lines_lock = threading.Lock()  # Lock for thread-safe access to keycodes
        # in simulations, we will need to disable the rfid listeners for a cleaner test
        # and avoiding constant log errors
        self._is_enabled = True

    def disable(self):
        self._is_enabled = False

    def enable(self):
        self._is_enabled = True

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

    def add_completed_line(self, rfid_line: CubeRfidLine) -> bool:
        if not rfid_line.is_valid():
            CubeLogger.static_error(f"Invalid RFID line entered: {rfid_line}")
            return False
        with self._lines_lock:
            self._completed_lines.append(rfid_line)
            return True

    def has_new_lines(self):
        with self._lines_lock:
            return len(self._completed_lines) > 0

    def remove_line(self, rfid_line: CubeRfidLine):
        with self._lines_lock:
            self._completed_lines.remove(rfid_line)

    def simulate_read(self, uid: str):
        """Simulate the reading of an RFID UID"""
        CubeLogger.static_info(f"Simulating RFID read: {uid}")
        if self.add_completed_line(CubeRfidLine(time.time(), uid)):
            CubeLogger.static_info(f"Simulated RFID read successful: {uid}")
        else:
            CubeLogger.static_error(f"Simulated RFID read failed: {uid}")


if is_raspberry_pi():
    class CubeRfidEventListener(CubeRfidListenerBase):
        """Listens for RFID events and stores the entered lines. Only works on Linux."""
        BY_ID_PATH = "/dev/input/by-id/"
        DEV_INPUT_PATH = "/dev/input/"
        ECODES_TO_STR_DIGIT_DICT = {
            evdev.ecodes.KEY_1: '1', evdev.ecodes.KEY_2: '2', evdev.ecodes.KEY_3: '3', evdev.ecodes.KEY_4: '4',
            evdev.ecodes.KEY_5: '5', evdev.ecodes.KEY_6: '6', evdev.ecodes.KEY_7: '7', evdev.ecodes.KEY_8: '8',
            evdev.ecodes.KEY_9: '9', evdev.ecodes.KEY_0: '0',
            evdev.ecodes.KEY_A: 'A', evdev.ecodes.KEY_B: 'B', evdev.ecodes.KEY_C: 'C', evdev.ecodes.KEY_D: 'D',
            evdev.ecodes.KEY_E: 'E', evdev.ecodes.KEY_F: 'F',
        }

        def __init__(self, show_debug=False):
            super().__init__()
            self.log = CubeLogger("RFID Event Listener")
            self.log.setLevel(logging.INFO)
            if show_debug:
                self.log.setLevel(logging.DEBUG)

            self._thread = threading.Thread(target=self._event_read_loop, daemon=True)
            self._keep_running = True

            self._device_path: Optional[str] = None
            self._device = None
            self._is_setup = False
            self.setup()

        def setup(self) -> bool:
            try:
                if not self._is_enabled:
                    return True
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
            if self._keep_running:
                self.stop()
            self._keep_running = True
            self._thread = threading.Thread(target=self._event_read_loop, daemon=True)
            self.log.info("Starting RFID Event listener...")
            self._thread.start()
            self.log.info("Started RFID Event listener")


        def stop(self):
            try:
                self.log.info("Stopping RFID Event listener...")
                self._keep_running = False
                self._thread.join(timeout=0.5)
                self.log.info("RFID Event listener stopped")
            except Exception as e:
                self.log.error(f"Error stopping RFID Event listener: {e}")

        def _event_read_loop(self):
            while self._keep_running:
                try:
                    if not self._is_enabled:
                        time.sleep(1)
                        continue
                    if not self.is_setup():
                        self.log.error(f"{self.__class__.__name__} not set up. Setting up...")
                        if not self.setup():
                            self.log.error(f"{self.__class__.__name__} setup failed. Retrying in 1 second...")
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

elif not is_raspberry_pi():
    # mock class of CubeRfidEventListener for non-raspberry pi systems
    class CubeRfidEventListener(CubeRfidListenerBase):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self.log = CubeLogger("Mock RFID Event Listener")
            self._is_setup = True

        def setup(self):
            return True

        def run(self):
            pass

        def stop(self):
            pass

class CubeRfidKeyboardListener(CubeRfidListenerBase):
    """Reacts to RFID characters entered as if by a keyboard and stores the entered lines"""

    AZERTY_DICT = {
        '&': '1', 'é': '2', '"': '3', "'": '4', '(': '5',
        '-': '6', 'è': '7', '_': '8', 'ç': '9', 'à': '0'}

    def __init__(self):
        super().__init__()
        self.log = CubeLogger(name="RFID Keyboard Listener")
        self.current_chars_buffer = deque()  # Use deque for efficient pop/append operations
        self._completed_lines = deque()  # Store completed lines with their timestamps
        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self.setup()

    def setup(self):
        # self._is_setup = self.enable_usb_rfid()
        self._is_setup = True
        if not self._is_setup:
            self.log.error("RFID Keyboard listener setup failed")
            return False
        self.log.success("RFID Keyboard listener setup successful")
        return True

    def run(self):
        self._keyboard_listener.start()

    def stop(self):
        self.log.info("Stopping RFID listener...")
        self._keyboard_listener.stop()
        self.log.info("RFID listener stopped")

    @cubetry
    def enable_usb_rfid(self) -> bool:
        self.log.info("Enabling RFID reader...")
        usb_path = None

        # Find the correct USB device path, display the results of lsusb
        with os.popen('lsusb') as f:
            for line in f:
                # print(line)
                if 'Sycreader RFID Technology' in line:
                    self.log.debug(f"Found RFID reader in '{line}'")
                    parts = line.split()
                    if len(parts) >= 4:
                        bus = parts[1]
                        device = parts[3][:-1]
                        self.log.info(f"Bus: {bus}, Device: {device}")
                        usb_path = f'/sys/bus/usb/devices/{bus}-{device}/authorized'
                        break
                    else:
                        self.log.error("Unexpected format in lsusb output")
        if not usb_path:
            self.log.error("USB RFID reader not found")
            return False

        if usb_path and os.path.exists(usb_path):
            try:
                with open(usb_path, 'r') as f:
                    status = f.read().strip()
                if status == '1':
                    self.log.success("RFID reader is already enabled.")
                    return True
                else:
                    with open(usb_path, 'w') as f:
                        f.write('1')
                    self.log.info(f"RFID reader enabled at {usb_path}")
            except Exception as e:
                self.log.error(f"Failed to enable RFID reader: {e}")
                return False
        else:
            self.log.error("RFID reader not found")
            return False
        self.log.success("RFID reader enabled successfully")
        return True

    def _on_press(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        # to reduce CPU hogging.
        #time.sleep(0.01)
        # print(f"Key pressed: {key}")
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
                # empty line? ignore
                if not self.current_chars_buffer:
                    return
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
                if CubeRfidLine.is_char_valid_uid_char(char):
                    self.current_chars_buffer.append(char)
        except Exception as e:
            # print(f"Error in RFID listener: {e}")
            pass


class CubeRfidSerialListener(CubeRfidListenerBase):
    """Listens for RFID data from a serial port."""

    def __init__(self):
        super().__init__()
        self.port = None
        self.serial_conn = None
        self.log = CubeLogger(name="RFID Serial Listener")
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._keep_running = True
        self.setup()

    def setup(self) -> bool:
        try:
            self.log.info("Setting up CubeRfidListenerSerial...")
            ports = subprocess.check_output("ls /dev/ttyUSB*", shell=True).decode().split()
            for port in ports:
                output = subprocess.check_output(f"udevadm info --name={port} --query=all", shell=True).decode()
                if "Future Technology Devices International" in output:
                    self.port = port
                    break
            if not self.port:
                raise Exception("No suitable serial port found.")
            self.serial_conn = serial.Serial(self.port, 9600)
            self._is_setup = True
            self.log.success(f"Serial RFID listener setup successful: {self.port}")
            return True
        except Exception as e:
            self.log.error(f"Error setting up CubeRfidListenerSerial: {e}")
            self._is_setup = False
            return False

    def run(self):
        if not self._is_setup:
            if not self.setup():
                return
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self.log.info("Stopping Serial RFID Listener...")
        self._keep_running = False
        self._thread.join(timeout=0.5)
        self.log.info("Serial RFID Listener stopped.")
        if self.serial_conn:
            self.serial_conn.close()
        self._is_setup = False

    def _read_loop(self):
        while self._keep_running:
            if not self._is_setup:
                if not self.setup():
                    time.sleep(1)
                    continue
            try:
                if self.serial_conn.in_waiting > 0:
                    char = self.serial_conn.read().decode('utf-8').rstrip()
                    # if it's a valid char, add it and continue
                    if CubeRfidLine.is_char_valid_uid_char(char):
                        self._current_chars_buffer.append(char)
                        continue
                    # ok, this is a non-valid (non-hex) char.
                    # non-valid chars are treated as separators.
                    # if the buffer is empty, do nothing.
                    if not self._current_chars_buffer:
                        self._current_chars_buffer.clear()
                        continue
                    # if the buffer is valid, add it to the lines
                    if not CubeRfidLine.is_valid_uid(''.join(self._current_chars_buffer)):
                        self.log.error(f"Invalid RFID UID: {''.join(self._current_chars_buffer)}")
                        self._current_chars_buffer.clear()
                        continue
                    newline = CubeRfidLine(time.time(), ''.join(self._current_chars_buffer))
                    if not newline.is_valid():
                        self.log.error("The UID is valid, but the RfidLine is invalid!?")
                        self._current_chars_buffer.clear()
                        continue
                    # ok it's a valid entry. add it to the lines and clear the buffer
                    self.add_completed_line(newline)
                    self._current_chars_buffer.clear()
                    self.log.info(f"Valid RFID line entered: {newline.uid}")

            except Exception as e:
                self.log.error(f"Error in CubeRfidListenerSerial read loop: {e}")
                self._is_setup = False


def test_rfid_keyboard_listener():
    rfid = CubeRfidKeyboardListener()
    rfid.log.info("RFID listener test. Press Ctrl+C to stop.")
    rfid.setup()
    rfid.run()
    try:
        while True:
            time.sleep(0.1)
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
    rfid.simulate_read(CubeRfidLine.generate_random_rfid_line().uid)
    print(rfid.get_completed_lines())

    print("Testing RFID read simulation for CubeRfidEventListener")
    rfid = CubeRfidEventListener()
    rfid.simulate_read(CubeRfidLine.generate_random_rfid_line().uid)
    print(rfid.get_completed_lines())


def test_serial_rfid():
    rfid = CubeRfidSerialListener()
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
    exit(0)


def test_compare_rfid_listeners():
    rfid_serial = CubeRfidSerialListener()
    rfid_keyboard = CubeRfidKeyboardListener()
    serial_lines = []
    keyboard_lines = []
    rfid_serial.run()
    rfid_keyboard.run()
    try:
        while True:
            if lines := rfid_serial.get_completed_lines():
                for line in lines:
                    serial_lines.append(line)
                rfid_serial._completed_lines.clear()
            if lines := rfid_keyboard.get_completed_lines():
                for line in lines:
                    keyboard_lines.append(line)
                rfid_keyboard._completed_lines.clear()
    except KeyboardInterrupt:
        print("Stopping listeners...")
    finally:
        rfid_serial.stop()
        rfid_keyboard.stop()
        # compare the lines: show which lines match which lines for each list
        for serial_line in serial_lines:
            for keyboard_line in keyboard_lines:
                if CubeRfidLine.are_uids_the_same(serial_line.uid, keyboard_line.uid):
                    print(f"Serial: {serial_line.uid} same as Keyboard: {keyboard_line.uid}")
        exit(0)


def test_enable_usb_rfid():
    rfid = CubeRfidKeyboardListener()
    # rfid.enable_usb_rfid()
    exit(0)


def test_for_windows():
    test_rfid_keyboard_listener()



def test_for_raspberry_pi():
    # test_enable_usb_rfid()
    test_serial_rfid()
    exit(0)
    test_compare_rfid_listeners()

    print("Testing RFID Line Simulation")
    test_rfid_read_simulation()
    exit(0)

    print("Testing RFID Keyboard Listener")
    test_rfid_keyboard_listener()
    print("Testing RFID Event Listener")
    test_rfid_event_listener()


def test_uid_equality():
    uid1 = "40001F411E"
    uid2 = "40001ecce2"
    uid3 = "1111111111"
    uid4 = "1234579"
    uid5 = "123456"
    uid6 = "12"
    uid7 = "123456789"
    for uid in [uid2, uid3, uid4, uid5, uid6, uid7]:
        print(f"{uid} is valid: {CubeRfidLine.is_valid_uid(uid)}")
        print(f"{uid} is in resetter list: {CubeRfidLine.is_uid_in_resetter_list(uid)}")
        print(f"{uid} == {uid1} : {CubeRfidLine.are_uids_the_same(uid, uid1)}")
    exit(0)


if __name__ == "__main__":
    test_uid_equality()
    if is_windows():
        test_for_windows()
    elif is_raspberry_pi():
        test_for_raspberry_pi()
