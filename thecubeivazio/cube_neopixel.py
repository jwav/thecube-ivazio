from thecubeivazio.cube_utils import is_raspberry_pi, cubetry
import time

# if we're not on an rpi, we'll be using this mock class
if not is_raspberry_pi():
    class CubeNeopixel:
        COLOR_WAITING_FOR_RESET = (255,0,0)
        COLOR_READY_TO_PLAY = (0,255,0)
        COLOR_CURRENTLY_PLAYING = (0,0,255)
        def __init__(self):
            pass
        def set_color(self, color: tuple[int,int,int]):
            print("CubeNeopixel.set_color called with color: ", color)


# if we're on raspberry pi, we'll be using the neopixel library
else:
    import board, neopixel
    class CubeNeopixel:
        COLOR_WAITING_FOR_RESET = (25,0,0)
        COLOR_READY_TO_PLAY = (0,25,0)
        COLOR_CURRENTLY_PLAYING = (0,0,25)
        def __init__(self):
            self.instance = neopixel.NeoPixel(board.D10, 12)

        @cubetry
        def set_color(self, color: tuple[int,int,int]):
            self.instance.fill(color)

        def __del__(self):
            try:
                self.set_color((0,0,0))
            except Exception as e:
                print(f"Error in CubeNeopixel.__del__: {e}")

if __name__ == "__main__":
    #test colors and turning off
    cube = CubeNeopixel()
    cube.set_color(CubeNeopixel.COLOR_WAITING_FOR_RESET)
    time.sleep(1)
    cube.set_color(CubeNeopixel.COLOR_READY_TO_PLAY)
    time.sleep(1)
    cube.set_color(CubeNeopixel.COLOR_CURRENTLY_PLAYING)
    time.sleep(1)
    cube.set_color((0,0,0))
