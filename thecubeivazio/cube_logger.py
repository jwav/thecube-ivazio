# TODO: handle the fact that the logs folder doesnt have the same relative path for everyone, like the GUI

import logging
import threading
from logging.handlers import RotatingFileHandler

from colorlog import ColoredFormatter
from os import path, makedirs

LOGS_DIR = "logs"
COMMON_LOG_FILENAME = path.join(LOGS_DIR, "cube_common.log")
CUBEMASTER_LOG_FILENAME = path.join(LOGS_DIR, "cubemaster.log")
CUBEBOX_LOG_FILENAME = path.join(LOGS_DIR, "cubebox.log")
CUBEFRONTDESK_LOG_FILENAME = path.join(LOGS_DIR, "cubefrontdesk.log")
CUBEGUI_LOG_FILENAME = path.join(LOGS_DIR, "cubegui.log")

LEVEL_SUCCESS = logging.INFO - 1
LEVELNAME_SUCCESS = "SUCCESS"
LEVEL_INFOPLUS = logging.INFO + 1
LEVELNAME_INFOPLUS = "INFOPLUS"
LEVEL_DEBUGPLUS = logging.DEBUG + 1
LEVELNAME_DEBUGPLUS = "DEBUGPLUS"

logging.addLevelName(LEVEL_SUCCESS, LEVELNAME_SUCCESS)
logging.addLevelName(LEVEL_INFOPLUS, LEVELNAME_INFOPLUS)
logging.addLevelName(LEVEL_DEBUGPLUS, LEVELNAME_DEBUGPLUS)


class CubeLogger(logging.Logger):
    # singleton instance for classes for whom instanciating a dedicated logger is not justified
    # (ex: classes that are often created and destroyed)
    _static_logger: 'CubeLogger' = None
    # convenient aliases
    LEVEL_SUCCESS = LEVEL_SUCCESS
    LEVEL_INFOPLUS = LEVEL_INFOPLUS
    LEVEL_DEBUGPLUS = LEVEL_DEBUGPLUS
    LEVEL_INFO = logging.INFO
    LEVEL_DEBUG = logging.DEBUG
    LEVEL_WARNING = logging.WARNING
    LEVEL_ERROR = logging.ERROR
    LEVEL_CRITICAL = logging.CRITICAL

    @classmethod
    def set_static_level(cls, level: int):
        cls.get_static_logger().setLevel(level)

    @classmethod
    def get_static_logger(cls) -> 'CubeLogger':
        if cls._static_logger is None:
            cls._static_logger = cls("CubeDefaultLogger", COMMON_LOG_FILENAME)
            cls._static_logger.setLevel(logging.DEBUG)
        return cls._static_logger

    @classmethod
    def static_info(cls, msg, *args, **kwargs):
        cls.get_static_logger().info(msg, *args, **kwargs)

    @classmethod
    def static_debug(cls, msg, *args, **kwargs):
        cls.get_static_logger().debug(msg, *args, **kwargs)

    @classmethod
    def static_error(cls, msg, *args, **kwargs):
        cls.get_static_logger().error(msg, *args, **kwargs)

    @classmethod
    def static_warning(cls, msg, *args, **kwargs):
        cls.get_static_logger().warning(msg, *args, **kwargs)

    @classmethod
    def static_debugplus(cls, msg, *args, **kwargs):
        cls.get_static_logger().debugplus(msg, *args, **kwargs)

    def __init__(self, name: str, log_filename: str = None):
        super().__init__(name)
        self.setLevel(logging.DEBUG)
        # handler for stdout logging
        self.stdout_handler = logging.StreamHandler()
        self.stdout_handler.setLevel(logging.DEBUG)

        # if the logs directory does not exist, create it
        if not path.exists(LOGS_DIR):
            makedirs(LOGS_DIR)
        # handler for common file logging : all instances of logger will log to this file
        # self.common_file_handler = logging.FileHandler(COMMON_LOG_FILENAME)
        self.common_file_handler = RotatingFileHandler(COMMON_LOG_FILENAME, maxBytes=5 * 1024 * 1024, backupCount=100)
        self.common_file_handler.setLevel(logging.DEBUG)

        # Create a formatter and add it to the handlers
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.color_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'green',
                'INFO': 'blue',
                'WARNING': 'purple',
                'ERROR': 'red',
                'CRITICAL': 'bold_yellow',
                LEVELNAME_SUCCESS: 'bold_cyan',
                LEVELNAME_INFOPLUS: 'bold_blue',
                LEVELNAME_DEBUGPLUS: 'green'
            },
            secondary_log_colors={},
            style='%'
        )

        self.stdout_handler.setFormatter(self.color_formatter)
        self.common_file_handler.setFormatter(self.formatter)

        self.addHandler(self.stdout_handler)
        self.addHandler(self.common_file_handler)

        # if a log_filename is provided, add an additional, specific file handler for this logger
        # used in order to have a log file specific to the CubeMaster, the CubeBox, the CubeGui, etc.
        if log_filename:
            file_handler = logging.FileHandler(log_filename)
            file_handler.setLevel(logging.DEBUG)
            self.addHandler(file_handler)
            file_handler.setFormatter(self.formatter)
            self.addHandler(file_handler)

    def success(self, msg, *args, **kwargs):
        if self.isEnabledFor(LEVEL_SUCCESS):
            self._log(LEVEL_SUCCESS, msg, args, **kwargs)

    def infoplus(self, msg, *args, **kwargs):
        if self.isEnabledFor(LEVEL_INFOPLUS):
            self._log(LEVEL_INFOPLUS, msg, args, **kwargs)

    def debugplus(self, msg, *args, **kwargs):
        if self.isEnabledFor(LEVEL_DEBUGPLUS):
            self._log(LEVEL_DEBUGPLUS, msg, args, **kwargs)


if __name__ == "__main__":
    # test the logger
    # log = make_logger("test")
    log = CubeLogger("Test")
    log.debug("This is a debug message")
    log.info("This is an info message")
    log.warning("This is a warning message")
    log.error("This is an error message")
    log.critical("This is a critical message")
    log.success("This is a success message")
    log.infoplus("This is an infoplus message")
    log.debugplus("This is a debugplus message")
    # test common instance
    common_log = CubeLogger.get_static_logger()
    common_log.debug("This is a common instance debug message")
    common_log.info("This is a common instance info message")
    common_log.warning("This is a common instance warning message")
    common_log.error("This is a common instance error message")
    common_log.critical("This is a common instance critical message")
    common_log.success("This is a common instance success message")
    common_log.infoplus("This is a common instance infoplus message")
    common_log.debugplus("This is a common instance debugplus message")
    # test static log methods
    CubeLogger.static_debug("This is a static debug message")
    CubeLogger.static_info("This is a static info message")
    CubeLogger.static_error("This is a static error message")
