# TODO: add imports and test method
import threading

# RGB matrix lib imports
from thecubeivazio.rgbmatrix_samplebase import SampleBase
from rgbmatrix import graphics

import os
import time
import datetime

from thecubeivazio.cube_common_defines import *
from thecubeivazio import cube_utils

NB_MATRICES = 2
PANEL_WIDTH = 64
PANEL_HEIGHT = 32
X_MARGIN = 0
Y_TEXT = 30
LED_SLOWDOWN_GPIO = 5

class CubeRgbTextDrawer(SampleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        known_args, _ = self.parser.parse_known_args([
            f'--led-cols={PANEL_WIDTH}',
            f'--led-rows={PANEL_HEIGHT}',
            f'--led-chain={NB_MATRICES}',
            f'--led-slowdown-gpio={LED_SLOWDOWN_GPIO}',
            f'--isolcpus=3'
        ])
        self.args = known_args
        print("CubeRgbTextDrawer args:", self.args)
        self._keep_running = False
        self.messages = []

    def run(self):
        # NOTE: DO NOT copy the canvas in a CubeRgbText instance property.
        # it seems to create new canvas instances, and makes the message disappear
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        while self._keep_running:
            offscreen_canvas.Clear()
            for msg in self.messages:
                msg.draw(canvas=offscreen_canvas)
            time.sleep(1)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)

    def stop(self):
        self._keep_running = False


class CubeRgbText:
    def __init__(self, matrix_id: int, text: str):
        self.text = text
        self.matrix_id = matrix_id
        self.x = matrix_id * PANEL_WIDTH + X_MARGIN
        self.start_time = time.time()
        self.font = graphics.Font()
        self.font.LoadFont(os.path.join(RGB_FONTS_DIR, "7x13.bdf"))
        self.textColor = graphics.Color(255, 255, 0)

    def draw(self, canvas):
        graphics.DrawText(canvas, self.font, self.x, Y_TEXT, self.textColor, self.text)


class CubeRgbMatrixManager:
    """A wrapper for CubeRgbTextDrawer, because CubeRgbTextDrawer is not run with `run`, but `process`.
    I'd like to keep it coherent"""
    def __init__(self):
        self._drawer = CubeRgbTextDrawer()
        self._thread = threading.Thread(target=self._drawer.process)
        self._keep_running = False

    def run(self):
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self._drawer.stop()
        self._thread.join(timeout=1)



# TODO: test display
if __name__ == "__main__":
    import atexit

    lm = CubeRgbMatrixManager()
    atexit.register(lm.stop)
    lm.run()
