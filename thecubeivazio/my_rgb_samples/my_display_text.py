#!/usr/bin/env python
# Display a runtext with double-buffering.
from samplebase import SampleBase
from rgbmatrix import graphics
import time
import datetime

def seconds_to_hhmmss(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

# NOTE: DO NOT copy the canvas in an instance property. it seems to create new canvas instances, and makes the message disappear
class Message:
    PANEL_WIDTH = 64
    X_MARGIN = 0
    Y_NAME = 10
    Y_TIME = 30
    def __init__(self, id, team, initial_seconds):
        self.team = team
        self.id = id
        self.x = id * self.PANEL_WIDTH + self.X_MARGIN
        self.initial_seconds = initial_seconds
        self.start_time = time.time()
        self.font = graphics.Font()
        self.font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/7x13.bdf")
        self.textColor = graphics.Color(255, 255, 0)

    @property
    def remaining_seconds(self) -> int:
        return int(self.initial_seconds - (time.time() - self.start_time))

    def draw(self, canvas):
        graphics.DrawText(canvas, self.font, self.x, self.Y_NAME, self.textColor, self.team)
        time_str = seconds_to_hhmmss(self.remaining_seconds)
        graphics.DrawText(canvas, self.font, self.x, self.Y_TIME, self.textColor, time_str)
        print(self.team, time_str)



class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()
        msg1 = Message(team="BERLIN", id=0, initial_seconds=3605)
        msg2 = Message(team="BUDAPEST", id=1, initial_seconds=3609)
        messages = [msg1, msg2]
        # messages = [msg1]

        while True:
            offscreen_canvas.Clear()
            for msg in messages:
                msg.draw(canvas=offscreen_canvas)
            time.sleep(1)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
