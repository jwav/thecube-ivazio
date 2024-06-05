import json
import logging
from typing import Tuple, Optional

from thecubeivazio import cube_logger
from thecubeivazio.cube_common_defines import *
import thecubeivazio.cube_utils as cube_utils

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

        if self.is_valid():
            self.log.info("CubeConfig fully loaded and valid")
        else:
            self.log.error("CubeConfig not fully loaded or invalid")

    @staticmethod
    def get_config():
        if CubeConfig._instance is None:
            CubeConfig._instance = CubeConfig()
        return CubeConfig._instance

    @cubetry
    def is_valid(self) -> bool:
        assert self.config_dict, "config_dict is empty"
        assert self.game_durations_str, "game_durations_str is empty"
        assert self.game_durations_sec, "game_durations_sec is empty"
        assert self.team_names, "team_names is empty"
        assert self.all_trophies, "trophies is empty"
        assert self.valid_node_names, "valid_node_names is empty"
        return True

    @cubetry
    def to_json(self) -> str:
        return json.dumps(self.config_dict)

    @cubetry
    def save_to_json(self, filepath: str=None) -> bool:
        if filepath is None:
            filepath = GLOBAL_CONFIG_FILEPATH
        with open(filepath, "w") as f:
            f.write(self.to_json())
            return True

    def to_string(self) -> str:
        return self.to_json()

    def __str__(self):
        return self.to_json()

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
    def all_trophies(self) -> list['CubeTrophy']:
        try:
            from thecubeivazio.cube_game import CubeTrophy
            return [CubeTrophy(**trophy) for trophy in self.config_dict.get("trophies", [])]
        except Exception as e:
            self.log.error(f"Error getting trophies: {e}")
            return []

if __name__ == "__main__":
    config = CubeConfig()
    config.log.info("-----------------")
    config.log.info(f"config valid?: {config.is_valid()}")
    config.log.info(f"game_durations: {config.game_durations_str}")
    config.log.info(f"game_durations: {config.game_durations_sec}")
    config.log.info(f"team_names: {config.team_names}")
    config.log.info(f"local_node_name: {config.local_node_name}")
    config.log.info(f"trophies: {config.all_trophies}")


