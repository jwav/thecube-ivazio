"""
This module handles everything button-related for the CubeBox
It is meant to interact with the Raspberry Pi's GPIO pins,
but when testing on a regular computer, it will simply tell if the 'v' key is pressed
"""
import logging
import threading
import time

from thecubeivazio import cube_logger, cube_utils
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_utils import CubeSimpleTimer, XvfbManager

# pynput requires an X server to run, so we start a virtual one with XVFB if it's not already running
if not XvfbManager.has_x_server():
    print("No X server found, starting XVFB...")
    XvfbManager.start_xvfb()
else:
    print("X server found, not starting XVFB")
from pynput import keyboard


class CubeButton:
    DEBOUNCE_TIME: Seconds = 0.5
    PRESS_CHECK_PERIOD: Seconds = 0.1
    BUTTON_PIN: int = 17
    KEYBOARD_SIMULATED_KEY: str = 'v'

    def __init__(self):
        self.log = cube_logger.CubeLogger(name="Button")
        self.log.setLevel(logging.INFO)
        # test if we're on a Raspberry Pi or not
        try:
            if not cube_utils.is_raspberry_pi():
                raise ModuleNotFoundError
            # noinspection PyUnresolvedReferences
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)
            self.GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._is_raspberry_pi = True
        except ModuleNotFoundError:
            self.GPIO = None
            self.keyboard_listener = keyboard.Listener(on_press=self._on_keyboard_press,
                                                       on_release=self._on_keyboard_release)
            self.keyboard_listener.start()
            self.log.info(f"Not on a Raspberry Pi, using '{self.KEYBOARD_SIMULATED_KEY}' key to simulate button press")
            self._is_raspberry_pi = False
        self._pressed = False
        self._timer_started = False
        self._press_timer = CubeSimpleTimer(self.DEBOUNCE_TIME)
        self._pressed_long_enough = False
        self._thread = None
        self._keep_running = True
        self._simulating_long_press = False

        # the button will toggle between high and low. What we're interested in is the change of state.

        self._pressed_state = None


    def set_current_state_as_unpressed(self):
        """This method should be called at startup and after a button press has been handled
        to indicate : 'the state the button is in is considered the unpressed state.
        When the button changes state, it will be considered pressed'
        """
        state = self.read_gpio_state()
        if state is not None:
            self._pressed_state = not state

    def read_gpio_state(self) -> Optional[bool]:
        # if we're on a rpi, read the GPIO pin
        if self.GPIO:
            return self.GPIO.input(self.BUTTON_PIN)
        # if we're not on a rpi, return None to indicate that we can't read the state
        else:
            return None

    def run(self):
        self.set_current_state_as_unpressed()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self.log.info("Stopping button internal thread...")
        # noinspection PyBroadException
        if not self._is_raspberry_pi:
            self.keyboard_listener.stop()
        self._keep_running = False
        self._thread.join(timeout=0.1)
        self.log.info("Button internal thread stopped")

    def reset(self):
        self.set_current_state_as_unpressed()
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
        """NOTE: with the wireless button, this method should NEVER be used.
        Sleeps while self.is_pressed_now() is True"""
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
                if self._timer_started and self._press_timer.is_timeout() and not self._pressed_long_enough:
                    self.log.debug("Button pressed long enough")
                    self._pressed_long_enough = True
            elif self._simulating_long_press:
                self._pressed_long_enough = True
            else:  # if not pressed
                self.reset()
            time.sleep(self.PRESS_CHECK_PERIOD)

    def is_pressed_now(self) -> bool:
        state = self.read_gpio_state()
        if state is not None:
            self._pressed = (state == self._pressed_state)
        else:
            # if we're not on a Raspberry Pi, the keyboard listener will update the state
            pass
        return self._pressed

    def _on_keyboard_press(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        if hasattr(key, 'char') and key.char == self.KEYBOARD_SIMULATED_KEY:
            self._pressed = True

    def _on_keyboard_release(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        if hasattr(key, 'char') and key.char == self.KEYBOARD_SIMULATED_KEY:
            self._pressed = False


def test_button_press():
    btn = CubeButton()
    btn.log.setLevel(logging.DEBUG)
    btn.run()
    try:
        while True:
            print("0V" if btn.read_gpio_state() else "3.3V", end=" -> ")
            print("Button ON" if btn.is_pressed_now() else "Button OFF")
            if btn.has_been_pressed_long_enough():
                print("Button pressed long enough")
                btn.reset()
            time.sleep(0.5)
    except KeyboardInterrupt:
        btn.stop()
        print("Button test stopped")
        exit(0)

if __name__ == "__main__":
    test_button_press()
