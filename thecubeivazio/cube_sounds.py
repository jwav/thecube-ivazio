"""Handles everything related to the buzzer.
Interfaces a piezo buzzer to the RaspberryPi or plays sound files if not on the RaspberryPi."""
import logging
import random
import subprocess
import threading
import time
import pygame.mixer as mixer
import pygame.time as pgtime

from thecubeivazio import cube_logger
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_utils import is_raspberry_pi


class CubeSoundPlayer:
    DEFAULT_VOLUME_PERCENT = 100
    MAX_VOLUME_PERCENT = 1000
    SUPPORTED_EXTENSIONS = ['.wav', '.mp3', '.ogg', '.flac', '.mod', '.s3m', '.it', '.xm']

    def __init__(self, init_timeout_sec:float=None):
        self._is_initialized = False
        self._is_initializing = False  # Flag to prevent recursion
        self.log = cube_logger.CubeLogger("CubeSoundPlayer")
        self.log.setLevel(logging.INFO)
        self._playing_thread = None
        self.log.info(f"Sounds directory: '{SOUNDS_DIR}'")
        self.initialize(init_timeout_sec=init_timeout_sec)

    def __del__(self):
        try:
            # self.stop_playing()
            mixer.quit()
        except Exception as e:
            self.log.error(f"Error cleaning up CubeSoundPlayer: {e}")

    def initialize(self, init_timeout_sec:float=None) -> bool:
        """Initialize the sound player.
        First tries to initialize using PulseAudio, then falls back to ALSA.
        if init_timeout_sec is not None, it will wait for the initialization to complete for that many seconds.
        """
        end_time = time.time() + (init_timeout_sec or 0)
        success = False
        while True:
            if self._is_initialized:
                success = True
                break
            if self._is_initializing:  # Prevent re-entry
                self.log.warning("Initialization already in progress, preventing re-entry.")
                return False
            self._is_initializing = True  # Set the flag

            if self._initialize("pulseaudio"):
                success = True
                break
            if self._initialize("alsa"):
                success = True
                break
            if init_timeout_sec and time.time() > end_time:
                self.log.error("Initialization timed out.")
                self._is_initializing = False
                success = False
                break
            time.sleep(0.5)

        self._is_initialized = success
        return success


        self._is_initializing = False  # Clear the flag on failure
        return False

    def _initialize(self, sdl_audiodriver: str = 'pulseaudio') -> bool:
        try:
            # only set SDL_AUDIODRIVER and AUDIODEV on RaspberryPi, not on desktop
            if is_raspberry_pi():
                os.environ['SDL_AUDIODRIVER'] = sdl_audiodriver
                os.environ['AUDIODEV'] = 'hw:1,0'
                # start pulseaudio if not running
                subprocess.run(['pulseaudio', '--start'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # start alsa if not running
                subprocess.run(['sudo', 'systemctl', 'start', 'alsa-restore'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['sudo', 'systemctl', 'start', 'alsa-state'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            mixer.init(frequency=44100, size=-16, channels=1, buffer=4096)
            self.set_volume_percent(self.DEFAULT_VOLUME_PERCENT)
            self._is_initialized = True
            self.log.success("CubeSoundPlayer initialized")
        except Exception as e:
            self.log.error(f"Error initializing CubeSoundPlayer: {e}")
            self._is_initialized = False
        finally:
            return self._is_initialized

    def is_initialized(self):
        return self._is_initialized

    @cubetry
    def set_volume_to_maximum(self):
        self.set_volume_percent(self.MAX_VOLUME_PERCENT)

    @cubetry
    def set_volume_percent(self, volume_percent: Union[int, float]):
        if not is_raspberry_pi():
            return
        if not self._is_initialized:
            self.log.warning("CubeSoundPlayer not initialized. Initializing...")
            if not self.initialize():
                self.log.error("Failed to initialize CubeSoundPlayer.")
                return

        if not isinstance(volume_percent, (int, float)):
            self.log.warning(f"Invalid volume_percent: {volume_percent}. Using default volume.")
            volume_percent = self.DEFAULT_VOLUME_PERCENT

        self.log.info(f"Setting volume to {volume_percent}%")
        volume_level = int(volume_percent)

        try:
            subprocess.run(['amixer', 'set', 'Master', f'{volume_level}%'],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log.info(f"Volume set to {volume_level}% using amixer")
        except subprocess.CalledProcessError as e:
            self.log.error(f"Failed to set volume using amixer: {e}")

        try:
            subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{volume_level}%'],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log.info(f"Volume set to {volume_level}% using pactl")
        except subprocess.CalledProcessError as e:
            self.log.error(f"Failed to set volume using pactl: {e}")

    @cubetry
    def play_sound_file(self, soundfile: str):
        self.log.info(f"Playing sound file: '{soundfile}'")
        self._playing_thread = threading.Thread(target=self._play_sound_file, args=(soundfile,), daemon=True)
        self._playing_thread.start()
        self._playing_thread.join(timeout=STATUS_REPLY_TIMEOUT)

    def _play_sound_file(self, soundfile: str, wait_for_finish: bool = True):
        try:
            if not self.is_initialized():
                self.log.warning("CubeSoundPlayer not initialized. Initializing...")
                if not self.initialize():
                    self.log.error("Failed to initialize CubeSoundPlayer.")
                    return
            if not os.path.exists(soundfile):
                soundfile = os.path.join(SOUNDS_DIR, soundfile)
            if not os.path.exists(soundfile):
                self.log.error(f"Sound file not found: '{soundfile}'")
                return
            self.log.debug(f"Playing sound file: '{soundfile}'")
            mixer.music.load(soundfile)
            mixer.music.play()
            if wait_for_finish:
                while mixer.music.get_busy():
                    pgtime.Clock().tick(10)
        except Exception as e:
            self.log.error(f"Error playing sound file: '{soundfile}': {e}")
            if "mixer not initialized" in str(e):
                self.log.info("Trying to reinitialize mixer...")
                if not self._initialize():
                    self.log.error("Failed to reinitialize mixer.")

    @cubetry
    def is_playing(self):
        return mixer.music.get_busy()

    @cubetry
    def find_sound_file_matching(self, filename: str, random_choice=False) -> Optional[str]:
        all_files = [f for f in os.listdir(SOUNDS_DIR)]
        sound_files = [f for f in all_files if os.path.splitext(f)[1].lower() in self.SUPPORTED_EXTENSIONS]
        matches = [f for f in sound_files if filename.lower() in f.lower()]

        if not matches:
            self.log.error(f"No matching sound files found for '{filename}'")
            return None

        chosen_file = random.choice(matches) if random_choice else matches[0]
        return chosen_file

    @cubetry
    def stop_playing(self):
        if self.is_playing():
            mixer.music.stop()

    @cubetry
    def play_sound_file_matching(self, partial_filename: str, random_choice: bool = False):
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

    def play_startup_sound(self):
        self.play_sound_file_matching("startup")


def test_sounds():
    player = CubeSoundPlayer()
    player.log.setLevel(logging.DEBUG)
    player.log.info("Playing startup sound")
    player.play_startup_sound()
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
    test_sounds()
    # test_volume()
