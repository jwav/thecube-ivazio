"""Handles everything related to the buzzer.
Interfaces a piezo buzzer to the RaspberryPi or plays sound files if not on the RaspberryPi."""
import logging
import random
import threading
import time
from typing import Tuple

from thecubeivazio import cube_logger
from thecubeivazio.cube_common_defines import *
import os

import pygame.mixer as mixer
import pygame.time as pgtime


class CubeSoundPlayer:
    DEFAULT_VOLUME_PERCENT = 100
    SUPPORTED_EXTENSIONS = ['.wav', '.mp3', '.ogg', '.flac', '.mod', '.s3m', '.it', '.xm']

    def __init__(self):
        self.log = cube_logger.CubeLogger("Buzzer")
        self.log.setLevel(logging.INFO)
        self._thread = None
        self.log.info(f"Sounds directory: '{SOUNDS_DIR}'")

    def set_volume_percent(self, volume_percent: int):
        """Set the volume of the buzzer."""
        self.log.info(f"Setting volume to {volume_percent}%")
        mixer.music.set_volume(volume_percent / 100)

    def play_sound_file(self, soundfile: str):
        """Play a sound file or a tune on the buzzer."""
        self._thread = threading.Thread(target=self._play_sound_file, args=(soundfile,))
        self._thread.start()
        self._thread.join(timeout=STATUS_REPLY_TIMEOUT)

    def _play_sound_file(self, soundfile: str):
        try:
            if not os.path.exists(soundfile):
                soundfile = os.path.join(SOUNDS_DIR, soundfile)
            if not os.path.exists(soundfile):
                self.log.error(f"Sound file not found: '{soundfile}'")
                return
            self.log.debug(f"Playing sound file: '{soundfile}'")
            self._is_playing = True
            mixer.init()
            # soundfile = self.get_sound_file_path(soundfile)
            mixer.music.load(soundfile)
            mixer.music.play()
            # Wait for the music to play
            while mixer.music.get_busy():
                pgtime.Clock().tick(10)
        except Exception as e:
            self.log.error(f"Error playing sound file: '{soundfile}': {e}")

    def is_playing(self):
        return mixer.music.get_busy()

    def find_sound_file_matching(self, filename: str, random_choice=False) -> Optional[str]:
        """searches for a sound file matching `filename` in the SOUNDS_DIR directory.
        A filename is a match if its name contains `filename` as a substring, ignoring case.
        If `random` is True and there are several matches, chooses one at random.
        If `random` is False and there are several matches, chooses the first one."""
        # Get list of all mp3 files in the SOUNDS_DIR directory
        all_files = [f for f in os.listdir(SOUNDS_DIR)]
        sound_files = [f for f in all_files if os.path.splitext(f)[1].lower() in self.SUPPORTED_EXTENSIONS]
        matches = [f for f in sound_files if filename.lower() in f.lower()]

        if not matches:
            self.log.error(f"No matching sound files found for '{filename}'")
            return None

        # Choose a file based on the random parameter
        chosen_file = random.choice(matches) if random_choice else matches[0]
        return chosen_file

    def stop_playing(self):
        if self.is_playing():
            mixer.music.stop()

    def play_sound_file_matching(self, partial_filename: str, random_choice: bool = False):
        """Play a sound file matching `partial_filename` in the SOUNDS_DIR directory."""
        soundfile = self.find_sound_file_matching(partial_filename, random_choice)
        if soundfile:
            self.play_sound_file(soundfile)

    def play_rfid_ok_sound(self):
        self.play_sound_file_matching("rfid_ok")

    def play_rfid_error_sound(self):
        self.play_sound_file_matching("rfid_error")

    def play_victory_sound(self):
        self.play_sound_file_matching("victory")

    def play_game_over_sound(self):
        self.play_sound_file_matching("game_over")

    def play_cubebox_reset_sound(self):
        self.play_sound_file_matching("cubebox_reset")


if __name__ == "__main__":
    buzzer = CubeSoundPlayer()
    buzzer.log.setLevel(logging.DEBUG)
    buzzer.log.info("Playing RFID OK sound")
    buzzer.play_rfid_ok_sound()
    buzzer.log.info("Playing RFID error sound")
    buzzer.play_rfid_error_sound()
    buzzer.log.info("Playing victory sound")
    buzzer.play_victory_sound()
    buzzer.log.info("Playing game over sound")
    buzzer.play_game_over_sound()
    buzzer.log.info("Playing cubebox reset sound")
    buzzer.play_cubebox_reset_sound()
    buzzer.log.info("Done")
