import time

from thecubeivazio import cube_utils
from thecubeivazio.cube_rgbmatrix_daemon.cube_rgbmatrix_daemon import *

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

def simple_read_write_test():
    test_file_path = RGBMATRIX_DAEMON_TEXT_FILEPATH
    print(f"Test file path: {test_file_path}")
    # Write to the test file
    try:
        with open(test_file_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write("Test content\n")
            fcntl.flock(f, fcntl.LOCK_UN)
        print("Write successful")
    except Exception as e:
        print(f"Error writing to test file: {e}")

    # Read from the test file
    try:
        with open(test_file_path, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            content = f.read()
            fcntl.flock(f, fcntl.LOCK_UN)
        print("Read successful")
        print("Content:", content)
    except Exception as e:
        print(f"Error reading from test file: {e}")

if __name__ == "__main__":
    simple_read_write_test()
    # exit(0)
    # if the argument --mock is passed, use the mock class
    import sys
    print(f"sys.argv: {sys.argv}")
    if "--mock" in sys.argv:
        CubeRgbMatrixDaemon = MockCubeRgbMatrixDaemon
    else:
        CubeRgbMatrixDaemon = CubeRgbMatrixDaemon

    # if --path, just print the path
    if "--path" in sys.argv:
        print(f"RGBMATRIX_DAEMON_TEXT_FILEPATH: {RGBMATRIX_DAEMON_TEXT_FILEPATH}")
        exit(0)
    print(f"RGBMATRIX_DAEMON_TEXT_FILEPATH: {RGBMATRIX_DAEMON_TEXT_FILEPATH}")

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