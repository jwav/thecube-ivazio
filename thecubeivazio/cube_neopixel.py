import time

from thecubeivazio.cube_utils import is_raspberry_pi, cubetry
from thecubeivazio.cube_config import CubeConfig

CubeNeopixelRgbHue = tuple[int, int, int]
CubeNeopixelRgbColor = tuple[int, int, int]

class _CubeNeopixelInterface:
    """Base interface to define the mock and real classes for the CubeNeopixel class"""
    HUE_WHITE = (1, 1, 1)
    HUE_RED = (1, 0, 0)
    HUE_GREEN = (0, 1, 0)
    HUE_BLUE = (0, 0, 1)
    HUE_YELLOW = (1, 1, 0)
    HUE_CYAN = (0, 1, 1)
    HUE_MAGENTA = (1, 0, 1)

    HUE_UNINITIALIZED = HUE_WHITE
    HUE_WAITING_FOR_RESET = HUE_RED
    HUE_READY_TO_PLAY = HUE_GREEN
    HUE_CURRENTLY_PLAYING = HUE_BLUE
    HUE_ERROR = HUE_MAGENTA
    # from 0 to 255
    DEFAULT_INTENSITY = 25

    def __init__(self):
        self.hue = None
        self._intensity = self.DEFAULT_INTENSITY
        self.update_intensity_from_config()
        self.set_hue_uninitialized()

    @property
    def color(self):
        return self._hue_to_color(self.hue)

    def set_hue(self, color: CubeNeopixelRgbHue):
        self.hue = color
        actual_color = self._hue_to_color(color)
        self._set_neopixel_color(actual_color)

    def _set_neopixel_color(self, color: CubeNeopixelRgbColor):
        """Must be implemented by the child class to actually
        send a color to the neopixel"""
        raise NotImplementedError

    @cubetry
    def _hue_to_color(self, hue: CubeNeopixelRgbHue) -> CubeNeopixelRgbColor:
        # first, normalize the tuple so that the max value is 1
        max_value = max(hue)
        if max_value == 0:
            return hue
        normalized_hue = CubeNeopixelRgbHue(value / max_value for value in hue)
        # then, multiply each value by the intensity
        # noinspection PyTypeChecker
        return CubeNeopixelRgbColor(int(value * self._intensity) for value in normalized_hue)

    def set_intensity(self, intensity: int):
        """sets the intensity from 0 to 255 then reapply the color"""
        self._intensity = max(0, min(255, intensity))
        self.set_hue(self.color)

    def set_hue_wait_for_reset(self):
        self.set_hue(self.HUE_WAITING_FOR_RESET)

    def set_hue_ready_to_play(self):
        self.set_hue(self.HUE_READY_TO_PLAY)

    def set_hue_currently_playing(self):
        self.set_hue(self.HUE_CURRENTLY_PLAYING)

    def set_hue_error(self):
        self.set_hue(self.HUE_ERROR)

    def set_hue_uninitialized(self):
        self.set_hue(self.HUE_UNINITIALIZED)

    def turn_off(self):
        self.set_hue((0, 0, 0))

    def update_intensity_from_config(self) -> bool:
        try:
            config = CubeConfig.get_config()
            self._intensity = config.get_field("cubebox_neopixel_intensity",
                              self.DEFAULT_INTENSITY)
        except Exception as e:
            print(f"Error getting cubebox intensity from config: {e}")
            self._intensity = self.DEFAULT_INTENSITY
            return False




# if we're not on an rpi, we'll be using this mock class
if not is_raspberry_pi():
    class CubeNeopixel(_CubeNeopixelInterface):
        """Mock class to simulate the neopixel library on non-raspberry pi devices"""
        def __init__(self):
            super().__init__()

        def _set_neopixel_color(self, color: CubeNeopixelRgbColor):
            print(f"{self.__class__.__name__}: setting color to {color} (hue: {self.hue}, color:{self.color})")


# if we're on raspberry pi, we'll be using the neopixel library
# elif is_raspberry_pi():
else:
    import board, neopixel


    class CubeNeopixel(_CubeNeopixelInterface):
        """Class to control the neopixel when running on a raspberry pi"""

        def __init__(self):
            self._neopixel = neopixel.NeoPixel(board.D10, 12)
            super().__init__()
            import atexit
            atexit.register(self.__del__)

        def _set_neopixel_color(self, color: CubeNeopixelRgbColor):
            try:
                self._neopixel.fill(color)
                self._color = color
            except Exception as e:
                print(f"Error setting neopixel color: {e}")

        def __del__(self):
            self.turn_off()

if __name__ == "__main__":
    # test colors and turning off
    cube = CubeNeopixel()
    cube.set_hue(CubeNeopixel.HUE_UNINITIALIZED)
    time.sleep(1)
    cube.set_hue(CubeNeopixel.HUE_ERROR)
    time.sleep(1)
    cube.set_hue(CubeNeopixel.HUE_WAITING_FOR_RESET)
    time.sleep(1)
    cube.set_hue(CubeNeopixel.HUE_READY_TO_PLAY)
    time.sleep(1)
    cube.set_hue(CubeNeopixel.HUE_CURRENTLY_PLAYING)
    time.sleep(1)
    cube.set_hue((0, 0, 0))
