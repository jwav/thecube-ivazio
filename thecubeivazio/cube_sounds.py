"""Handles everything related to the buzzer.
Interfaces a piezo buzzer to the RaspberryPi or plays sound files if not on the RaspberryPi."""
import logging
import random
import threading

import pygame.mixer as mixer
import pygame.time as pgtime

from thecubeivazio import cube_logger
from thecubeivazio.cube_common_defines import *


class CubeSoundPlayer:
    DEFAULT_VOLUME_PERCENT = 100
    SUPPORTED_EXTENSIONS = ['.wav', '.mp3', '.ogg', '.flac', '.mod', '.s3m', '.it', '.xm']

    def __init__(self):
        self._is_initialized = False
        self.log = cube_logger.CubeLogger("Buzzer")
        self.log.setLevel(logging.INFO)
        self._playing_thread = None
        self.log.info(f"Sounds directory: '{SOUNDS_DIR}'")
        self.initialize()


    def __del__(self):
        try:
            # self.stop_playing()
            mixer.quit()
        except Exception as e:
            self.log.error(f"Error cleaning up CubeSoundPlayer: {e}")

    def initialize(self):
        try:
            # alsa fails for cubemaster, but pulseaudio works
            # os.environ['SDL_AUDIODRIVER'] = 'alsa'
            os.environ['SDL_AUDIODRIVER'] = 'pulseaudio'
            os.environ['AUDIODEV'] = 'hw:1,0'

            # mixer.init()
            mixer.init(frequency=44100, size=-16, channels=1, buffer=4096)
            self.set_volume_percent(self.DEFAULT_VOLUME_PERCENT)
            self._is_initialized = True
            self.log.success("CubeSoundPlayer initialized")
        except Exception as e:
            self.log.error(f"Error initializing CubeSoundPlayer: {e}")
            self._is_initialized = False

    def is_initialized(self):
        return self._is_initialized

    @cubetry
    def set_volume_percent(self, volume_percent: int):
        """Set the volume of the buzzer."""
        self.log.info(f"Setting volume to {volume_percent}%")
        mixer.music.set_volume(volume_percent / 100)

    @cubetry
    def play_sound_file(self, soundfile: str):
        """Play a sound file or a tune on the buzzer."""
        self.log.info(f"Playing sound file: '{soundfile}'")
        self._playing_thread = threading.Thread(target=self._play_sound_file, args=(soundfile,), daemon=True)
        self._playing_thread.start()
        self._playing_thread.join(timeout=STATUS_REPLY_TIMEOUT)

    def _play_sound_file(self, soundfile: str):
        try:
            if not os.path.exists(soundfile):
                soundfile = os.path.join(SOUNDS_DIR, soundfile)
            if not os.path.exists(soundfile):
                self.log.error(f"Sound file not found: '{soundfile}'")
                return
            self.log.debug(f"Playing sound file: '{soundfile}'")
            # soundfile = self.get_sound_file_path(soundfile)
            mixer.music.load(soundfile)
            mixer.music.play()
            # Wait for the music to play
            while mixer.music.get_busy():
                pgtime.Clock().tick(10)
        except Exception as e:
            self.log.error(f"Error playing sound file: '{soundfile}': {e}")

    @cubetry
    def is_playing(self):
        return mixer.music.get_busy()

    @cubetry
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

    @cubetry
    def stop_playing(self):
        if self.is_playing():
            mixer.music.stop()

    @cubetry
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


def test_sounds():
    player = CubeSoundPlayer()
    player.log.setLevel(logging.DEBUG)
    player.log.info("Playing RFID OK sound")
    player.play_rfid_ok_sound()
    player.log.info("Playing RFID error sound")
    player.play_rfid_error_sound()
    player.log.info("Playing victory sound")
    player.play_victory_sound()
    player.log.info("Playing game over sound")
    player.play_game_over_sound()
    player.log.info("Playing cubebox reset sound")
    player.play_cubebox_reset_sound()
    player.log.info("Done")

def test_volume():
    player = CubeSoundPlayer()
    player.log.setLevel(logging.DEBUG)
    player.set_volume_percent(100)
    player.play_sound_file_matching("rfid_ok")
    player.set_volume_percent(50)
    player.play_sound_file_matching("rfid_ok")
    player.set_volume_percent(10)
    player.play_sound_file_matching("rfid_ok")

if __name__ == "__main__":
    # test_sounds()
    test_volume()

