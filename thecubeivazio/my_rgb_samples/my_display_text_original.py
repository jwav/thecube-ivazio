#!/usr/bin/env python
# Display a runtext with double-buffering.
from samplebase import SampleBase
from rgbmatrix import graphics
import time
import datetime

def seconds_to_hhmmss(seconds):
        return str(datetime.timedelta(seconds=seconds))

class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        font = graphics.Font()
        font.LoadFont("/home/pi/rpi-rgb-led-matrix/rgb_fonts/7x13.bdf")
        textColor = graphics.Color(255, 255, 0)
        w = offscreen_canvas.width
        team_name = "BERLIN"
        allocated_seconds = 3605
        start_time = time.time() + allocated_seconds
        x_name = 11
        y_name = 10
        x_time = 8
        y_time = 30

        while True:
            offscreen_canvas.Clear()
            length = graphics.DrawText(offscreen_canvas, font, x_name, y_name, textColor, team_name)
            # print("team_name length:", length)
            time_str = seconds_to_hhmmss(int(start_time - time.time()))
            length = graphics.DrawText(offscreen_canvas, font, x_time, y_time, textColor, time_str)
            # print("time_str length:", length)
            print(time_str)

            time.sleep(1)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
