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

if __name__ == "__main__":
    # if the argument --mock is passed, use the mock class
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        CubeRgbMatrixDaemon = MockCubeRgbMatrixDaemon
    else:
        CubeRgbMatrixDaemon = CubeRgbMatrixDaemon
    start_time = time.time()
    CubeRgbMatrixDaemon.launch_process()

    try:
        while True:
            time.sleep(1)
            print("time elapsed:", time.time() - start_time)
            secs1 = int(time.time() - start_time)
            secs2 = int(time.time() - start_time) + 5
            lines = [cube_utils.seconds_to_hhmmss_string(x, separators="::") for x in [secs1, secs2]]
            if CubeRgbMatrixDaemon.write_lines_to_daemon_file(lines):
                print("lines written: ", lines)
            else:
                print("error writing lines")
            lines_read = CubeRgbMatrixDaemon.read_lines_from_daemon_file()
            print("lines read:", lines_read)

    except Exception as e:
        print(f"Error launching process: {e}")
    finally:
        CubeRgbMatrixDaemon.stop_process()
        print("process stopped")
        exit(0)