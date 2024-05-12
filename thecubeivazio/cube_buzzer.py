"""Handles everything related to the buzzer.
Interfaces a piezo buzzer to the RaspberryPi or plays sound files if not on the RaspberryPi."""
import logging
import threading
import time
from typing import Tuple

from thecubeivazio import cube_logger

try:
    # noinspection PyUnresolvedReferences
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    GPIO = None

class CubeBuzzer:
    BUZZER_PIN = 17
    def __init__(self):
        self.log = cube_logger.make_logger("Buzzer")
        self.log.setLevel(logging.INFO)
        self._thread = None
        self._lock = threading.Lock()
        # check if on RaspberryPi
        if GPIO is not None:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.BUZZER_PIN, GPIO.OUT)
            self._is_raspberry_pi = True
        else:
            self.log.info("Not on a Raspberry Pi, using sound files to simulate buzzer")
            self._is_raspberry_pi = False

    def play_file_or_tune(self, soundfile:str, tune:Tuple[Tuple[int, float], ...]):
        """Play a sound file or a tune on the buzzer."""
        self._thread = threading.Thread(target=self._play_file_or_tune, args=(soundfile, tune))
        self._thread.start()
        with self._lock:
            self._thread.join()

    def _play_file_or_tune(self, soundfile:str, tune:Tuple[Tuple[int, float], ...]):
        if self._is_raspberry_pi:
            for pitch, duration in tune:
                self.buzz(pitch, duration)
        else:
            self.play_sound_file(soundfile)

    def play_sound_file(self, soundfile:str):
        self.log.debug(f"Playing sound file: {soundfile}")
        if self._is_raspberry_pi:
            return
        import pygame.mixer as mixer
        import pygame.time as pgtime
        mixer.init()
        #soundfile = self.get_sound_file_path(soundfile)
        mixer.music.load(soundfile)
        mixer.music.play()
        # Wait for the music to play
        while mixer.music.get_busy():
            pgtime.Clock().tick(10)

    def buzz(self, pitch:int, duration:float):
        """Play a tone on the buzzer."""
        self.log.info(f"Playing tone: {pitch} Hz for {duration} seconds")
        if not self._is_raspberry_pi:
            return
        if pitch == 0:
            time.sleep(duration)
            return
        period = 1.0 / pitch  # Period of the wave
        delay = period / 2  # Delay between toggles
        cycles = int(duration * pitch)  # Number of cycles for the tone

        for i in range(cycles):
            GPIO.output(self.BUZZER_PIN, True)
            time.sleep(delay)
            GPIO.output(self.BUZZER_PIN, False)
            time.sleep(delay)

    def play_rfid_ok_sound(self):
        self.play_file_or_tune("sounds/rfid_ok.mp3", ((523, 0.5), (800, 0.5)))

    def play_rfid_error_sound(self):
        self.play_file_or_tune("sounds/rfid_error.mp3", ((523, 0.5), (400, 1.0)))

    def play_victory_sound(self):
        self.play_file_or_tune("sounds/victory.mp3", ((400, 0.5), (500, 0.5), (600, 0.5), (700, 1.0)))

    def play_game_over_sound(self):
        self.play_file_or_tune("sounds/game_over.mp3", ((400, 0.5), (300, 0.5), (200, 0.5), (100, 1.0)))


if __name__ == "__main__":
    buzzer = CubeBuzzer()
    buzzer.log.setLevel(logging.DEBUG)
    buzzer.log.info("Playing RFID OK sound")
    buzzer.play_rfid_ok_sound()
    buzzer.log.info("Playing RFID error sound")
    buzzer.play_rfid_error_sound()
    buzzer.log.info("Playing victory sound")
    buzzer.play_victory_sound()
    buzzer.log.info("Playing game over sound")
    buzzer.play_game_over_sound()
    buzzer.log.info("Done")