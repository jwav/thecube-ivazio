# TODO: add imports and test method
import ctypes
import sys
import threading

# RGB matrix lib imports
from rgbmatrix_samplebase import SampleBase
from rgbmatrix import graphics

import os
import time
import datetime


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
        # print("CubeRgbTextDrawer args:", self.args)
        self._keep_running = False
        self.messages = ["foo", "bar"]

    def run(self):
        print("CubeRgbTextDrawer running")
        self._keep_running = True
        # NOTE: DO NOT copy the canvas in a CubeRgbText instance property.
        # it seems to create new canvas instances, and makes the message disappear
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        while self._keep_running:
            offscreen_canvas.Clear()
            for msg in self.messages:
                msg.draw(canvas=offscreen_canvas)
            time.sleep(1)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)
        print("CubeRgbTextDrawer stopped")

    def stop(self):
        self._keep_running = False


class CubeRgbText:
    def __init__(self, matrix_id: int, text: str):
        self.text = text
        self.matrix_id = matrix_id
        self.x = matrix_id * PANEL_WIDTH + X_MARGIN
        self.start_time = time.time()
        self.font = graphics.Font()
        self.font.LoadFont(os.path.join("7x13.bdf"))
        self.textColor = graphics.Color(255, 255, 0)

    def draw(self, canvas):
        graphics.DrawText(canvas, self.font, self.x, Y_TEXT, self.textColor, self.text)


class CubeRgbMatrixManager:
    """A wrapper for CubeRgbTextDrawer, because CubeRgbTextDrawer is not run with `run`, but `process`.
    I'd like to keep it coherent"""
    def __init__(self):
        self._drawer = CubeRgbTextDrawer()
        # self._thread = threading.Thread(target=self._drawer.process)

    def run(self):
        self._drawer.process()
        # self._thread.start()

    def stop(self):
        self._drawer.stop()
        # self._thread.join(timeout=1)


def check_capabilities():
    CAP_SYS_NICE = 24
    CAP_DAC_OVERRIDE = 1

    libc = ctypes.CDLL('libc.so.6', use_errno=True)

    class CapHeader(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32),
                    ("pid", ctypes.c_int)]

    class CapData(ctypes.Structure):
        _fields_ = [("effective", ctypes.c_uint32),
                    ("permitted", ctypes.c_uint32),
                    ("inheritable", ctypes.c_uint32)]

    header = CapHeader()
    data = (CapData * 2)()
    header.version = 0x19980330
    header.pid = 0

    if libc.capget(ctypes.byref(header), ctypes.byref(data)) != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))

    cap_sys_nice = (data[0].effective & (1 << CAP_SYS_NICE)) != 0
    cap_dac_override = (data[0].effective & (1 << CAP_DAC_OVERRIDE)) != 0

    print(f"Effective UID: {os.geteuid()}")
    print(f"Has CAP_SYS_NICE? {cap_sys_nice}")
    print(f"Has CAP_DAC_OVERRIDE? {cap_dac_override}")


# TODO: test display
if __name__ == "__main__":
    # check_capabilities()
    # if not os.geteuid() == 0 and not (check_capabilities()):
    #     print("Need root or appropriate capabilities to run this script.")
    #     exit(1)
    import atexit

    drawer = CubeRgbTextDrawer()
    drawer.process()
    exit(0)
    lm = CubeRgbMatrixManager()
    atexit.register(lm.stop)
    lm.run()
