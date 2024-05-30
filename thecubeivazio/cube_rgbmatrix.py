# TODO: add imports and test method
import ctypes
import sys
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


def has_capability(cap):
    # Define necessary constants
    CAP_SYS_NICE = 24
    CAP_DAC_OVERRIDE = 1

    # Map capability names to their values
    cap_map = {
        'cap_sys_nice': CAP_SYS_NICE,
        'cap_dac_override': CAP_DAC_OVERRIDE
    }

    cap_val = cap_map.get(cap)
    if cap_val is None:
        return False

    # Check if the process has the specified capability
    libc = ctypes.CDLL('libc.so.6', use_errno=True)
    cap_data = (ctypes.c_uint32 * 2)()
    if libc.capget(ctypes.byref(cap_data), ctypes.byref(cap_data)) != 0:
        return False

    return (cap_data[0] & (1 << cap_val)) != 0


# TODO: test display
if __name__ == "__main__":
    print("has cap_sys_nice ?", has_capability('cap_sys_nice'))
    print("has cap_dac_override ?", has_capability('cap_dac_override'))
    if not os.geteuid() == 0 and not (has_capability('cap_sys_nice') and has_capability('cap_dac_override')):
        print("Need root or appropriate capabilities to run this script.")
    exit(1)
    import atexit

    lm = CubeRgbMatrixManager()
    atexit.register(lm.stop)
    lm.run()
