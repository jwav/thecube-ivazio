# TODO: add imports and test method
import ctypes
import fcntl
import logging
import sys
import threading
import os
import time
import datetime
import subprocess

from logging.handlers import RotatingFileHandler

# RGB matrix lib imports
# local import rgbmatrix_samplebase
# RGBMATRIX_DAEMON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), './'))
RGBMATRIX_DAEMON_PY_PATH = os.path.abspath(__file__)
RGBMATRIX_DAEMON_DIR_PATH = os.path.dirname(RGBMATRIX_DAEMON_PY_PATH)

if RGBMATRIX_DAEMON_DIR_PATH not in sys.path:
    sys.path.append(RGBMATRIX_DAEMON_DIR_PATH)
from rgbmatrix_samplebase import SampleBase
from rgbmatrix import graphics




RGBMATRIX_DAEMON_TEXT_FILENAME = "cube_rgbmatrix_daemon_text.txt"
RGBMATRIX_DAEMON_TEXT_FILEPATH = os.path.join(RGBMATRIX_DAEMON_DIR_PATH, RGBMATRIX_DAEMON_TEXT_FILENAME)
RGBMATRIX_DAEMON_LOG_FILEPATH = os.path.join(RGBMATRIX_DAEMON_DIR_PATH, "rgbmatrix_daemon.log")
NB_MATRICES = 2
PANEL_WIDTH = 64
PANEL_HEIGHT = 32
X_MARGIN = 0
Y_TEXT = 30
LED_SLOWDOWN_GPIO = 5

class CubeRgbMatrixDaemon(SampleBase):
    # singleton instance for the subprocess
    _static_process = None

    # Create a logger object
    log = logging.getLogger('RGBMatrixDaemon')
    log.setLevel(logging.DEBUG)
    file_handler = RotatingFileHandler(RGBMATRIX_DAEMON_LOG_FILEPATH, maxBytes=1024*1024, backupCount=1)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    log.addHandler(console_handler)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # known_args, _ = self.parser.parse_known_args([
        #     f'--led-cols={PANEL_WIDTH}',
        #     f'--led-rows={PANEL_HEIGHT}',
        #     f'--led-chain={NB_MATRICES}',
        #     f'--led-slowdown-gpio={LED_SLOWDOWN_GPIO}',
        # ])
        # self.args = known_args
        sys.argv.extend([
            '--led-cols=64',
            '--led-rows=32',
            '--led-chain=2',
            '--led-slowdown-gpio=5'
        ])
        # print("CubeRgbTextDrawer args:", self.args)
        self._keep_running = False
        self.texts = ["foo", "bar"]
        self.start_time = time.time()
        self.font = graphics.Font()
        self.font.LoadFont(os.path.join("7x13.bdf"))
        self.textColor = graphics.Color(255, 255, 0)



    @classmethod
    def write_lines_to_daemon_file(cls, lines: list[str]):
        try:
            with open(RGBMATRIX_DAEMON_TEXT_FILEPATH, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write("\n".join(lines)+"\n")
                fcntl.flock(f, fcntl.LOCK_UN)
            return True
        except Exception as e:
            cls.log.error(f"Error writing to file: {e}")
            return False

    @classmethod
    def read_lines_from_daemon_file(cls) -> list[str]:
        try:
            with open(RGBMATRIX_DAEMON_TEXT_FILEPATH, "r") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                ret = [s.strip() for s in f.readlines()]
                fcntl.flock(f, fcntl.LOCK_UN)
                return ret
        except Exception as e:
            cls.log.error(f"Error reading from file: {e}")
            return []

    @classmethod
    def launch_process(cls) -> bool:
        if cls._static_process:
            cls.log.warning(f"{cls.__name__} :  process already running")
            return False
        daemon_path = os.path.abspath(__file__)
        cls._static_process = subprocess.Popen(['sudo', 'python3', daemon_path])
        cls.log.info(f"{cls.__name__} :  process launched")
        return True

    @classmethod
    def stop_process(cls, timeout=2):
        cls.log.info(f"{cls.__name__} : stopping process")
        try:
            if cls._static_process:
                cls._static_process.terminate()
                cls._static_process.wait(timeout=timeout)
        except Exception as e:
            print(f"{cls.__name__} : Error stopping process: {e}")

    def start(self):
        return self.process()

    def run(self):
        self.log.info("CubeRgbTextDrawer running")
        self._keep_running = True
        # NOTE: DO NOT copy the canvas in a CubeRgbText instance property.
        # it seems to create new canvas instances, and makes the message disappear
        canvas = self.matrix.CreateFrameCanvas()
        while self._keep_running:
            self.texts = self.read_lines_from_daemon_file()
            canvas.Clear()
            for matrix_id,text in enumerate(self.texts):
                x = matrix_id * PANEL_WIDTH + X_MARGIN
                graphics.DrawText(canvas, self.font, x, Y_TEXT, self.textColor, text)
            time.sleep(1)
            canvas = self.matrix.SwapOnVSync(canvas)
        print("CubeRgbTextDrawer stopped")

    def stop(self):
        self.log.info("CubeRgbTextDrawer stopping")
        self._keep_running = False




# TODO: test display
if __name__ == "__main__":
    print(f"log filepath: {RGBMATRIX_DAEMON_LOG_FILEPATH}")
    daemon = CubeRgbMatrixDaemon()
    CubeRgbMatrixDaemon.write_lines_to_daemon_file(["aaa", "bbb"])
    lines_read = CubeRgbMatrixDaemon.read_lines_from_daemon_file()
    print(f"lines read: {lines_read}")

    if not daemon.start():
        exit(1)
    exit(0)