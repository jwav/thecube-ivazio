import json
import logging
from typing import Tuple

import thecubeivazio.cube_utils as cube_utils
from thecubeivazio import cube_logger
from thecubeivazio.cube_common_defines import *


class CubeConfig:
    """Class to hold configuration values."""
    # singleton instance of CubeConfig
    _instance = None
    ALWAYS_USE_ENCRYPTION = False
    DEFAULT_PASSWORD = "pwd"
    AUTO_GENERATE_ENCRYPTED_CONFIG_AT_FIRST_LOAD = True
    ENCRYPTED_JSON_FILE_EXTENSION = ".json.enc"

    def __init__(self, do_not_load=False):
        self.log = cube_logger.CubeLogger(name="CubeConfig")
        self.log.setLevel(logging.INFO)

        self.config_dict = {}

        self.use_encryption = self.ALWAYS_USE_ENCRYPTION
        self.password = self.DEFAULT_PASSWORD

        self.clear()

        self._auto_generate_done = False


        if not do_not_load:
            self.load_default_config()
            if self.is_valid():
                self.log.info("CubeConfig fully loaded and valid")
            else:
                self.log.error("CubeConfig not fully loaded or invalid")

    def update_from_config(self, config: 'CubeConfig'):
        self.config_dict = config.config_dict
        self.use_encryption = config.use_encryption
        self.password = config.password


    @staticmethod
    def get_config():
        if CubeConfig._instance is None:
            CubeConfig._instance = CubeConfig()
        return CubeConfig._instance

    def is_valid(self) -> bool:
        try:
            assert self.config_dict, "config_dict is empty"
            assert self.game_durations_str, "game_durations_str is empty"
            assert self.game_durations_sec, "game_durations_sec is empty"
            assert self.defined_team_names, "team_names is empty"
            assert self.defined_trophies, "trophies is empty"
            assert self.valid_node_names, "valid_node_names is empty"
            return True
        except Exception as e:
            self.log.error(f"Error checking if config is valid: {e}")
            return False

    @cubetry
    def to_json(self) -> str:
        return json.dumps(self.config_dict)

    @classmethod
    @cubetry
    def make_from_json(cls, json_str: str) -> 'CubeConfig':
        config = CubeConfig()
        config.config_dict = json.loads(json_str)
        return config

    def unsafe_load_from_json(self, json_str: str):
        self.config_dict = json.loads(json_str)
        return True

    @cubetry
    def load_from_json_file(self, filepath: str = CONFIG_FILEPATH):
        return self.unsafe_load_from_json_file(filepath)

    def unsafe_load_from_json_file(self, filepath: str = CONFIG_FILEPATH):
        if self.use_encryption:
            return self.load_from_encrypted_json_file(filepath=filepath)
        self.log.info(f"Loading config from file: {filepath}")
        with open(filepath, "r") as f:
            return self.unsafe_load_from_json(f.read())

    @cubetry
    def save_to_json_file(self, filepath: str = CONFIG_FILEPATH) -> bool:
        return self.unsafe_save_to_json_file(filepath)

    def unsafe_save_to_json_file(self, filepath: str = CONFIG_FILEPATH) -> bool:
        if self.use_encryption:
            return self.save_to_encrypted_json_file(filepath=filepath)
        with open(filepath, "w") as f:
            f.write(self.to_json())
            return True

    @cubetry
    def load_from_encrypted_json_file(self, password: str=None, filepath: str = ENCRYPTED_CONFIG_FILEPATH) -> bool:
        return self.unsafe_load_from_encrypted_json_file(password, filepath)

    @cubetry
    def save_to_encrypted_json_file(self, password:str=None, filepath: str = ENCRYPTED_CONFIG_FILEPATH) -> bool:
        return self.unsafe_save_to_encrypted_json_file(password, filepath)

    def unsafe_load_from_encrypted_json_file(self, password: str=None, filepath: str = ENCRYPTED_CONFIG_FILEPATH) -> bool:
        self.log.info(f"Loading encrypted config from file: {filepath}")
        password = password or self.password
        assert password, "password is required to load encrypted json"
        self.unsafe_load_from_json(cube_utils.read_encrypted_file(filepath, password))
        return True

    def unsafe_save_to_encrypted_json_file(self, password:str=None, filepath: str = ENCRYPTED_CONFIG_FILEPATH) -> bool:
        assert filepath.endswith(self.ENCRYPTED_JSON_FILE_EXTENSION), f"filepath must end with {self.ENCRYPTED_JSON_FILE_EXTENSION} (filepath={filepath})"
        password = password or self.password
        assert password, "password is required to save encrypted json"
        cube_utils.encrypt_and_write_to_file(self.to_json(), filepath, password)
        return True

    def to_string(self) -> str:
        return self.to_json()

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        return self.__str__()

    def clear(self):
        self.config_dict = {}

    @classmethod
    @cubetry
    def make_from_json_file(cls, filepath: str) -> 'CubeConfig':
        with open(filepath, "r") as f:
            return cls.make_from_json(f.read())

    @classmethod
    @cubetry
    def make_from_encrypted_json_file(cls, password: str=None, filepath: str=ENCRYPTED_CONFIG_FILEPATH) -> 'CubeConfig':
        password = password or cls.DEFAULT_PASSWORD
        return cls.make_from_json(cube_utils.read_encrypted_file(filepath, password))

    @cubetry
    def load_default_config(self):
        try:
            # if there is an unecrypted config file, load it
            if not self.use_encryption:
                assert self.unsafe_load_from_json_file(CONFIG_FILEPATH), f"Error loading config file '{CONFIG_FILEPATH}'"
                self.log.success(f"Loaded config file '{CONFIG_FILEPATH}'")
                if self.AUTO_GENERATE_ENCRYPTED_CONFIG_AT_FIRST_LOAD and not self._auto_generate_done:
                    assert self.save_to_encrypted_json_file(), f"Error auto-generating encrypted config file: {ENCRYPTED_CONFIG_FILEPATH}"
                    self.log.success(f"Auto-generating encrypted config file: {ENCRYPTED_CONFIG_FILEPATH}")
                    self._auto_generate_done = True
                return True
            # if not using encryption...
            assert self.load_from_encrypted_json_file(ENCRYPTED_CONFIG_FILEPATH), f"Error loading encrypted config file: {ENCRYPTED_CONFIG_FILEPATH}"
            self.log.success(f"Loaded encrypted config file: {ENCRYPTED_CONFIG_FILEPATH}")
            return True
        except Exception as e:
            self.log.error(f"Error loading default config: {e}")
            return False


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
    def defined_team_names(self) -> Optional[list[str]]:
        return self.config_dict.get("team_names", None)

    @property
    def valid_node_names(self) -> Optional[list[str]]:
        return self.config_dict.get("valid_node_names", None)

    @property
    def defined_trophies(self) -> list['CubeTrophy']:
        try:
            from thecubeivazio.cube_game import CubeTrophy
            return [CubeTrophy(**trophy) for trophy in self.config_dict.get("trophies", [])]
        except Exception as e:
            self.log.error(f"Error getting trophies: {e}")
            return []

    @property
    def display_team_names_on_rgb(self) -> Optional[bool]:
        return self.config_dict.get("display_team_names_on_rgb", None)

    @property
    def cubebox_audio_volume_percent(self) -> Optional[int]:
        try:
            return int(self.config_dict.get("cubebox_audio_volume_percent"))
        except:
            return None

    @property
    def cubemaster_audio_volume_percent(self) -> Optional[int]:
        try:
            return int(self.config_dict.get("cubemaster_audio_volume_percent"))
        except:
            return None

    @cubetry
    def set_field(self, field_name: str, value) -> bool:
        self.config_dict[field_name] = value
        return True

    @cubetry
    def get_field(self, field_name:str) -> Optional[str]:
        return self.config_dict.get(field_name, None)

    @cubetry
    def set_password(self, password: str) -> bool:
        self.password = password
        return True

    @cubetry
    def set_field(self, field_name: str, value) -> bool:
        self.config_dict[field_name] = value
        return True

    @cubetry
    def add_resetter_rfid(self, uid:str) -> bool:
        key = "resetter_rfids"
        resetters = self.config_dict.get(key, [])
        if uid not in resetters:
            resetters.append(uid)
            self.config_dict[key] = resetters
        return True

    @cubetry
    def remove_resetter_rfid(self, uid:str) -> bool:
        key = "resetter_rfids"
        resetters = self.config_dict.get(key, [])
        if uid in resetters:
            resetters.remove(uid)
            self.config_dict[key] = resetters
        return True

    @cubetry
    def get_resetter_rfids(self) -> list[str]:
        return self.config_dict.get("resetter_rfids", [])




def encryption_test():
    filepath = f"{CONFIG_FILEPATH}.enctest"
    config = CubeConfig()
    config.set_field("test_field", "test_value")
    config.save_to_encrypted_json_file(password="test_password", filepath=filepath)
    config2 = CubeConfig()
    config2.load_from_encrypted_json_file(password="test_password", filepath=filepath)
    assert config.config_dict == config2.config_dict
    assert config.config_dict["test_field"] == "test_value"
    assert config.to_json() == config2.to_json()
    print("encryption test passed")
    exit(0)




if __name__ == "__main__":
    # generate_encrypted_config_from_non_encrypted_config()
    # encryption_test()
    config = CubeConfig()
    enc_config = CubeConfig.make_from_encrypted_json_file()
    assert config.config_dict == enc_config.config_dict
    assert config.to_json() == enc_config.to_json()
    exit(0)
    config.log.info("-----------------")
    config.log.info(f"config valid?: {config.is_valid()}")
    config.log.info(f"game_durations: {config.game_durations_str}")
    config.log.info(f"game_durations: {config.game_durations_sec}")
    config.log.info(f"team_names: {config.defined_team_names}")
    config.log.info(f"trophies: {config.defined_trophies}")
