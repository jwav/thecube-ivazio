"""
This module handles everything button-related for the CubeBox
It is meant to interact with the Raspberry Pi's GPIO pins,
but when testing on a regular computer, it will simply tell if the 'v' key is pressed
"""
import threading

from cube_utils import SimpleTimer

import time
from typing import Union
from pynput import keyboard


# TODO: read state of GPIO, add methods to interface all that
# TODO: use an interrupt?
class CubeBoxButton:
    DEBOUNCE_TIME = 1
    PERIOD = 0.01
    def __init__(self):
        # test if we're on a Raspberry Pi or not
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)
            self.GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except ModuleNotFoundError:
            self.GPIO = None
            self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.listener.start()
            print("Not on a Raspberry Pi, using 'v' key to simulate button press")
        self._pressed = False
        self._timer_started = False
        self._press_timer = SimpleTimer(self.DEBOUNCE_TIME)
        self._pressed_long_enough = False
        self._thread = None
        self._keep_running = True

    def run(self):
        self._thread = threading.Thread(target=self._loop)
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self._keep_running = False
        self._thread.join()

    def reset(self):
        self._pressed = False
        self._timer_started = False
        self._press_timer.reset()
        self._pressed_long_enough = False

    def has_been_pressed_long_enough(self) -> bool:
        """Returns True if the button has been pressed long enough (debounce time)
        DO NOT FORGET to reset the button after reading this value or it will always return True
        """
        return self._pressed_long_enough

    def _loop(self):
        while self._keep_running:
            if self._is_pressed_now():
                if not self._timer_started:
                    self._press_timer.reset()
                    self._timer_started = True
                    print("starting button timer")
                if self._timer_started and self._press_timer.is_timeout():
                    self._pressed_long_enough = True
            else: # if not pressed
                self.reset()
            time.sleep(self.PERIOD)

    def _is_pressed_now(self) -> bool:
        if self.GPIO:
            self._pressed = self.GPIO.input(18) == 0
        else:
            # on_press handles the update of _pressed when not on a Raspberry Pi (keyboard input)
            pass
        return self._pressed

    def on_press(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        if hasattr(key, 'char') and key.char == 'v':  # Check if 'v' key is pressed
            # print("v key pressed")
            self._pressed = True


    def on_release(self, key: Union[keyboard.KeyCode, keyboard.Key]):
        if hasattr(key, 'char') and key.char == 'v':
            # print("v key released")
            self._pressed = False




# TODO: perform test read
if __name__ == "__main__":
    btn = CubeBoxButton()
    btn.run()
    while True:
        print("Button ON" if btn._is_pressed_now() else "Button OFF")
        if btn.has_been_pressed_long_enough():
            print("Button pressed long enough")
            btn.reset()
            btn.stop()
            break
        time.sleep(0.5)
