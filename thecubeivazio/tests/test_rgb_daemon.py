import time

from thecubeivazio import cube_utils
from thecubeivazio.cube_rgbmatrix_daemon.cube_rgbmatrix_daemon import CubeRgbMatrixDaemon

class MockCubeRgbMatrixDaemon:
    @staticmethod
    def launch_process():
        print("launching process")

    @staticmethod
    def write_lines_to_daemon_file(lines):
        print("writing lines to daemon file : ", lines)

    @staticmethod
    def stop_process():
        print("stopping process")
try:
    # CubeRgbMatrixDaemon = MockCubeRgbMatrixDaemon
    CubeRgbMatrixDaemon.launch_process()
    start_time = time.time()
    while True:
        time.sleep(1)
        print("time elapsed:", time.time() - start_time)
        secs1 = int(time.time() - start_time)
        secs2 = int(time.time() - start_time) + 5
        lines = [cube_utils.seconds_to_hhmmss_string(x) for x in [secs1, secs2]]
        CubeRgbMatrixDaemon.write_lines_to_daemon_file(lines)

except Exception as e:
    print(f"Error launching process: {e}")
finally:
    CubeRgbMatrixDaemon.stop_process()
    print("process stopped")