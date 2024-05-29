import json
import logging
from typing import Tuple, Optional

from thecubeivazio import cube_logger
from thecubeivazio.cube_common_defines import *
import thecubeivazio.cube_utils as cube_utils
from thecubeivazio.cube_game import CubeTrophy

# todo: to_json
# todo: remove local config. only one config file, the local is not needed
class CubeConfig:
    """Class to hold configuration values."""
    # singleton instance of CubeConfig
    _instance = None

    def __init__(self):
        self.log = cube_logger.CubeLogger(name="CubeConfig")
        self.log.setLevel(logging.INFO)
        self.config_dict = {}
        self._trophies = []

        self.clear()
        self.load_global_config()
        self.load_local_config()
        if self.is_valid():
            self.log.info("CubeConfig fully loaded and valid")
        else:
            self.log.error("CubeConfig not fully loaded or invalid")

    @staticmethod
    def get_config():
        if CubeConfig._instance is None:
            CubeConfig._instance = CubeConfig()
        return CubeConfig._instance

    def is_valid(self):
        try:
            assert self.config_dict, "config_dict is empty"
            assert self.game_durations_str, "game_durations_str is empty"
            assert self.game_durations_sec, "game_durations_sec is empty"
            assert self.team_names, "team_names is empty"
            assert self.local_node_name, "local_node_name is empty"
            assert self.trophies, "trophies is empty"
            assert self.valid_node_names, "valid_node_names is empty"
            assert self.local_node_name in self.valid_node_names, "local_node_name not in valid_node_names"
            return True
        except Exception as e:
            self.log.error(f"Error checking if CubeConfig is valid: {e}")
            return False

    def to_string(self):
        return self.__str__()

    def __str__(self):
        return f"CubeConfig(config_dict={self.config_dict})"

    def __repr__(self):
        return self.__str__()

    def clear(self):
        self.config_dict = {}
        self._trophies = []

    def load_global_config(self):
        self.log.info(f"Loading global configuration from file : '{GLOBAL_CONFIG_FILEPATH}'")
        try:
            with open(GLOBAL_CONFIG_FILEPATH, "r") as f:
                self.config_dict = json.load(f)
        except FileNotFoundError:
            self.log.error(f"Configuration file not found: '{GLOBAL_CONFIG_FILEPATH}'")
            self.config_dict = {}
        except json.JSONDecodeError:
            self.log.error(f"Error decoding JSON configuration file: '{GLOBAL_CONFIG_FILEPATH}'")
            self.config_dict = {}
        self.log.info(f"Global configuration loaded")

    def load_local_config(self):
        self.log.info(f"Loading local configuration from file : '{LOCAL_CONFIG_FILEPATH}'")
        try:
            with open(LOCAL_CONFIG_FILEPATH, "r") as f:
                local_config = json.load(f)
                self.config_dict.update(local_config)
        except FileNotFoundError:
            self.log.error(f"Configuration file not found: '{LOCAL_CONFIG_FILEPATH}'")
            self.config_dict = {}
        except json.JSONDecodeError as e:
            self.log.error(f"Error decoding JSON configuration file: '{LOCAL_CONFIG_FILEPATH}'")
            self.log.error(f"{e}")
            self.config_dict = {}
        self.log.info(f"Local configuration loaded")


    @property
    def game_durations_str(self) -> Optional[Tuple[str]]:
        try:
            # noinspection PyTypeChecker
            return tuple(str(x) for x in self.config_dict.get("game_durations", []))
        except Exception as e:
            self.log.error(f"Error getting game_durations_str: {e}")
            return None

    @property
    def game_durations_sec(self) -> Optional[Tuple[Seconds]]:
        try:
            # noinspection PyTypeChecker
            return tuple(cube_utils.hhmmss_string_to_seconds(duration_str) for duration_str in self.game_durations_str)
        except Exception as e:
            self.log.error(f"Error getting game_durations_sec: {e}")
            return None

    @property
    def team_names(self):
        return self.config_dict.get("team_names", {})

    @property
    def local_node_name(self):
        return self.config_dict.get("local_node_name", None)

    @property
    def valid_node_names(self):
        return self.config_dict.get("valid_node_names", [])

    @property
    def trophies(self) -> list[CubeTrophy]:
        return [CubeTrophy(**trophy) for trophy in self.config_dict.get("trophies", [])]

if __name__ == "__main__":
    config = CubeConfig()
    config.log.info("-----------------")
    config.log.info(f"config valid?: {config.is_valid()}")
    config.log.info(f"game_durations: {config.game_durations_str}")
    config.log.info(f"game_durations: {config.game_durations_sec}")
    config.log.info(f"team_names: {config.team_names}")
    config.log.info(f"local_node_name: {config.local_node_name}")
    config.log.info(f"trophies: {config.trophies}")


