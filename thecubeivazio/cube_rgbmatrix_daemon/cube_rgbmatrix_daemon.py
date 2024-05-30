# TODO: add imports and test method
import ctypes
import sys
import threading
import os
import time
import datetime
import subprocess

# RGB matrix lib imports
# local import rgbmatrix_samplebase
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), './'))
if module_path not in sys.path:
    sys.path.append(module_path)
from rgbmatrix_samplebase import SampleBase
from rgbmatrix import graphics




RGGMATRIX_DAEMON_TEXT_FILENAME = "cube_rgbmatrix_daemon_text.txt"
NB_MATRICES = 2
PANEL_WIDTH = 64
PANEL_HEIGHT = 32
X_MARGIN = 0
Y_TEXT = 30
LED_SLOWDOWN_GPIO = 5

class CubeRgbMatrixDaemon(SampleBase):
    # singleton instance for the subprocess
    _static_process = None

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

    @staticmethod
    def write_lines_to_daemon_file(lines: list[str]):
        with open(RGGMATRIX_DAEMON_TEXT_FILENAME, "w") as f:
            f.write("\n".join(lines))

    @staticmethod
    def read_lines_from_daemon_file() -> list[str]:
        with open(RGGMATRIX_DAEMON_TEXT_FILENAME, "r") as f:
            return f.readlines()

    @classmethod
    def launch_process(cls) -> bool:
        if cls._static_process:
            print(f"{cls.__name__} :  process already running")
            return False
        daemon_path = os.path.abspath(__file__)
        cls._static_process = subprocess.Popen(['sudo', 'python3', daemon_path])
        return True

    @classmethod
    def stop_process(cls, timeout=2):
        print(f"{cls.__name__} : stopping process")
        try:
            if cls._static_process:
                cls._static_process.terminate()
                cls._static_process.wait(timeout=timeout)
        except Exception as e:
            print(f"{cls.__name__} : Error stopping process: {e}")

    def run(self):
        print("CubeRgbTextDrawer running")
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
        self._keep_running = False


# TODO: make obsolete
class CubeRgbText:
    def __init__(self, matrix_id: int, text: str):
        self.text = text
        self.matrix_id = matrix_id
        self.x = matrix_id * PANEL_WIDTH + X_MARGIN
        self.start_time = time.time()
        self.font = graphics.Font()
        self.font.LoadFont(os.path.join("../7x13.bdf"))
        self.textColor = graphics.Color(255, 255, 0)

    def draw(self, canvas):
        graphics.DrawText(canvas, self.font, self.x, Y_TEXT, self.textColor, self.text)






# TODO: test display
if __name__ == "__main__":
    daemon = CubeRgbMatrixDaemon()
    daemon.run()