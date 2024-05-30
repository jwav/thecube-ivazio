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


class CubeRgbTextDrawer(SampleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        msg1 = CubeRgbText(matrix_id=0, text="BERLIN")
        msg2 = CubeRgbText(matrix_id=1, text="BUDAPEST")
        messages = [msg1, msg2]
        # messages = [msg1]

        while True:
            offscreen_canvas.Clear()
            for msg in messages:
                msg.draw(canvas=offscreen_canvas)
            time.sleep(1)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)

class CubeRgbText:
    PANEL_WIDTH = 64
    X_MARGIN = 0
    Y_TIME = 30
    def __init__(self, matrix_id:int, text:str):
        self.text = text
        self.matrix_id = matrix_id
        self.x = matrix_id * self.PANEL_WIDTH + self.X_MARGIN
        self.start_time = time.time()
        self.font = graphics.Font()
        self.font.LoadFont(os.path.join(RGB_FONTS_DIR, "7x13.bdf"))
        self.textColor = graphics.Color(255, 255, 0)

    def draw(self, canvas):
        graphics.DrawText(canvas, self.font, self.x, self.Y_TIME, self.textColor, self.text)


# TODO: implement
class CubeMasterLedMatrices:
    # TODO: set this in a config file
    NB_MATRICES = 2
    PANEL_WIDTH = 64
    X_MARGIN = 0
    Y_TIME = 30
    def __init__(self):
        self._drawer = CubeRgbTextDrawer()
        self._thread = threading.Thread()
        self._keep_running = False


    def run(self):
        self._thread = threading.Thread(target=self._drawing_loop)
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self._keep_running = False
        self._thread.join(timeout=0.5)

    def _drawing_loop(self):
        # NOTE: DO NOT copy the canvas in a CubeRgbText instance property.
        # it seems to create new canvas instances, and makes the message disappear
        start_time = time.time()
        offscreen_canvas = self._drawer.matrix.CreateFrameCanvas()

        while self._keep_running:
            offscreen_canvas.Clear()
            for matrix_id in range(self.NB_MATRICES):
                # timestr = cube_utils.seconds_to_hhmmss_string(time.time() - start_time)
                text = f"aaa{matrix_id}"
                CubeRgbText(matrix_id=matrix_id, text=text).draw(canvas=offscreen_canvas)

            time.sleep(1)
            offscreen_canvas = self._drawer.matrix.SwapOnVSync(offscreen_canvas)




# TODO: test display
if __name__ == "__main__":
    import atexit
    lm = CubeMasterLedMatrices()
    atexit.register(lm.stop)
    lm.run()
