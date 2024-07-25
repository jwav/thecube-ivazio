# TODO: add imports and test method
import datetime
import logging
import os
import random
import subprocess
import sys
import threading
import time

# RGB matrix lib imports
# local import rgbmatrix_samplebase
# RGBMATRIX_DAEMON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), './'))
# RGBMATRIX_DAEMON_PY_PATH = os.path.abspath(__file__)
# RGBMATRIX_DAEMON_DIR_PATH = os.path.dirname(RGBMATRIX_DAEMON_PY_PATH)

# home_dir = os.path.expanduser("~")
home_dir = "/home/ivazio"
mnt_shared_dir = "/mnt/shared"

possible_daemon_dirs = [
    os.path.join(home_dir, "thecube-ivazio/thecubeivazio/cube_rgbmatrix_daemon"),
    os.path.join(mnt_shared_dir, "thecube-ivazio/thecubeivazio/cube_rgbmatrix_daemon")
]

for path in possible_daemon_dirs:
    if os.path.exists(path):
        RGBMATRIX_DAEMON_DIR = path
        print(f"RGBMATRIX_DAEMON_DIR_PATH found: {RGBMATRIX_DAEMON_DIR}")
        break
else:
    print("RGBMATRIX_DAEMON_DIR not found")
    RGBMATRIX_DAEMON_DIR = None
    raise FileNotFoundError("RGBMATRIX_DAEMON_DIR not found")

if RGBMATRIX_DAEMON_DIR not in sys.path:
    sys.path.append(RGBMATRIX_DAEMON_DIR)


RGBMATRIX_DAEMON_LOG_FILEPATH = os.path.join(RGBMATRIX_DAEMON_DIR, "rgbmatrix_daemon.log")
print(f"RGBMATRIX_DAEMON_LOG_FILEPATH: {RGBMATRIX_DAEMON_LOG_FILEPATH}")
RGBMATRIX_DAEMON_FONTS_DIR = os.path.join(RGBMATRIX_DAEMON_DIR, "rgb_fonts")
print(f"RGBMATRIX_DAEMON_FONTS_DIR: {RGBMATRIX_DAEMON_FONTS_DIR}")

NB_MATRICES = 12
PANEL_WIDTH = 64
PANEL_HEIGHT = 32
Y_CENTERED = 20
Y_TOP = 10
Y_BOTTOM = 30
LED_SLOWDOWN_GPIO = 5
MAX_CHARS_FOR_WIDTH = 9
PIXELS_PER_CHAR = PANEL_WIDTH // MAX_CHARS_FOR_WIDTH
# by default, index 0 is the farthest matrix, not the closest.
REVERSE_CHAIN_ORDER = True


from rgbmatrix_samplebase import SampleBase
from rgbmatrix import graphics

from cube_rgbmatrix_server import CubeRgbMatrixContentDict, CubeRgbMatrixContent, CubeRgbServer


class MockLogger:
    def __init__(self, name):
        self.name = name
        self.enabled = True

    def debug(self, msg, *args, **kwargs):
        if self.enabled:
            print(f"DEBUG: {self.name} - {msg}")

    def info(self, msg, *args, **kwargs):
        if self.enabled:
            print(f"INFO: {self.name} - {msg}")

    def warning(self, msg, *args, **kwargs):
        if self.enabled:
            print(f"WARNING: {self.name} - {msg}")

    def error(self, msg, *args, **kwargs):
        if self.enabled:
            print(f"ERROR: {self.name} - {msg}")

    def critical(self, msg, *args, **kwargs):
        if self.enabled:
            print(f"CRITICAL: {self.name} - {msg}")


    def addHandler(self, handler):
        pass

    def setLevel(self, level):
        pass


class CubeRgbMatrixDaemon(SampleBase):
    # singleton instance for the subprocess
    _static_process = None
    _log_file = None
    enable_logging = False

    # Create a logger object
    log = MockLogger('RGBMatrixDaemon')
    log.enabled = False
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    @classmethod
    def enable_log_stdout(cls, enable=True):
        if enable:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(cls.formatter)
            cls.log.addHandler(console_handler)
            cls.log.enabled = True
        else:
            cls.log.enabled = False

    @classmethod
    def launch_process(cls) -> bool:
        try:
            if cls._static_process:
                cls.log.warning(f"{cls.__name__} : process already running")
                return False
            daemon_path = os.path.abspath(__file__)
            if cls.enable_logging:
                cls._log_file = open(RGBMATRIX_DAEMON_LOG_FILEPATH, 'w')
                cls._static_process = subprocess.Popen(
                    ['sudo', 'python3', daemon_path],
                    stdout=cls._log_file,
                    stderr=cls._log_file
                )
            else:
                cls._static_process = subprocess.Popen(
                    ['sudo', 'python3', daemon_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            cls.log.info(f"{cls.__name__} : process launched")
            return True
        except Exception as e:
            cls.log.error(f"{cls.__name__} : Error launching process: {e}")
            return False

    @classmethod
    def stop_process(cls, timeout=2):
        cls.log.info(f"{cls.__name__} : stopping process")
        try:
            if cls._static_process:
                cls._static_process.terminate()
                cls._static_process.wait(timeout=timeout)
                cls._static_process = None
            if cls._log_file:
                cls._log_file.close()
                cls._log_file = None
        except Exception as e:
            print(f"{cls.__name__} : Error stopping process: {e}")

    @classmethod
    def is_process_running(cls):
        return cls._static_process is not None

    def start(self):
        """Calls SampleBase.process(), which is the standard way of running the RGB matrices."""
        return self.process()

    @staticmethod
    def get_random_texts():
        import random
        time1 = random.randint(0, 8000)
        time2 = random.randint(0, 8000)
        remaining_times = [time1, time2]
        lines = []
        # convert to hh:mm:ss
        for time in remaining_times:
            lines.append(str(datetime.timedelta(seconds=time)))
        return lines

    def run(self):
        self.log.info("CubeRgbTextDrawer running")
        self._keep_running = True
        # NOTE: DO NOT copy the canvas in a CubeRgbText instance property.
        # it seems to create new canvas instances, and makes the message disappear
        canvas = self.matrix.CreateFrameCanvas()
        while self._keep_running:
            contents_dict = self.server.get_rgb_matrix_contents_dict()

            self.log.debug(f"CubeRgbTextDrawer contents: {contents_dict}")
            canvas.Clear()
            for matrix_id, content in contents_dict.items():
                if REVERSE_CHAIN_ORDER:
                    matrix_id = NB_MATRICES - matrix_id - 1
                self.log.debug(f"matrix_id: {matrix_id}, content: {content}, content.team_name: {content.team_name}, content.remaining_time_str: {content.remaining_time_str}")
                if not content.team_name:
                    time_text = content.remaining_time_str
                    time_width = len(time_text) * PIXELS_PER_CHAR
                    x_time = matrix_id * PANEL_WIDTH + (PANEL_WIDTH - time_width) // 2

                    graphics.DrawText(canvas, self.font, x_time, Y_CENTERED, self.textColor, time_text)
                else:
                    name_text = content.team_name[:MAX_CHARS_FOR_WIDTH]
                    name_width = len(name_text) * PIXELS_PER_CHAR
                    x_name = matrix_id * PANEL_WIDTH + (PANEL_WIDTH - name_width) // 2
                    graphics.DrawText(canvas, self.font, x_name, Y_TOP, self.textColor, name_text)

                    time_text = content.remaining_time_str
                    time_width = len(time_text) * PIXELS_PER_CHAR
                    x_time = matrix_id * PANEL_WIDTH + (PANEL_WIDTH - time_width) // 2
                    graphics.DrawText(canvas, self.font, x_time, Y_BOTTOM, self.textColor, time_text)
            time.sleep(1)
            canvas = self.matrix.SwapOnVSync(canvas)
        self.clear_matrices()
        self.log.info("CubeRgbTextDrawer stopped")

    def clear_matrices(self):
        try:
            self.log.info("Clearing matrices")
            canvas = self.matrix.CreateFrameCanvas()
            canvas.Clear()
            canvas = self.matrix.SwapOnVSync(canvas)
        except Exception as e:
            self.log.error(f"Error clearing matrices: {e}")






    def stop(self):
        self.log.info("CubeRgbTextDrawer stopping")
        self._keep_running = False
        self.clear_matrices()
        time.sleep(0.2)
        self.log.info("CubeRgbTextDrawer stopped")


class CubeRgbMatrixMockDaemon(CubeRgbMatrixDaemon):
    """Has the same interface as the CubeRgbMatrixDaemon, but displays text
    instead of using the RGB matrix."""

    # noinspection PyMissingConstructor
    def __init__(self):
        self._keep_running = False
        self.server = CubeRgbServer(is_rgb=True, debug=True)
        self.create_log_file()

    @classmethod
    def launch_process(cls) -> bool:
        """same as the original, but without sudo"""
        if cls._static_process:
            cls.log.warning(f"{cls.__name__} :  process already running")
            return False
        daemon_path = os.path.abspath(__file__)
        cls._static_process = subprocess.Popen(['python3', daemon_path])
        cls.log.info(f"{cls.__name__} :  process launched")
        return True

    @classmethod
    def stop_process(cls, timeout=2):
        """same as the original, but without sudo"""
        cls.log.info(f"{cls.__name__} : stopping process")
        try:
            if cls._static_process:
                cls._static_process.terminate()
                cls._static_process.wait(timeout=timeout)
        except Exception as e:
            print(f"{cls.__name__} : Error stopping process: {e}")

    def start(self):
        return self.run()

    def run(self):
        self.log.info("CubeRgbTextDrawer running")
        self._keep_running = True
        while self._keep_running:
            contents_dict = self.server.get_rgb_matrix_contents_dict()
            self.log.debug(f"CubeRgbTextDrawer contents: {contents_dict}")
            for matrix_id, content in contents_dict.items():
                if content.team_name is None:
                    text = content.remaining_time_str
                else:
                    text = content.team_name + " " + content.remaining_time_str
                print(f"matrix_id: {matrix_id}, text: {text}")
            time.sleep(1)
            print("-----------------------")
        print("CubeRgbTextDrawer stopped")




def is_raspberry_pi():
    try:
        with open('/proc/device-tree/model') as f:
            model = f.read().lower()
        return 'raspberry pi' in model
    except Exception:
        return False


def test():
    if is_raspberry_pi():
        print("Using the real CubeRgbMatrixDaemon")
        daemon = CubeRgbMatrixDaemon()
    else:
        print("Using the mock CubeRgbMatrixDaemon")
        daemon = CubeRgbMatrixMockDaemon()
    daemon.server._rgb_matrix_contents_dict = CubeRgbMatrixContentDict({
        0: CubeRgbMatrixContent(matrix_id=0, team_name="Team 1", end_timestamp=time.time() + 3),
        1: CubeRgbMatrixContent(matrix_id=1, team_name="Team 2", end_timestamp=time.time() + 10),
    })
    daemon.log.setLevel(logging.DEBUG)
    daemon.server._debug = True
    daemon.enable_log_stdout()
    daemon.log.critical("---- Starting RGB Daemon TEST ----")
    print("Starting RGB Daemon TEST")

    team_names = [
        "Oslo",
        "Stockholm",
        "Dakar",
        "Berne",
        "Budapest",
        "Kiev",
        "Naples",
        "Belgrade",
        "Moscou",
        "Madrid",
        "Paris",
        "Ankara",
    ]

    nb_teams = len(team_names)

    # random timestamps posterior to time.time()
    end_timestamps = [
        time.time() + random.randint(0, 8000) for _ in range(nb_teams)
    ]

    try:
        thread = threading.Thread(target=daemon.start, daemon=True)
        thread.start()

        print("Running RGB Daemon test")
        d_names = CubeRgbMatrixContentDict({
            i:CubeRgbMatrixContent(matrix_id=i,
                                   team_name=team_names[i],
                                   end_timestamp=end_timestamps[i]) for i in range(nb_teams)
        })
        text_with_names = d_names.to_string()
        d_no_names = CubeRgbMatrixContentDict({
            i:CubeRgbMatrixContent(matrix_id=i,
                                      team_name="",
                                      end_timestamp=end_timestamps[i]) for i in range(nb_teams)
        })
        text_no_names = d_no_names.to_string()
        while True:
            daemon.server._handle_received_text(text_with_names)
            time.sleep(2)
            daemon.server._handle_received_text(text_no_names)
            time.sleep(2)

    except Exception as e:
        print(f"RGB Daemon : Exception : {e}")
        exit(1)
    finally:
        daemon.stop()
        exit(0)

def main():
    print("Starting RGB Daemon")
    if is_raspberry_pi():
        print("Using the real CubeRgbMatrixDaemon")
        daemon = CubeRgbMatrixDaemon()
    else:
        print("Using the mock CubeRgbMatrixDaemon")
        daemon = CubeRgbMatrixMockDaemon()

    try:
        assert daemon.start()
        while True:
            time.sleep(0.1)
    except Exception as e:
        print(f"RGB Daemon : Exception : {e}")
        exit(1)
    finally:
        daemon.stop()
        exit(0)

if __name__ == "__main__":
    import sys

    # always test if not on raspberry pi
    do_test = not is_raspberry_pi()

    if "--test" in sys.argv or do_test:
        if "--test" in sys.argv:
            print("Removing --test from sys.argv")
            # remove "--test" from sys.argv to avoid problems for the SampleBase.
            # if we leave it, it will try to parse it as an argument and raise an error.
            sys.argv.remove("--test")
        test()
    else:
        main()
