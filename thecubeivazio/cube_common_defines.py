import os
import traceback
from pathlib import Path
from typing import Union
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

# constants

# the project root path
PROJECT_ROOT_PATH = Path(__file__).parent.resolve()
SOUNDS_DIR = os.path.join(PROJECT_ROOT_PATH, "sounds")
LOGS_DIR = os.path.join(PROJECT_ROOT_PATH, "logs")
CUBEGUI_DIR = os.path.join(PROJECT_ROOT_PATH, "cubegui")
CONFIG_DIR = os.path.join(PROJECT_ROOT_PATH, "config")
IMAGES_DIR = os.path.join(CUBEGUI_DIR, "images")
SAVES_DIR = os.path.join(PROJECT_ROOT_PATH, "saves")
SCORESHEETS_DIR = os.path.join(PROJECT_ROOT_PATH, "scoresheets")

GLOBAL_CONFIG_FILEPATH = os.path.join(CONFIG_DIR, "global_config.json")
LOCAL_CONFIG_FILEPATH = os.path.join(CONFIG_DIR, "local_config.json")
DEFAULT_TROPHY_IMAGE_FILENAME = "default_trophy_image.png"
DEFAULT_TROPHY_IMAGE_FILEPATH = os.path.join(IMAGES_DIR, DEFAULT_TROPHY_IMAGE_FILENAME)
CUBEBOXES_BACKUP_FILEPATH = os.path.join(SAVES_DIR, "cubeboxes_backup.json")
TEAMS_BACKUP_FILEPATH = os.path.join(SAVES_DIR, "teams_backup.json")
TEAMS_DATABASE_FILEPATH = os.path.join(SAVES_DIR, "teams_database.json")
RESETTER_RFID_LIST_FILEPATH = os.path.join(SAVES_DIR, "rfid_reset_list.json")

# used in looping functions to induce a little delay
# TODO: implement in existing loops
LOOP_PERIOD_SEC = 0.1
STATUS_REPLY_TIMEOUT = 5


def cubetry(func):
    """Decorator to catch exceptions in functions and log them without having to write a try/except block in the function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # print full traceback
            CubeLogger.static_error(f"{func.__name__} : {e}\n{traceback.format_exc()}")
            if func.__annotations__.get('return') == bool:
                return False
            elif func.__annotations__.get('return') == str:
                return ""
            return None
    return wrapper

def test_paths():
    all_paths = [PROJECT_ROOT_PATH, SOUNDS_DIR, LOGS_DIR, CUBEGUI_DIR, CONFIG_DIR, GLOBAL_CONFIG_FILEPATH,
                 LOCAL_CONFIG_FILEPATH, SCORESHEETS_DIR, IMAGES_DIR, DEFAULT_TROPHY_IMAGE_FILEPATH,
                 CUBEBOXES_BACKUP_FILEPATH, TEAMS_DATABASE_FILEPATH]
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
        # noinspection PyTypeChecker
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


