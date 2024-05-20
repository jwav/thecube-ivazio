"""
This module handles everything button-related for the CubeBox
It is meant to interact with the Raspberry Pi's GPIO pins,
but when testing on a regular computer, it will simply tell if the 'v' key is pressed
"""
from thecubeivazio import cube_logger
from thecubeivazio.cube_utils import SimpleTimer, XvfbManager

import logging
import threading
import time
from typing import Union

# pynput requires an X server to run, so we start a virtual one with XVFB if it's not already running
if not XvfbManager.has_x_server():
    XvfbManager.start_xvfb()
from pynput import keyboard


# TODO: read state of GPIO, add methods to interface all that
# TODO: use an interrupt?
class CubeButton:
    DEBOUNCE_TIME = 1
    PRESS_CHECK_PERIOD = 0.01
    BUTTON_PIN = 18

    def __init__(self):
        self.log = cube_logger.cube_logger.CubeLogger(name="Button")
        self.log.setLevel(logging.INFO)
        # test if we're on a Raspberry Pi or not
        try:
            # noinspection PyUnresolvedReferences
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)
            self.GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._is_raspberry_pi = True
        except ModuleNotFoundError:
            self.GPIO = None
            self.keyboard_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.keyboard_listener.start()
            self.log.info("Not on a Raspberry Pi, using 'v' key to simulate button press")
            self._is_raspberry_pi = False
        self._pressed = False
        self._timer_started = False
        self._press_timer = SimpleTimer(self.DEBOUNCE_TIME)
        self._pressed_long_enough = False
        self._thread = None
        self._keep_running = True
        self._simulating_long_press = False

    def run(self):
        self._thread = threading.Thread(target=self._loop)
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self.log.info("Stopping button thread...")
        # noinspection PyBroadException
        if not self._is_raspberry_pi:
            self.keyboard_listener.stop()
        self._keep_running = False
        self._thread.join(timeout=1)
        self.log.info("Button thread stopped")

    def reset(self):
        # print("Resetting button")
        self._pressed = False
        self._timer_started = False
        self._press_timer.reset()
        self._pressed_long_enough = False
        self._simulating_long_press = False

    def has_been_pressed_long_enough(self) -> bool:
        """Returns True if the button has been pressed long enough (debounce time)
        DO NOT FORGET to reset the button after reading this value or it will always return True
        """
        return self._pressed_long_enough

    def simulate_long_press(self):
        """Simulate a long press of the button by altering the state of this object"""
        self._simulating_long_press = True

    def wait_until_released(self):
        """Sleeps while self.is_pressed_now() is True"""
        while self.is_pressed_now():
            time.sleep(self.PRESS_CHECK_PERIOD)

    def _loop(self):
        while self._keep_running:
            if self.is_pressed_now():
                # print("Button pressed NOW")
                if not self._timer_started:
                    self._press_timer.reset()
                    self.log.debug("resetting button timer")
                    self._timer_started = True
                    # print("starting button timer")
                if self._timer_started and self._press_timer.is_timeout():
                    self.log.debug("Button pressed long enough")
                    self._pressed_long_enough = True
            elif self._simulating_long_press:
                self._pressed_long_enough = True
            else:  # if not pressed
                self.reset()
            time.sleep(self.PRESS_CHECK_PERIOD)

    def is_pressed_now(self) -> bool:
        if self.GPIO:
            self._pressed = self.GPIO.input(18) == 0
        else:
            # on_press handles the update of _pressed when not on a Raspberry Pi (keyboard input)
            pass
        # print("Button pressed" if self._pressed else "Button not pressed")
        return self._pressed

    def _on_press(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        if hasattr(key, 'char') and key.char == 'v':  # Check if 'v' key is pressed
            # print("v key pressed")
            self._pressed = True

    def _on_release(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        if hasattr(key, 'char') and key.char == 'v':
            # print("v key released")
            self._pressed = False


if __name__ == "__main__":
    btn = CubeButton()
    btn.log.setLevel(logging.DEBUG)
    btn.run()
    try:
        while True:
            print("Button ON" if btn.is_pressed_now() else "Button OFF")
            if btn.has_been_pressed_long_enough():
                print("Button pressed long enough")
                print("Waiting for button to be released...")
                btn.wait_until_released()
                print("Button released")
                btn.reset()
            time.sleep(0.5)
    except KeyboardInterrupt:
        btn.stop()
        print("Button test stopped")
        exit(0)
