# TODO: handle the fact that the logs folder doesnt have the same relative path for everyone, like the GUI

import logging
from colorlog import ColoredFormatter
from os import path, makedirs

LOGS_DIR = "logs"
COMMON_LOG_FILENAME = path.join(LOGS_DIR, "cube_common.log")
CUBEMASTER_LOG_FILENAME = path.join(LOGS_DIR, "cubemaster.log")
CUBEBOX_LOG_FILENAME =  path.join(LOGS_DIR, "cubebox.log")
CUBEFRONTDESK_LOG_FILENAME = path.join(LOGS_DIR, "cubefrontdesk.log")
CUBEGUI_LOG_FILENAME = path.join(LOGS_DIR, "cubegui.log")

SUCCESS_LEVEL = logging.INFO - 1
SUCCESS_LEVEL_NAME = "SUCCESS"

logging.addLevelName(SUCCESS_LEVEL, SUCCESS_LEVEL_NAME)

class CubeLogger(logging.Logger):
    def __init__(self, name:str, log_filename:str=None):
        super().__init__(name)
        self.setLevel(logging.DEBUG)
        # handler for stdout logging
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.DEBUG)

        # if the logs directory does not exist, create it
        if not path.exists(LOGS_DIR):
            makedirs(LOGS_DIR)
        # handler for common file logging : all instances of logger will log to this file
        common_file_handler = logging.FileHandler(COMMON_LOG_FILENAME)
        common_file_handler.setLevel(logging.DEBUG)

        # Create a formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        color_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'green',
                'INFO': 'blue',
                'WARNING': 'purple',
                'ERROR': 'red',
                'CRITICAL': 'bold_yellow',
                'SUCCESS': 'yellow'
            },
            secondary_log_colors={},
            style='%'
        )

        stdout_handler.setFormatter(color_formatter)
        common_file_handler.setFormatter(formatter)

        self.addHandler(stdout_handler)
        self.addHandler(common_file_handler)

        # if a log_filename is provided, add an additional, specific file handler for this logger
        # used in order to have a log file specific to the CubeMaster, the CubeBox, the CubeGui, etc.
        if log_filename:
            file_handler = logging.FileHandler(log_filename)
            file_handler.setLevel(logging.DEBUG)
            self.addHandler(file_handler)
            file_handler.setFormatter(formatter)
            self.addHandler(file_handler)


    def success(self, msg, *args, **kwargs):
        if self.isEnabledFor(SUCCESS_LEVEL):
            self._log(SUCCESS_LEVEL, msg, args, **kwargs)

def make_logger(name:str, log_filename:str=None) -> logging.Logger:
    # Instantiate a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # handler for stdout logging
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.DEBUG)

    # if the logs directory does not exist, create it
    if not path.exists(LOGS_DIR):
        makedirs(LOGS_DIR)
    # handler for common file logging : all instances of logger will log to this file
    common_file_handler = logging.FileHandler(COMMON_LOG_FILENAME)
    common_file_handler.setLevel(logging.DEBUG)

    # Create a formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    color_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'green',
            'INFO': 'blue',
            'WARNING': 'purple',
            'ERROR': 'red',
            'CRITICAL': 'bold_yellow',
            'SUCCESS': 'yellow'
        },
        secondary_log_colors={},
        style='%'
    )

    stdout_handler.setFormatter(color_formatter)
    common_file_handler.setFormatter(formatter)

    logger.addHandler(stdout_handler)
    logger.addHandler(common_file_handler)

    # if a log_filename is provided, add an additional, specific file handler for this logger
    # used in order to have a log file specific to the CubeMaster, the CubeBox, the CubeGui, etc.
    if log_filename:
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

if __name__ == "__main__":
    # test the logger
    # log = make_logger("test")
    log = CubeLogger("test")
    log.debug("This is a debug message")
    log.info("This is an info message")
    log.success("This is a success message")
    log.warning("This is a warning message")
    log.error("This is an error message")
    log.critical("This is a critical message")