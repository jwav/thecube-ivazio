import glob
import inspect
import os
import traceback
from pathlib import Path
from typing import Union, Optional
from functools import wraps
from thecubeivazio.cube_logger import CubeLogger


# type aliases
Seconds = Union[float, int]
Timestamp = Seconds
CubeId = int
TeamName = str
NodeName = str
Hash = str
HashDict = dict[str, Hash]
ScoringPresetName = str

# constants

# used to unlock admin actions and decrypt encrypted files
ADMIN_PASSWORD_SHA256 = "ea6c4c5edc6493edd233ed2e51fcc1f9002b654e04b88806b5439f00fadcff2b"

POSSIBLE_PROJECT_ROOT_PATH_PATTERNS = [
    "/mnt/shared/thecube-ivazio/thecubeivazio",
    "/home/*/thecube-ivazio/thecubeivazio",
    "D:\\thecube-ivazio\\thecubeivazio"
]

def find_first_matching_path() -> Optional[str]:
    for pattern in POSSIBLE_PROJECT_ROOT_PATH_PATTERNS:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


# poses problems depending on the environment
# PROJECT_ROOT_PATH = Path(__file__).parent.resolve()
PROJECT_ROOT_PATH = find_first_matching_path()

try:
    assert PROJECT_ROOT_PATH and Path(PROJECT_ROOT_PATH).exists(), "PROJECT_ROOT_PATH not found"
    print(f"PROJECT_ROOT_PATH: '{PROJECT_ROOT_PATH}'")
except AssertionError as e:
    print(e)
    print("PROJECT_ROOT_PATH not found. Exiting.")
    exit(1)

SOUNDS_DIR = os.path.join(PROJECT_ROOT_PATH, "sounds")
LOGS_DIR = os.path.join(PROJECT_ROOT_PATH, "logs")
CUBEGUI_DIR = os.path.join(PROJECT_ROOT_PATH, "cubegui")
CONFIG_DIR = os.path.join(PROJECT_ROOT_PATH, "config")
IMAGES_DIR = os.path.join(CUBEGUI_DIR, "images")
SAVES_DIR = os.path.join(PROJECT_ROOT_PATH, "saves")
SCORESHEETS_DIR = os.path.join(PROJECT_ROOT_PATH, "scoresheets")
HIGHSCORES_DIR = os.path.join(PROJECT_ROOT_PATH, "scores_screen")
RGB_FONTS_DIR = os.path.join(PROJECT_ROOT_PATH, "rgb_fonts")
RGB_SERVER_DIR = os.path.join(PROJECT_ROOT_PATH, "cube_rgbmatrix_daemon")
# from thecubeivazio.cube_rgbmatrix_daemon.cube_rgbmatrix_daemon import RGBMATRIX_DAEMON_TEXT_FILENAME
# RGB_SERVER_TEXT = os.path.join(RGB_SERVER_DIR, RGBMATRIX_DAEMON_TEXT_FILENAME)

CONFIG_FILEPATH = os.path.join(CONFIG_DIR, "global_config.json")
ENCRYPTED_CONFIG_FILEPATH = os.path.join(CONFIG_DIR, "global_config.json.enc")
DEFAULT_TROPHY_IMAGE_FILENAME = "default_trophy_image.png"
DEFAULT_TROPHY_IMAGE_FILEPATH = os.path.join(IMAGES_DIR, DEFAULT_TROPHY_IMAGE_FILENAME)
CUBEBOXES_BACKUP_FILEPATH = os.path.join(SAVES_DIR, "cubeboxes_backup.json")
TEAMS_BACKUP_FILEPATH = os.path.join(SAVES_DIR, "teams_backup.json")
TEAMS_JSON_DATABASE_FILEPATH = os.path.join(SAVES_DIR, "teams_database.json")
TEAMS_SQLITE_DATABASE_FILEPATH = os.path.join(SAVES_DIR, "teams_database.db")
RESETTER_RFID_LIST_FILEPATH = os.path.join(CONFIG_DIR, "resetter_rfids_list.json")

# used in looping functions to induce a little delay
# TODO: implement in existing loops
LOOP_PERIOD_SEC = 0.1
STATUS_REPLY_TIMEOUT = 2
TIMESTAMP_EPSILON = 0.00001

def cubetry(func):
    """Decorator to catch exceptions in functions and log them without having to write a try/except block in the function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get the signature and the parameters of the function
            sig = inspect.signature(func)
            parameters = sig.parameters

            # Only pass the required arguments to the function
            func_args = args[:len(parameters)]
            func_kwargs = {k: v for k, v in kwargs.items() if k in parameters}

            return func(*func_args, **func_kwargs)
        except Exception as e:
            # Get the full traceback of the error
            full_traceback = traceback.format_exc()

            # Get the full call stack
            call_stack = inspect.stack()
            formatted_call_stack = "\n".join([
                f"File \"{frame.filename}\", line {frame.lineno}, in {frame.function}"
                for frame in call_stack
            ])

            # Format the log message
            log_message = (
                f"Exception in {func.__name__}:\n"
                f"Call Stack:\n{formatted_call_stack}\n"
                f"Error: {e}\n"
                f"{full_traceback}"
            )

            # Log the error with additional context
            CubeLogger.static_error(log_message)

            # Return appropriate default values based on function annotations
            if func.__annotations__.get('return') == bool:
                return False
            elif func.__annotations__.get('return') == str:
                return ""
            return None
    return wrapper



def test_paths():
    all_paths = [PROJECT_ROOT_PATH, SOUNDS_DIR, LOGS_DIR, CUBEGUI_DIR, CONFIG_DIR, CONFIG_FILEPATH,
                 SCORESHEETS_DIR, IMAGES_DIR, DEFAULT_TROPHY_IMAGE_FILEPATH,
                 CUBEBOXES_BACKUP_FILEPATH, TEAMS_JSON_DATABASE_FILEPATH]
    for path in all_paths:
        try:
            assert os.path.exists(path)
            print(f"path ok: {path}")
        except AssertionError as e:
            print(f"path error: {path}")
            print(e)

def test_cubetry():
    @cubetry
    def test_func1():
        raise Exception("test exception")
    @cubetry
    def test_func2():
        return 1/0
    @cubetry
    def test_func3() -> bool:
        # noinspection PyTypeChecker, PyUnusedLocal
        x = 1 + "1"
        return True
    @cubetry
    def test_func4() -> int:
        assert 1 == 0, "asserted that 1 == 0"
        # noinspection PyUnreachableCode
        return 42

    test_func1()
    test_func2()
    test_func3()
    test_func4()

def test_all():
    test_paths()
    test_cubetry()

def handle_sys_args() -> bool:
    # use sys args to test the functions : if an argument starts with --test,
    # check if it matches the name of a "test_*" function. if it does, call it.
    # else, return False
    import sys
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--test"):
                test_name = arg[2:]
                try:
                    globals()[test_name]()
                    return True
                except KeyError:
                    print(f"Test function {test_name} not found.")
                    return False
    return False

if __name__ == "__main__":
    if not handle_sys_args():
        print("sys args not handled")
        # test_paths()
        test_cubetry()


