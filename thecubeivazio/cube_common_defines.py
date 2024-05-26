import os
from pathlib import Path
from typing import Union

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
GLOBAL_CONFIG_FILEPATH = os.path.join(CONFIG_DIR, "global_config.json")
LOCAL_CONFIG_FILEPATH = os.path.join(CONFIG_DIR, "local_config.json")
SCORESHEETS_DIR = os.path.join(PROJECT_ROOT_PATH, "scoresheets")
IMAGES_DIR = os.path.join(CUBEGUI_DIR, "images")
DEFAULT_TROPHY_IMAGE_FILENAME = "default_trophy_image.png"
DEFAULT_TROPHY_IMAGE_FILEPATH = os.path.join(IMAGES_DIR, DEFAULT_TROPHY_IMAGE_FILENAME)

# used in looping functions to induce a little delay
# TODO: implement in existing loops
LOOP_PERIOD_SEC = 0.1

if __name__ == "__main__":
    all_paths = [PROJECT_ROOT_PATH, SOUNDS_DIR, LOGS_DIR, CUBEGUI_DIR, CONFIG_DIR, GLOBAL_CONFIG_FILEPATH,
                 LOCAL_CONFIG_FILEPATH, SCORESHEETS_DIR]
    for path in all_paths:
        print(f"path: {path}")
        try:
            assert os.path.exists(path)
        except AssertionError as e:
            print(f"Error: {e}")
        else:
            print(f"exists: {path}")
