import time

from thecubeivazio.cube_utils import is_raspberry_pi, cubetry


class _CubeNeopixelInterface:
    """Base interface to define the mock and real classes for the CubeNeopixel class"""
    COLOR_WAITING_FOR_RESET = (25, 0, 0)
    COLOR_READY_TO_PLAY = (0, 25, 0)
    COLOR_CURRENTLY_PLAYING = (0, 0, 25)
    COLOR_ERROR = (25, 0, 25)

    def __init__(self):
        self._color = None

    @property
    def color(self):
        return self._color

    def set_color(self, color: tuple[int, int, int]):
        raise NotImplementedError

    def set_color_wait_for_reset(self):
        self.set_color(self.COLOR_WAITING_FOR_RESET)

    def set_color_ready_to_play(self):
        self.set_color(self.COLOR_READY_TO_PLAY)

    def set_color_currently_playing(self):
        self.set_color(self.COLOR_CURRENTLY_PLAYING)

    def set_color_error(self):
        self.set_color(self.COLOR_ERROR)


# if we're not on an rpi, we'll be using this mock class
if not is_raspberry_pi():
    class CubeNeopixel(_CubeNeopixelInterface):
        """Mock class to simulate the neopixel library on non-raspberry pi devices"""
        def __init__(self):
            super().__init__()
            self._color = None

        def set_color(self, color: tuple[int, int, int]):
            print("CubeNeopixel.set_color called with color: ", color)
            self._color = color


# if we're on raspberry pi, we'll be using the neopixel library
# elif is_raspberry_pi():
else:
    import board, neopixel


    class CubeNeopixel(_CubeNeopixelInterface):
        """Class to control the neopixel when running on a raspberry pi"""

        def __init__(self):
            super().__init__()
            self._neopixel = neopixel.NeoPixel(board.D10, 12)
            self.set_color(self.COLOR_ERROR)
            self._color = None
            import atexit
            atexit.register(self.__del__)

        @cubetry
        def set_color(self, color: tuple[int, int, int]):
            self._neopixel.fill(color)
            self._color = color

        def __del__(self):
            try:
                # turn off the light
                self.set_color((0, 0, 0))
            except Exception as e:
                print(f"Error in CubeNeopixel.__del__: {e}")

if __name__ == "__main__":
    # test colors and turning off
    cube = CubeNeopixel()
    cube.set_color(CubeNeopixel.COLOR_ERROR)
    time.sleep(1)
    cube.set_color(CubeNeopixel.COLOR_WAITING_FOR_RESET)
    time.sleep(1)
    cube.set_color(CubeNeopixel.COLOR_READY_TO_PLAY)
    time.sleep(1)
    cube.set_color(CubeNeopixel.COLOR_CURRENTLY_PLAYING)
    time.sleep(1)
    cube.set_color((0, 0, 0))
