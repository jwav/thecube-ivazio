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
            'CRITICAL': 'red,bg_white',
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