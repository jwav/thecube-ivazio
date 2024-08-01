"""Modelises a TheCube game session, i.e. a team trying to open a CubeBox"""
import enum
import hashlib
import json
import random
import time
from typing import List, Dict, Tuple, Iterable

import thecubeivazio.cube_rfid as cube_rfid
from thecubeivazio import cube_identification as cubeid
from thecubeivazio import cube_utils as cube_utils
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_config import CubeConfig
from thecubeivazio.cube_logger import CubeLogger

class CubeboxState(enum.Enum):
    # TODO: implement the unknown state, useful for the frontdesk
    STATE_UNKNOWN = "UNKNOWN"
    STATE_READY_TO_PLAY = "READY_TO_PLAY"
    STATE_PLAYING = "PLAYING"
    STATE_WAITING_FOR_RESET = "WAITING_FOR_RESET"

    def __eq__(self, other):
        try:
            return str(self.value) == str(other.value)
        except Exception as e:
            CubeLogger.static_error(f"CubeboxState.__eq__ {e}")
            return False

    def __str__(self):
        return self.value

    def to_french(self):
        return "Prêt à jouer" if self == CubeboxState.STATE_READY_TO_PLAY \
            else "En cours de jeu" if self == CubeboxState.STATE_PLAYING \
            else "En attente de réinitialisation" if self == CubeboxState.STATE_WAITING_FOR_RESET \
            else "État inconnu"


# TODO safeguard methods liable to raise exceptions
class CubeboxStatus:
    """Represents a game session, i.e. a team trying to open a CubeBox"""

    def __init__(self, cube_id: CubeId = None, current_team_name: TeamName = None, start_timestamp: Seconds = None,
                 win_timestamp: Seconds = None, last_valid_rfid_line: cube_rfid.CubeRfidLine = None,
                 state: CubeboxState = CubeboxState.STATE_UNKNOWN):
        self.cube_id = cube_id
        self.current_team_name = current_team_name
        self.start_timestamp = start_timestamp
        self.win_timestamp = win_timestamp
        self.last_valid_rfid_line = last_valid_rfid_line
        self._state = state
        # helper variable to implement the CUBE_TIME_BETWEEN_PRESSES time counting rule
        self._prev_cubebox_win_timestamp = None

    def __str__(self):
        return self.to_string()

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.__eq__ {e}")
            return False

    @cubetry
    def is_valid(self):
        """if this function returns False, then it might have been made from corrupted data"""
        return all((self.cube_id in cubeid.CUBEBOX_IDS, self._state in CubeboxState))

    @property
    def hash(self) -> Hash:
        try:
            return hashlib.sha256(self.to_string().encode()).hexdigest()
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.hash {e}")
            return ""

    @property
    @cubetry
    def node_name(self) -> NodeName:
        return cubeid.cubebox_index_to_node_name(self.cube_id)

    def __repr__(self):
        ret = f"CubeboxStatus({self.to_string()}, last_valid_rfid_line={self.last_valid_rfid_line})"
        return ret

    def to_string(self) -> str:
        return self.to_json()

    @cubetry
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def make_from_json(cls, json_str: str):
        try:
            return cls.make_from_dict(json.loads(json_str))
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.make_from_json {e.with_traceback(None)}")
            return None

    @cubetry
    def to_dict(self) -> Dict:
        return {
            "cube_id": self.cube_id,
            "current_team_name": self.current_team_name,
            "start_timestamp": self.start_timestamp,
            "win_timestamp": self.win_timestamp,
            "last_valid_rfid_line": self.last_valid_rfid_line.to_dict() if self.last_valid_rfid_line else None,
            "state": self.get_state().value
        }

    @classmethod
    def make_from_dict(cls, d: Dict) -> Optional['CubeboxStatus']:
        # print(f"CubeboxStatus.make_from_dict {d}")
        try:
            assert type(d) == dict
            cube_id = int(d.get("cube_id"))
            ret = CubeboxStatus(cube_id)
            ret.current_team_name = d.get("current_team_name", None)
            ret.start_timestamp = d.get("start_timestamp", None)
            if ret.start_timestamp is not None:
                ret.start_timestamp = float(ret.start_timestamp)
            ret.win_timestamp = d.get("win_timestamp", None)
            if ret.win_timestamp is not None:
                ret.win_timestamp = float(ret.win_timestamp)
            # skip the rfid line. it will not be useful for whomever asks for it
            # ret.last_valid_rfid_line = cube_rfid.CubeRfidLine.make_from_string(kwargs.get("last_valid_rfid_line"))
            ret._state = CubeboxState(d.get("state"))
            return ret
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.make_from_dict {e.with_traceback(None)}")
            return None

    @classmethod
    def make_from_kwargs(cls, **kwargs) -> Optional['CubeboxStatus']:
        return cls.make_from_dict(kwargs)

    @staticmethod
    def make_from_string(string: str) -> Optional['CubeboxStatus']:
        try:
            kwargs = {}
            for line in string.split("\n"):
                if line:
                    key, value = line.split("=")
                    kwargs[key.strip()] = value.strip()
            return CubeboxStatus.make_from_kwargs(**kwargs)
        except Exception as e:
            print(e)
            return None

    def get_state(self) -> CubeboxState:
        """Returns the current state of the CubeBox game:
        - STATE_READY_TO_PLAY if the CubeBox is ready to be played
        - STATE_PLAYING if a team is currently playing
        - STATE_WAITING_FOR_RESET if a team has won and the CubeBox is waiting to be reset by a staff member
        """
        return self._state

    def is_ready_to_play(self) -> bool:
        return self.get_state() == CubeboxState.STATE_READY_TO_PLAY

    def is_playing(self) -> bool:
        return self.get_state() == CubeboxState.STATE_PLAYING

    def is_waiting_for_reset(self) -> bool:
        return self.get_state() == CubeboxState.STATE_WAITING_FOR_RESET

    def set_state_ready_to_play(self):
        """Resets the CubeBox to its initial state, ready to be played by a team."""
        self.current_team_name = None
        self.start_timestamp = None
        self.win_timestamp = None
        self._state = CubeboxState.STATE_READY_TO_PLAY

    def reset(self):
        """alias of set_state_ready_to_play()"""
        self.set_state_ready_to_play()

    def set_state_playing(self, team_name: str = None, start_timestamp: Seconds = None):
        self.current_team_name = team_name
        self.start_timestamp = start_timestamp
        self.win_timestamp = None
        self._state = CubeboxState.STATE_PLAYING

    def set_state(self, state: CubeboxState) -> bool:
        try:
            if state not in CubeboxState:
                CubeLogger.static_error(f"CubeboxStatus.set_state: unknown state {state}")
                return False
            if state == CubeboxState.STATE_READY_TO_PLAY:
                self.set_state_ready_to_play()
            elif state == CubeboxState.STATE_PLAYING:
                self.set_state_playing()
            elif state == CubeboxState.STATE_WAITING_FOR_RESET:
                self.set_state_waiting_for_reset()
            elif state == CubeboxState.STATE_UNKNOWN:
                self._state = CubeboxState.STATE_UNKNOWN
            return True
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.set_state {e}")
            return False

    def set_state_waiting_for_reset(self):
        self._state = CubeboxState.STATE_WAITING_FOR_RESET

    def copy(self) -> 'CubeboxStatus':
        ret = CubeboxStatus(self.cube_id)
        ret.build_from_copy(self)
        return ret

    def build_from_copy(self, other: 'CubeboxStatus'):
        self.cube_id = other.cube_id
        self.current_team_name = other.current_team_name
        self.start_timestamp = other.start_timestamp
        self.win_timestamp = other.win_timestamp
        self.last_valid_rfid_line = other.last_valid_rfid_line
        self._state = other.get_state()

    @property
    def completion_time_sec(self) -> Optional[Seconds]:
        try:
            if CUBE_TIME_METHOD == CUBE_TIME_RFID_TO_PRESS or self._prev_cubebox_win_timestamp is None:
                return self.win_timestamp - self.start_timestamp
            elif CUBE_TIME_METHOD == CUBE_TIME_BETWEEN_PRESSES:
                return self.win_timestamp - self._prev_cubebox_win_timestamp
            else:
                raise Exception(f"CubeboxStatus.completion_time_sec: unknown CUBE_TIME_METHOD {CUBE_TIME_METHOD}")
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.completion_time_sec {e}")
            return None

    @property
    def completion_time_str(self) -> str:
        completion_time = self.completion_time_sec
        if completion_time is None:
            return ""
        return cube_utils.seconds_to_hhmmss_string(completion_time)

    @cubetry
    def calculate_box_score(self) -> Optional[int]:
        # find the preset associated to this cubebox. If not found, use the default one
        presets = CubeboxesScoringPresets.make_from_config()
        assert presets, "CubeboxStatus.calculate_score: failed to build scoring presets from config!"
        calculator = presets.get_calculator_for_cube_id(self.cube_id)
        if not calculator:
            calculator = presets.get_default_calculator()
            CubeLogger.static_warning(
                f"CubeboxStatus.calculate_score: no preset found for cubebox {self.node_name}. Using default preset.")
        if not calculator:
            raise Exception(f"CubeboxStatus.calculate_score: failed to build default score calculator")
        # calculate the score
        return calculator.compute_score(self.completion_time_sec)

    @cubetry
    def is_completed(self) -> bool:
        return self.is_valid() and self.win_timestamp is not None and self.start_timestamp is not None


class CubeboxesStatusList(List[CubeboxStatus]):
    """List of CubeGame instances, one for each CubeBox in TheCube game. Meant to be used by the CubeMaster and FrontDesk."""
    JSON_ROOT_OBJECT_NAME = "cubeboxes"

    @cubetry
    def copy(self) -> 'CubeboxesStatusList':
        return CubeboxesStatusList([box.copy() for box in self], force_complete_list=self._force_complete_list)

    def __init__(self, cubeboxes: Optional[List[CubeboxStatus]] = None, force_complete_list=True):
        """If `cubeboxes` is not None, the CubeboxesStatusList will be initialized with these CubeboxStatus instances.
        If `force_complete_list` is True, the CubeboxesStatusList will be initialized with all the CubeboxStatus instances
        for each CubeBox in TheCube game."""
        super().__init__()
        self._force_complete_list = force_complete_list
        if force_complete_list:
            self.initialize_all_cubeboxes()
        if cubeboxes:
            self.update_from_cubeboxes(cubeboxes)

    @cubetry
    def update_from_cubeboxes(self, cubeboxes: Iterable[CubeboxStatus]) -> bool:
        for box in cubeboxes:
            self.update_from_cubebox(box)
        return True

    @cubetry
    def is_valid(self):
        return all([box.is_valid() for box in self])

    @cubetry
    def extend(self, cubeboxes_list: Iterable[CubeboxStatus]):
        self.update_from_cubeboxes(cubeboxes_list)

    @cubetry
    def append(self, box: CubeboxStatus):
        self.update_from_cubebox(box)

    @property
    @cubetry
    def hash_dict(self) -> Dict[NodeName, Hash]:
        return {cubeid.cubebox_index_to_node_name(box.cube_id): box.hash for box in self}

    @property
    @cubetry
    def hash(self) -> Hash:
        return hashlib.sha256(self.to_string().encode()).hexdigest()

    def compare_with_hashlist(self, hash_dict: Dict[NodeName, Hash]) -> Optional[Tuple[NodeName, ...]]:
        """Returns the names of the teams whose hash is different from the one in the hash_dict.
        If the returned tuple is empty, it means that the hash_dict is up-to-date with the teams list.
        If None is returned, it means that there was an error."""
        try:
            return tuple([node_name for node_name, hash in hash_dict.items() if
                          hash != self.get_cubebox_by_node_name(node_name).hash])
        except Exception as e:
            CubeLogger.static_error(f"CubeboxesStatusList.compare_with_hashlist {e}")
            return None

    def matches_hashlist(self, hash_dict: Dict[NodeName, Hash]) -> bool:
        return self.compare_with_hashlist(hash_dict) == ()

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except Exception as e:
            CubeLogger.static_error(f"CubeboxesStatusList.__eq__ {e}")
            return False

    def __repr__(self) -> str:
        ret = f"CubeboxStatusList : {len(self)} boxes\n"
        for box in self:
            ret += f"  {box.to_string()}\n"
        return ret

    def to_string(self):
        return self.to_json()

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self) -> Dict:
        return {
            self.JSON_ROOT_OBJECT_NAME: [box.to_dict() for box in self]
        }

    @classmethod
    def make_from_dict(cls, d: Dict) -> Optional['CubeboxesStatusList']:
        try:
            # print(f"CubeboxesStatusList.make_from_dict d={d}")
            assert type(d) == dict
            assert cls.JSON_ROOT_OBJECT_NAME in d
            ret = cls()
            # print(f"d (type={type(d)}: {d}")
            for box_data in d[cls.JSON_ROOT_OBJECT_NAME]:
                # print(f"box_data (type={type(box_data)}) : {box_data}")
                ret.update_from_cubebox(CubeboxStatus.make_from_dict(box_data))
            return ret
        except Exception as e:
            CubeLogger.static_error(f"CubeboxesStatusList.make_from_dict {e.with_traceback(None)}")
            return None

    @classmethod
    def make_from_json(cls, json_str: str):
        try:
            return cls.make_from_dict(json.loads(json_str))
        except Exception as e:
            CubeLogger.static_error(f"CubeboxesStatusList.make_from_json {e}")
            return None

    @classmethod
    def make_from_kwargs(cls, **kwargs):
        return cls.make_from_dict(kwargs)

    @cubetry
    def update_from_cubebox(self, cubebox: CubeboxStatus) -> bool:
        if not cubebox:
            return False
        # if we have it, update it
        for box in self:
            if box.cube_id == cubebox.cube_id:
                box.build_from_copy(cubebox)
                return True
        # if we don't have it, add it
        super().append(cubebox)
        return False

    def get_cubebox_by_cube_id(self, cubebox_id: int) -> Optional[CubeboxStatus]:
        for box in self:
            if box.cube_id == cubebox_id:
                return box
        return None

    def get_cubebox_by_node_name(self, node_name: str) -> Optional[CubeboxStatus]:
        for box in self:
            if cubeid.node_name_to_cubebox_index(node_name) == box.cube_id:
                return box
        return None

    def initialize_all_cubeboxes(self):
        self.clear()
        super().extend([CubeboxStatus(cube_id) for cube_id in cubeid.CUBEBOX_IDS])

    def free_cubes(self) -> List[CubeId]:
        return [box.cube_id for box in self if box.is_ready_to_play()]

    def played_cubes(self) -> List[int]:
        return [box.cube_id for box in self if not box.is_ready_to_play()]


class CubeTrophy:
    """Represents a trophy that a team can win by playing a CubeGame"""

    def __init__(self, name: str, french_name: str, description: str, points: int, image_filename: str = None):
        self.name = name
        self.french_name = french_name
        self.description = description
        self.points = points
        self.image_filename = image_filename or DEFAULT_TROPHY_IMAGE_FILENAME

    @property
    def image_filepath(self) -> str:
        try:
            return str(os.path.join(IMAGES_DIR, self.image_filename))
        except:
            return str(DEFAULT_TROPHY_IMAGE_FILEPATH)

    def to_string(self):
        sep = ","
        return sep.join([f"{k}={v}" for k, v in self.to_dict().items()])

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        return self.to_json()

    @cubetry
    def __eq__(self, other):
        return self.to_dict() == other.to_dict()

    @cubetry
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @cubetry
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "french_name": self.french_name,
            "description": self.description,
            "points": self.points,
            "image_filename": self.image_filename
        }

    @classmethod
    @cubetry
    def make_from_dict(cls, d: Dict) -> Optional['CubeTrophy']:
        try:
            return cls(d.get("name"),
                       d.get("french_name"),
                       d.get("description"),
                       int(d.get("points")),
                       d.get("image_filename", None))
        except Exception as e:
            print(e)
            return None

    @classmethod
    @cubetry
    def make_from_name(cls, trophy_name: str) -> Optional['CubeTrophy']:
        for config_trophy in CubeConfig.get_config().defined_trophies:
            config_trophy: CubeTrophy
            if config_trophy.name == trophy_name:
                return config_trophy

    @classmethod
    @cubetry
    def make_from_french_name(cls, french_name: str) -> Optional['CubeTrophy']:
        for config_trophy in CubeConfig.get_config().defined_trophies:
            config_trophy: CubeTrophy
            if config_trophy.french_name == french_name:
                return config_trophy


# an alias just for clarity, we'll use this one to refer exclusively to completed cubeboxes
CompletedCubeboxStatus = CubeboxStatus
CompletedCubeboxStatus.__doc__ = "Represents a CubeBox that has been successfully played by a team"


class CompletedCubeboxStatusList(CubeboxesStatusList):
    def __init__(self, cubeboxes: Optional[List[CompletedCubeboxStatus]] = None):
        super().__init__(cubeboxes, force_complete_list=False)

    def is_valid(self):
        try:
            assert super().is_valid(), f"CompletedCubeboxStatusList.is_valid: super().is_valid() failed"
            assert all([box.is_completed() for box in
                        self]), f"CompletedCubeboxStatusList.is_valid: not all boxes are completed"
            return True
        except Exception as e:
            CubeLogger.static_error(f"CompletedCubeboxStatusList.is_valid {e}")
            return False


class CubeTeamStatus:
    """Represents a team playing a CubeGame"""

    CUSTOM_NAME_MAX_LENGTH = 30

    def __init__(self, name: str, rfid_uid: str, max_time_sec: Seconds, creation_timestamp: Timestamp = None,
                 custom_name: str = "",
                 start_timestamp: Timestamp = None, current_cubebox_id: int = None,
                 completed_cubeboxes: CompletedCubeboxStatusList = None,
                 trophies_names: List[str] = None,
                 use_alarm=False,
                 last_modification_timestamp: Timestamp = None
                 ):
        self.creation_timestamp = creation_timestamp or time.time()
        # the team's code name (a city name)
        self.name = name
        # the custom names chosen by the customers. If no custom name, we use the name
        self.custom_name = custom_name or name
        # if the custom name is too long, we truncate it
        self.custom_name = self.custom_name[:self.CUSTOM_NAME_MAX_LENGTH]
        # the RFID UID of the team
        self.rfid_uid = rfid_uid
        # the maximum time allowed to play the CubeGame
        self.max_time_sec = max_time_sec
        # the time when the team starts playing its first cubebox
        self.start_timestamp = start_timestamp
        # the cubebox ID currently being played by the team
        self.current_cubebox_id = current_cubebox_id
        # the list of the cubeboxes IDs that the team has successfully played, with their completion times
        self._completed_cubeboxes = CompletedCubeboxStatusList(completed_cubeboxes)
        # the trophies collected by the team, awarded by the frontdesk
        self.trophies_names: List[str] = trophies_names or []
        # for certain teams, we want to use a loud alarm when their time is up
        self.use_alarm = use_alarm
        # used only for database synchronisation
        self.last_modification_timestamp = last_modification_timestamp
        # TODO: implement and test
        self.pause_timestamps = []
        self.resume_timestamps = []

    @cubetry
    def auto_compute_trophies(self):
        """Computes the trophies that the team has won,
        based on the completion times of the cubeboxes and other factors"""
        # find the preset associated to this cubebox. If not found, use the default one
        presets = CubeboxesScoringPresets.make_from_config()
        assert presets, "CubeTeamStatus.compute_trophies: failed to build scoring presets from config!"
        # 12_CUBES_DONE
        if len(self.completed_cubeboxes) >= 12:
            self.add_trophy_by_name("12_CUBES_DONE")
        # 6_CUBES_DONE
        if len(self.completed_cubeboxes) >= 6:
            self.add_trophy_by_name("6_CUBES_DONE")
        # CUBE_DONE_FAST
        for box in self.completed_cubeboxes:
            if box.completion_time_sec < 5 * 60:
                self.add_trophy_by_name("CUBE_DONE_FAST")
                break
        # EXPERT : hard cube under 10 minutes
        for box in self.completed_cubeboxes:
            cube_id = box.cube_id
            # check if it's a hard one
            scoring_settings = CubeboxesScoringSettings()
            preset_name = scoring_settings.get_preset_name_for_cube_id(cube_id)
            if preset_name == "hard" and box.completion_time_sec < 10 * 60:
                self.add_trophy_by_name("EXPERT")
                break

    @cubetry
    def is_playing(self) -> bool:
        return self.start_timestamp is not None and not self.end_timestamp

    # TODO: implement
    @cubetry
    def is_paused(self) -> bool:
        return len(self.pause_timestamps) > len(self.resume_timestamps)

    @cubetry
    def update_modification_timestamp(self):
        self.last_modification_timestamp = time.time()

    @property
    @cubetry
    def completed_cubeboxes(self) -> CompletedCubeboxStatusList:
        assert self._update_completed_cubeboxes()
        return CompletedCubeboxStatusList([box for box in self._completed_cubeboxes])

    @cubetry
    def _update_completed_cubeboxes(self) -> bool:
        """updates the time elapsed for each cubebox, according to the rule defined in
        cube_common_defines"""
        # if any completed box isnt set properly, remove it.
        # This shouldn't happen so if one of these cubeboxes is not completed, log it as a critical error
        for box in self._completed_cubeboxes:
            if not box.is_completed():
                CubeLogger.static_critical(
                    f"CubeTeamStatus._update_completed_cubeboxes: cubebox {box.node_name} is not completed!")
        self._completed_cubeboxes = [box for box in self._completed_cubeboxes if box.is_completed()]
        # order the completed cubeboxes by time of completion
        self._completed_cubeboxes.sort(key=lambda box: box.win_timestamp)
        # for each completed box, set the _prev_cubebox_win_timestamp
        for i, box in enumerate(self._completed_cubeboxes):
            if i == 0:
                box._prev_cubebox_win_timestamp = None
            else:
                box._prev_cubebox_win_timestamp = self._completed_cubeboxes[i - 1].win_timestamp
        return True

    @property
    def end_timestamp(self) -> Optional[Timestamp]:
        try:
            return self.start_timestamp + self.max_time_sec
        except:
            return None

    def is_valid(self):
        """if this function returns False, then it might have been made from corrupted data"""
        try:
            assert isinstance(self.name, str), f"self.name is not a str: {self.name}"
            assert isinstance(self.rfid_uid, str), f"self.rfid_uid is not a str: {self.rfid_uid}"
            assert isinstance(self.max_time_sec,
                              (int, float)), f"self.max_time_sec is not a number: {self.max_time_sec}"
            assert isinstance(self.creation_timestamp,
                              (int, float)), f"self.creation_timestamp is not a number: {self.creation_timestamp}"
            assert isinstance(self.custom_name, str), f"self.custom_name is not a str: {self.custom_name}"
            assert isinstance(self.start_timestamp, (int,
                                                     float)) or self.start_timestamp is None, f"self.start_timestamp is not a number: {self.start_timestamp}"
            assert isinstance(self.current_cubebox_id,
                              int) or self.current_cubebox_id is None, f"self.current_cubebox_id is not a number: {self.current_cubebox_id}"
            assert isinstance(self._completed_cubeboxes,
                              list), f"self.completed_cubeboxes is not a list: {self._completed_cubeboxes}"
            assert all([box.is_valid() for box in
                        self._completed_cubeboxes]), f"self.completed_cubeboxes is not a list of valid CompletedCubeboxStatus: {self._completed_cubeboxes}"
            assert all([box.is_completed() for box in
                        self._completed_cubeboxes]), f"self.completed_cubeboxes is not a list of completed CompletedCubeboxStatus: {self._completed_cubeboxes}"
            assert isinstance(self.trophies_names, list) and all([isinstance(t, str) for t in
                                                                  self.trophies_names]), f"self.trophies_names is not a list of str: {self.trophies_names}"
            assert isinstance(self.use_alarm, bool), f"self.use_alarm is not a bool: {self.use_alarm}"

            return True
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.is_valid {e}")
            return False

    @property
    def remaining_time(self) -> Optional[Seconds]:
        try:
            ret = self.max_time_sec - (time.time() - self.start_timestamp)
            # TODO: take pauses into account
            return ret if ret > 0 else 0
        except:
            return None

    @property
    def trophies(self) -> List[CubeTrophy]:
        return [CubeTrophy.make_from_name(trophy_name) for trophy_name in self.trophies_names]

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.__eq__ {e}")
            return False

    @cubetry
    def is_same_team_as(self, team):
        """Returns True if the creation timestamps are the same. This is the only way to uniquely identify a team."""
        return self.creation_timestamp == team.creation_timestamp

    def __repr__(self):
        return self.to_string()

    def __str__(self):
        return self.to_string()

    def to_string(self) -> Optional[str]:
        return self.to_json()

    def to_dict(self) -> Dict:
        """This is the main method to convert a CubeTeamStatus instance to any kind of text.
        When the CubeTeamStatus structure is changed, update this method as well as make_from_dict()"""
        return {
            "name": self.name,
            "custom_name": self.custom_name,
            "rfid_uid": self.rfid_uid,
            "max_time_sec": self.max_time_sec,
            "creation_timestamp": self.creation_timestamp,
            "start_timestamp": self.start_timestamp,
            "current_cubebox_id": self.current_cubebox_id,
            "completed_cubeboxes": [box.to_dict() for box in self._completed_cubeboxes],
            "trophies_names": self.trophies_names,
            "use_alarm": self.use_alarm,
            "last_modification_timestamp": self.last_modification_timestamp,
        }

    @classmethod
    def make_from_dict(cls, d: Optional[Dict]) -> Optional['CubeTeamStatus']:
        """This is the main method to convert any kind of text to a CubeTeamStatus instance.
        When the CubeTeamStatus structure is changed, update this method as well as to_dict()"""
        # CubeLogger.static_debug(f"CubeTeamStatus.make_from_dict {d}")
        try:
            ret = cls(name=d.get("name"),
                      rfid_uid=d.get("rfid_uid"),
                      max_time_sec=d.get("max_time_sec"),
                      creation_timestamp=d.get("creation_timestamp"))

            ret.custom_name = d.get("custom_name", "")
            ret.start_timestamp = d.get("start_timestamp", None)
            if ret.start_timestamp is not None:
                ret.start_timestamp = float(ret.start_timestamp)
            ret.current_cubebox_id = d.get("current_cubebox_id", None)
            if ret.current_cubebox_id is not None:
                ret.current_cubebox_id = int(ret.current_cubebox_id)
            ret._completed_cubeboxes = [
                CompletedCubeboxStatus.make_from_dict(box) for box in d.get("completed_cubeboxes", [])]
            ret.trophies_names = d.get("trophies_names", [])
            ret.use_alarm = d.get("use_alarm", False)
            if ret.last_modification_timestamp is not None:
                ret.last_modification_timestamp = float(ret.last_modification_timestamp)
            return ret
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.make_from_dict {e}")
            return None

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def make_from_json(cls, json_str: Optional[str]):
        try:
            d = json.loads(json_str)
            return cls.make_from_dict(d)
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.make_from_json {e}")
            return None

    @property
    def completed_cubebox_ids(self) -> List[CubeId]:
        return [box.cube_id for box in self.completed_cubeboxes]

    @property
    def hash(self) -> Hash:
        try:
            return hashlib.sha256(self.to_string().encode()).hexdigest()
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.hash {e}")
            return ""

    # TODO: test
    def is_time_up(self, current_time: Seconds = None) -> bool:
        if not self.start_timestamp or not self.max_time_sec:
            return False
        current_time = current_time or time.time()
        try:
            return current_time - self.start_timestamp > self.max_time_sec
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.is_time_up {e}")
            return False

    # TODO: test. useful?
    def has_played_today(self, current_time: Seconds = None) -> bool:
        if current_time is None:
            current_time = time.time()
        try:
            return any(
                [box.win_timestamp > cube_utils.timestamps_are_in_same_day(self.start_timestamp, current_time) for
                 box in self._completed_cubeboxes])
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.has_played_today {e}")
            return False

    # TODO: test
    def has_played_this_week(self, current_time: Seconds = None) -> bool:
        if current_time is None:
            current_time = time.time()
        try:
            return any(
                [box.win_timestamp > cube_utils.timestamps_are_in_same_week(self.start_timestamp, current_time) for
                 box in self._completed_cubeboxes])
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.has_played_this_week {e}")
            return False

    # TODO: test
    def has_played_this_month(self, current_time: Seconds = None) -> bool:
        if current_time is None:
            current_time = time.time()
        try:
            return any(
                [box.win_timestamp > cube_utils.timestamps_are_in_same_month(self.start_timestamp, current_time) for
                 box in self._completed_cubeboxes])
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.has_played_this_month {e}")
            return False

    # TODO: test
    def has_completed_cube(self, cube_id: int) -> bool:
        return cube_id in [box.cube_id for box in self._completed_cubeboxes]

    # TODO: test
    def set_completed_cube(self, cube_id: int, start_timestamp: float, win_timestamp: float) -> bool:
        if self.has_completed_cube(cube_id):
            CubeLogger.static_warning(
                f"CubeTeamStatus.set_completed_cube: Cube {cube_id} already completed by team {self.name}")
            return False
        self._completed_cubeboxes.append(CompletedCubeboxStatus(
            cube_id=cube_id, current_team_name=self.name, start_timestamp=start_timestamp,
            win_timestamp=win_timestamp))
        return True

    def has_started(self) -> bool:
        return self.start_timestamp is not None

    @cubetry
    def calculate_team_score(self) -> int:
        """Calculate the total score of the team, based on the completion times of the cubeboxes it has played."""
        # memo: cid means cube_id, cts means completion_time_sec
        try:
            boxes_score = sum([box.calculate_box_score() for box in self._completed_cubeboxes])
        except:
            boxes_score = 0
        try:
            trophy_score = sum([trophy.points for trophy in self.trophies])
        except:
            trophy_score = 0
        # CubeLogger.static_info(f"CubeTeamStatus.calculate_score boxes_score={boxes_score} trophy_score={trophy_score}")
        return boxes_score + trophy_score

    @cubetry
    def copy(self):
        ret = CubeTeamStatus(name=self.name, rfid_uid=self.rfid_uid, max_time_sec=self.max_time_sec,
                             creation_timestamp=self.creation_timestamp, custom_name=self.custom_name,
                             start_timestamp=self.start_timestamp, current_cubebox_id=self.current_cubebox_id,
                             completed_cubeboxes=self._completed_cubeboxes.copy(),
                             trophies_names=self.trophies_names.copy(), use_alarm=self.use_alarm)
        return ret

    @cubetry
    def resign_current_cube(self):
        # TODO: do we need to actually do something more here?
        self.current_cubebox_id = None

    @cubetry
    def has_played_cube(self, cubebox_id):
        return cubebox_id in [box.cube_id for box in self._completed_cubeboxes]

    @cubetry
    def update_from_team(self, team):
        """If this team is the same as the other team, update its data with the other team's data,
        preserving the completed cubeboxes and trophies
        If this is another team, return False"""
        assert team.is_valid(), f"CubeTeamStatus.update_from_team: invalid team {team}"
        CubeLogger.static_debug(f"CubeTeamStatus.update_from_team: updating team {self.name}")
        if not self.is_same_team_as(team):
            CubeLogger.static_debug(f"CubeTeamStatus.update_from_team: this is not the same team. returning.")
            return False
        # TODO: just do a raw copy
        CubeLogger.static_debug(f"CubeTeamStatus.update_from_team: this is the same team. updating.")
        CubeLogger.static_debug(f"current team status: {self.to_json()}")
        for completed_cube in team.completed_cubeboxes:
            self.set_completed_cube(completed_cube.cube_id, completed_cube.start_timestamp,
                                    completed_cube.win_timestamp)
        for trophy in team.trophies_names:
            self.add_trophy_by_name(trophy)
        self.current_cubebox_id = team.current_cubebox_id
        if not self.start_timestamp:
            self.start_timestamp = team.start_timestamp
        self.max_time_sec = team.max_time_sec
        CubeLogger.static_debug(f"updated team status: {self.to_json()}")
        return True

    @cubetry
    def add_trophy_by_name(self, trophy_name: str):
        if not trophy_name in self.trophies_names:
            self.trophies_names.append(trophy_name)

    @cubetry
    def remove_trophy_by_name(self, trophy_name: str):
        if trophy_name in self.trophies_names:
            self.trophies_names.remove(trophy_name)

    @cubetry
    def remove_trophy_by_french_name(self, french_name: str):
        trophy = CubeTrophy.make_from_french_name(french_name)
        if trophy:
            self.remove_trophy_by_name(trophy.name)

    @cubetry
    def add_trophy_by_french_name(self, french_name: str):
        trophy = CubeTrophy.make_from_french_name(french_name)
        if trophy:
            self.add_trophy_by_name(trophy.name)



# TODO : add ranks for the day, week, mont, all-time
class CubeTeamsStatusList(List[CubeTeamStatus]):
    """List of CubeTeam instances, one for each team playing a CubeGame. Meant to be used by the CubeMaster and FrontDesk."""

    DEFAULT_JSON_FILE = "cube_teams_list.json"
    JSON_ROOT_OBJECT_NAME = "teams"

    def __init__(self, teams: Optional[List[CubeTeamStatus]] = None):
        super().__init__()
        if teams:
            self.extend(teams)

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.to_string()

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamsStatusList.__eq__ {e}")
            return False

    @property
    def hash_dict(self) -> Dict[TeamName, Hash]:
        return {team.name: team.hash for team in self}

    @cubetry
    def copy(self) -> 'CubeTeamsStatusList':
        ret = CubeTeamsStatusList()
        for team in self:
            ret.add_team(team.copy())
        return ret

    @cubetry
    def sort_teams_by_score(self):
        def get_team_score(team: CubeTeamStatus):
            return team.calculate_team_score()

        self.sort(key=get_team_score, reverse=True)

    @property
    def hash(self) -> Hash:
        try:
            return hashlib.sha256(self.to_string().encode()).hexdigest()
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamsStatusList.hash {e}")
            return ""

    @cubetry
    def has_team(self, team: CubeTeamStatus) -> bool:
        for t in self:
            if t.is_same_team_as(team):
                return True

    @cubetry
    def get_team_ranking_among_list(self, team: CubeTeamStatus) -> int:
        """Returns the ranking of the team among the teams in this list.
        The ranking is based on the total score of the team."""
        try:
            assert self.has_team(
                team), f"CubeTeamsStatusList.get_team_ranking_among_list: team with cts {team.creation_timestamp} not in list"

            def score(t: CubeTeamStatus) -> int:
                return t.calculate_team_score()

            return sorted(self, key=score, reverse=True).index(team) + 1
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamsStatusList.get_team_ranking_among_list {e}")
            CubeLogger.static_error(f"creation_timestamps: {[t.creation_timestamp for t in self]}")
            return 0

    def is_valid(self):
        try:
            all_valid = all([team.is_valid() for team in self])
            # if two teams share the same create_timestamp, they're duplicates
            no_duplicates = len(set([team.creation_timestamp for team in self])) == len(self)
            if not all_valid:
                CubeLogger.static_warning("CubeTeamsStatusList.is_valid: these teams are invalid:")
                for team in self:
                    if not team.is_valid():
                        CubeLogger.static_warning(f"CubeTeamsStatusList.is_valid: {team}")
            if not no_duplicates:
                CubeLogger.static_warning("CubeTeamsStatusList.is_valid: these teams are duplicates:")
                for team in self:
                    if [t.creation_timestamp for t in self].count(team.creation_timestamp) > 1:
                        CubeLogger.static_warning(f"CubeTeamsStatusList.is_valid: {team}")
            return all_valid and no_duplicates
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamsStatusList.is_valid {e}")
            return False

    def compare_with_hashlist(self, hash_dict: Dict[TeamName, Hash]) -> Optional[Tuple[TeamName, ...]]:
        """Returns the names of the teams whose hash is different from the one in the hash_dict.
        If the returned tuple is empty, it means that the hash_dict is up-to-date with the teams list.
        If None is returned, it means that there was an error."""
        try:
            return tuple(
                [team_name for team_name, hash in hash_dict.items() if self.get_team_by_name(team_name).hash != hash])
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamsStatusList.compare_with_hashlist {e}")
            return None

    def matches_hashlist(self, hash_dict: Dict[TeamName, Hash]) -> bool:
        return self.compare_with_hashlist(hash_dict) == ()

    def reset(self):
        self.clear()

    def to_string(self) -> str:
        return self.to_json()

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self) -> Dict:
        return {
            self.JSON_ROOT_OBJECT_NAME: [team.to_dict() for team in self]
        }

    @classmethod
    def make_from_dict(cls, d: Dict) -> Optional['CubeTeamsStatusList']:
        try:
            team_list = cls()
            for team_data in d[cls.JSON_ROOT_OBJECT_NAME]:
                team_list.append(CubeTeamStatus.make_from_dict(team_data))
            return team_list
        except Exception as e:
            print(f"Error in make_from_dict: {e}")
            return None

    @classmethod
    @cubetry
    def make_from_json(cls, json_str: str) -> Optional['CubeTeamsStatusList']:
        return cls.make_from_dict(json.loads(json_str))

    @cubetry
    def add_team(self, team: CubeTeamStatus) -> bool:
        if not team.is_valid():
            return False
        if self.has_team(team):
            return False
        self.append(team)
        return True

    @cubetry
    def remove_team_by_name(self, name: str) -> bool:
        for team in self:
            if team.name == name:
                super().remove(team)
                return True
        return False

    @cubetry
    def get_team_by_rfid_uid(self, rfid_uid: str) -> Optional[CubeTeamStatus]:
        for team in self:
            if cube_rfid.CubeRfidLine.are_uids_the_same(team.rfid_uid, rfid_uid):
                return team
        return None

    @cubetry
    def get_team_by_name(self, name: str, ignore_case=True) -> Optional[CubeTeamStatus]:
        for team in self:
            if ignore_case and team.name.lower() == name.lower():
                return team
            if not ignore_case and team.name == name:
                return team
        return None

    @cubetry
    def get_team_by_current_cube_id(self, cube_id: int) -> Optional[CubeTeamStatus]:
        for team in self:
            if team.current_cubebox_id == cube_id:
                return team
        return None

    @cubetry
    def save_to_json_file(self, filename: str = None) -> bool:
        filename = filename or self.DEFAULT_JSON_FILE
        with open(filename, 'w') as f:
            f.write(self.to_json())
        return True

    def load_from_json_file(self, filename: str = None) -> bool:
        filename = filename or self.DEFAULT_JSON_FILE
        try:
            with open(filename, 'r') as f:
                data = f.read()
            self.clear()
            self.extend(CubeTeamsStatusList.make_from_json(data))
            return True
        except Exception as e:
            CubeLogger.static_error(e)
            return False

    @cubetry
    def update_team(self, team: CubeTeamStatus) -> bool:
        assert team.is_valid()
        for i, t in enumerate(self):
            if t.is_same_team_as(team):
                return self[i].update_from_team(team)
        self.append(team)
        return True

    def update_from_teams_list(self, teams_list: 'CubeTeamsStatusList') -> bool:
        try:
            for team in teams_list:
                self.update_team(team)
            return True
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamsStatusList.update_from_teams_list {e}")
            return False

    def remove_team(self, team_name: str) -> bool:
        for team in self:
            if team.name == team_name:
                self.remove(team)
                return True
        return False

    @cubetry
    def find_team_by_creation_timestamp(self, team_creation_timestamp: Timestamp) -> Optional[CubeTeamStatus]:
        epsilon = TIMESTAMP_EPSILON
        for team in self:
            if abs(team.creation_timestamp - team_creation_timestamp) < epsilon:
                return team
        return None


class CubeGameStatus:
    """Holds the statuses of all cubeboxes and all teams"""

    def __init__(self, cubeboxes: CubeboxesStatusList = None, teams: CubeTeamsStatusList = None):
        self.cubeboxes = cubeboxes or CubeboxesStatusList()
        self.teams = teams or CubeTeamsStatusList()

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except Exception as e:
            CubeLogger.static_error(f"CubeGameStatus.__eq__ {e}")
            return False

    @property
    def hash(self) -> Hash:
        try:
            return hashlib.sha256(self.to_json().encode()).hexdigest()
        except Exception as e:
            CubeLogger.static_error(f"CubeGameStatus.hash {e}")
            return ""

    def register_win(self, cube_id: int, team_name: str, win_timestamp: Seconds) -> bool:
        cubebox = self.cubeboxes.get_cubebox_by_cube_id(cube_id)
        if cubebox:
            cubebox.set_state_waiting_for_reset()
            team = self.teams.get_team_by_name(team_name)
            if team:
                team.set_completed_cube(cube_id, cubebox.start_timestamp, win_timestamp)
                return True
        return False

    def to_dict(self) -> Dict:
        return {
            CubeboxesStatusList.JSON_ROOT_OBJECT_NAME: self.cubeboxes.to_dict(),
            CubeTeamsStatusList.JSON_ROOT_OBJECT_NAME: self.teams.to_dict()
        }

    @classmethod
    def make_from_dict(cls, d: Dict) -> Optional['CubeGameStatus']:
        try:
            return cls(
                CubeboxesStatusList.make_from_dict(d.get(CubeboxesStatusList.JSON_ROOT_OBJECT_NAME)),
                CubeTeamsStatusList.make_from_dict(d.get(CubeTeamsStatusList.JSON_ROOT_OBJECT_NAME))
            )
        except Exception as e:
            CubeLogger.static_error(f"CubeGameStatus.make_from_dict {e}")
            return None

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def make_from_json(cls, json_str: str):
        try:
            return cls.make_from_dict(json.loads(json_str))
        except Exception as e:
            CubeLogger.static_error(f"CubeGameStatus.make_from_json {e}")
            return None


class CubeScoreCalculator:
    ScoringFunction = str
    SCORE_FUNCTION_LINEAR = "linear"
    VALID_SCORING_FUNCTIONS = [SCORE_FUNCTION_LINEAR]

    """Object used to configure how the score of a particular cubebox is calculated.
    The formula is : min_points + 
    """

    def __init__(self, max_score: int, max_time_sec: Seconds, min_score: int = 0,
                 scoring_function_type: ScoringFunction = SCORE_FUNCTION_LINEAR):
        try:
            self.max_time_sec = float(max_time_sec)
            self.min_score = int(min_score)
            self.max_score = int(max_score)
            self.scoring_function_type = scoring_function_type
            self.error_str = ""
        except Exception as e:
            CubeLogger.static_error(f"CubeScoreCalculator.__init__ {e}")

    def is_valid(self):
        try:
            assert isinstance(self.max_time_sec, float), f"self.max_time is not an int: {self.max_time_sec}"
            assert isinstance(self.min_score, int), f"self.min_score is not an int: {self.min_score}"
            assert isinstance(self.max_score, int), f"self.max_score is not an int: {self.max_score}"
            assert str(self.scoring_function_type) in [
                str(e) for e in
                CubeScoreCalculator.VALID_SCORING_FUNCTIONS], f"self.scoring_function_type is not a valid type: {self.scoring_function_type}"
            assert self.max_time_sec >= 0, f"self.max_time is negative: {self.max_time_sec}"
            assert self.max_score is None or self.max_score >= self.min_score, f"self.max_score is less than self.min_score: {self.max_score} < {self.min_score}"
            return True
        except Exception as e:
            self.error_str = str(e)
            return False

    @cubetry
    def to_dict(self):
        return {
            "max_time_sec": self.max_time_sec,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "scoring_function_type": self.scoring_function_type,
        }

    @classmethod
    @cubetry
    def make_from_dict(cls, d: Dict) -> Optional['CubeScoreCalculator']:
        return cls(max_time_sec=d.get("max_time_sec"),
                   min_score=d.get("min_score"),
                   max_score=d.get("max_score"),
                   scoring_function_type=d.get("scoring_function_type"),
                   )

    @cubetry
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    @cubetry
    def make_from_json(cls, json_str: str) -> Optional['CubeScoreCalculator']:
        return cls.make_from_dict(json.loads(json_str))

    def compute_score(self, time_elapsed: Seconds) -> Optional[int]:
        """the longer the time, the lower the score. min_score is the lowest possible value"""
        try:
            assert self.is_valid(), f"CubeScoreCalculator.calculate_score: invalid CubeScoreCalculator {self}"
            if time_elapsed > self.max_time_sec:
                time_elapsed = self.max_time_sec
            if self.scoring_function_type == CubeScoreCalculator.SCORE_FUNCTION_LINEAR:
                return int(self.min_score + (self.max_score - self.min_score) * (1 - time_elapsed / self.max_time_sec))
            else:
                raise ValueError(
                    f"CubeScoreCalculator.compute_score: invalid scoring function {self.scoring_function_type}")
        except Exception as e:
            CubeLogger.static_error(f"CubeScoreCalculator.calculate_score {e}")
            return None


class CubeboxesScoringPresets(Dict[ScoringPresetName, CubeScoreCalculator]):
    """A dict assigning, for each cubebox identified by its nodename, the name of the scoring preset to use"""

    JSON_ROOT_OBJECT_NAME = "cubeboxes_scoring_presets"

    def __init__(self):
        super().__init__()

    def is_valid(self):
        try:
            for preset_name, calc in self.items():
                assert isinstance(preset_name,
                                  str), f"CubeboxesScoringPresets.is_valid: preset_name is not a str: {preset_name}"
                assert isinstance(calc,
                                  CubeScoreCalculator), f"CubeboxesScoringPresets.is_valid: calc is not a CubeScoreCalculator: {calc}"
                assert calc.is_valid(), f"CubeboxesScoringPresets.is_valid: invalid CubeScoreCalculator {calc}"
            return True
        except Exception as e:
            CubeLogger.static_error(f"CubeboxesScoringPresets.is_valid {e}")
            return False

    @classmethod
    @cubetry
    def make_from_config(cls, config: CubeConfig = None) -> Optional['CubeboxesScoringPresets']:
        config = config or CubeConfig.get_config()
        ret = cls()
        dsp_dict = config.get_field(cls.JSON_ROOT_OBJECT_NAME)
        assert isinstance(dsp_dict,
                          dict), f"CubeboxesScoringPresets.make_from_config: dsp_dict is not a dict: {dsp_dict}"
        # CubeLogger.static_debug(f"CubeboxesScoringPresets.make_from_config: dsp_dict : type({type(dsp_dict)}) = {dsp_dict}")

        for preset_name, calc_dict in dsp_dict.items():
            assert isinstance(preset_name,
                              str), f"CubeboxesScoringPresets.make_from_config: preset_name is not a str: {preset_name}"
            assert isinstance(calc_dict,
                              dict), f"CubeboxesScoringPresets.make_from_config: calc_dict is not a dict: {calc_dict}"
            # CubeLogger.static_debug(f"CubeboxesScoringPresets.make_from_config: preset_name={preset_name} calc_dict={calc_dict}")
            ret[preset_name] = CubeScoreCalculator.make_from_dict(calc_dict)
            assert isinstance(ret[preset_name],
                              CubeScoreCalculator), f"CubeboxesScoringPresets.make_from_config: invalid CubeScoreCalculator {ret[preset_name]}"
            assert ret[
                preset_name].is_valid(), f"CubeboxesScoringPresets.make_from_config: invalid CubeScoreCalculator {ret[preset_name]}"
        return ret

    @cubetry
    def get_default_calculator(self) -> CubeScoreCalculator:
        return CubeScoreCalculator(
            max_score=100, max_time_sec=60.0, min_score=0,
            scoring_function_type=CubeScoreCalculator.SCORE_FUNCTION_LINEAR)

    @cubetry
    def get_calculator_by_preset_name(self, preset_name: str) -> CubeScoreCalculator:
        return self.get(preset_name)

    @cubetry
    def get_calculator_for_cube_id(self, cube_id: int, config=None) -> CubeScoreCalculator:
        config = config or CubeConfig.get_config()
        preset_name = CubeboxesScoringSettings.make_from_config(config).get_preset_name_for_cube_id(cube_id)
        return self.get_calculator_by_preset_name(preset_name)


class CubeboxesScoringSettings(Dict[CubeId, ScoringPresetName]):
    def __init__(self):
        super().__init__()
        self.clear()

    def is_valid(self):
        try:
            for cbid in cubeid.CUBEBOX_IDS:
                assert cbid in self.keys()
            assert len(self.keys()) == len(cubeid.CUBEBOX_IDS)
            return True
        except Exception as e:
            CubeLogger.static_error(f"CubeboxesScoringSettingsDict.is_valid {e}")
            return False

    @cubetry
    def get_preset_name_for_cube_id(self, cube_id: CubeId) -> ScoringPresetName:
        return self.get(cube_id)

    @classmethod
    @cubetry
    def make_from_config(cls, config: CubeConfig = None) -> 'CubeboxesScoringSettings':
        config = config or CubeConfig.get_config()
        settings_dict = config.get_field("cubeboxes_scoring_settings")
        return cls.make_from_dict(settings_dict)

    @classmethod
    @cubetry
    def make_from_dict(cls, settings_dict:Dict) -> 'CubeboxesScoringSettings':
        ret = cls()
        for str_id, preset_name in settings_dict.items():
            str_id = "".join([c for c in str_id if c in "0123456789"])
            int_id = int(str_id)
            ret[int_id] = preset_name
        return ret


def test_hashes():
    team1 = CubeTeamStatus(rfid_uid="1234567890", name="Budapest", max_time_sec=60.0)
    team1_2 = team1.copy()
    team2 = CubeTeamStatus(rfid_uid="1234567891", name="Paris", max_time_sec=60.0)
    print(f"team1 hash: {team1.hash}")
    print(f"team2 hash: {team2.hash}")
    print(f"team1_2 hash: {team1_2.hash}")
    assert team1.hash != team2.hash
    assert team1.hash == team1_2.hash

    box1 = CubeboxStatus(cube_id=1, current_team_name="Budapest", start_timestamp=1.0, win_timestamp=2.0)
    box1_2 = box1.copy()
    box2 = CubeboxStatus(cube_id=2, current_team_name="Paris", start_timestamp=1.0, win_timestamp=2.0)
    print(f"box1 hash: {box1.hash}")
    print(f"box2 hash: {box2.hash}")
    print(f"box1_2 hash: {box1_2.hash}")
    assert box1.hash != box2.hash
    assert box1.hash == box1_2.hash


def test_json():
    log = CubeLogger("test_json")
    team1 = CubeTeamStatus(rfid_uid="1234567890", name="Budapest", max_time_sec=60.0)
    team1_2 = CubeTeamStatus.make_from_json(team1.to_json())
    log.debug(f"team1.to_json()={team1.to_json()}")
    log.debug(f"team1_2.to_json()={team1_2.to_json()}")
    assert team1 == team1_2
    log.success("team1 == team1_2")

    box1 = CubeboxStatus(cube_id=1, current_team_name="Budapest", start_timestamp=1.0, win_timestamp=2.0)
    log.debug(f"box1.to_dict()={box1.to_dict()}")
    log.debug(f"box1.to_json()={box1.to_json()}")
    box1_2 = CubeboxStatus.make_from_json(box1.to_json())
    log.debug(f"box1_2.to_json()={box1_2.to_json()}")
    assert box1 == box1_2
    log.success("box1 == box1_2")

    teams_list = CubeTeamsStatusList()
    teams_list.append(team1)
    teams_list.append(CubeTeamStatus(rfid_uid="1234567891", name="Paris", max_time_sec=60.0))
    teams_list_2 = CubeTeamsStatusList.make_from_json(teams_list.to_json())
    log.debug(f"teams_list.to_json()={teams_list.to_json()}")
    log.debug(f"teams_list_2.to_json()={teams_list_2.to_json()}")
    assert teams_list == teams_list_2

    boxes_list = CubeboxesStatusList()
    boxes_list.update_from_cubebox(
        CubeboxStatus(cube_id=1, current_team_name="Budapest", start_timestamp=1.0, win_timestamp=2.0))
    boxes_list.update_from_cubebox(
        CubeboxStatus(cube_id=2, current_team_name="Paris", start_timestamp=1.0, win_timestamp=2.0))
    boxes_list_2 = CubeboxesStatusList.make_from_json(boxes_list.to_json())
    log.debug("-------------------")
    log.debug(f"boxes_list.to_json()={boxes_list.to_json()}")
    log.debug("-------------------")
    log.debug(f"boxes_list_2.to_json()={boxes_list_2.to_json()}")
    for cid in cubeid.CUBEBOX_IDS:
        if boxes_list.get_cubebox_by_cube_id(cid) != boxes_list_2.get_cubebox_by_cube_id(cid):
            log.error(f"boxes_list.get_cubebox_by_cube_id({cid}) != boxes_list_2.get_cubebox_by_cube_id({cid}):")
            log.error(f"boxes_list.get_cubebox_by_cube_id({cid})={boxes_list.get_cubebox_by_cube_id(cid)}")
            log.error(f"boxes_list_2.get_cubebox_by_cube_id({cid})={boxes_list_2.get_cubebox_by_cube_id(cid)}")
        else:
            log.success(f"boxes_list.get_cubebox_by_cube_id({cid}) == boxes_list_2.get_cubebox_by_cube_id({cid})")
    d1 = boxes_list.to_dict()
    d2 = boxes_list_2.to_dict()
    log.debug(f"d1.keys()={list(d1.keys())}")
    log.debug(f"d2.keys()={list(d2.keys())}")
    log.debug(f"d1.values() : len={len(d1.values())} ={list(d1.values())}")
    log.debug(f"d2.values() : len={len(d2.values())} ={list(d2.values())}")
    log.debug(f"d1.cubeboxes : len={len(d1['cubeboxes'])} ={d1['cubeboxes']}")
    log.debug(f"d2.cubeboxes : len={len(d2['cubeboxes'])} ={d2['cubeboxes']}")
    log.debug(f"dicts equal? {d1 == d2}")

    assert boxes_list == boxes_list_2

    log.success("All tests passed")


def test_CubeScoreCalculator():
    """test different cases with different argument composition and value, check that the expected score is the right one"""

    # test of a valid case
    max_time, min_score, max_score = 60.0, 0, 100
    calc = CubeScoreCalculator(max_time_sec=max_time, min_score=min_score, max_score=max_score)
    assert calc.is_valid()
    assert calc.compute_score(0) == max_score
    assert calc.compute_score(max_time) == min_score
    assert calc.compute_score(max_time / 2) == max_score / 2
    assert calc.compute_score(max_time * 2) == min_score

    # tests of invalid cases
    calc1 = CubeScoreCalculator(max_time_sec=-1, min_score=0, max_score=100)
    calc2 = CubeScoreCalculator(max_time_sec=60, min_score=100, max_score=0)
    calc3 = CubeScoreCalculator(max_time_sec=60, min_score=0, max_score=-1)
    calc4 = CubeScoreCalculator(max_time_sec=60, min_score=0, max_score=100, scoring_function_type="invalid")
    assert not calc1.is_valid(), f"calc1 should not be valid: {calc1}"
    assert not calc2.is_valid(), f"calc2 should not be valid: {calc2}"
    assert not calc3.is_valid(), f"calc3 should not be valid: {calc3}"
    assert not calc4.is_valid(), f"calc4 should not be valid: {calc4}"
    exit(0)


def test_ScoringPresets():
    """load the presets from the config, check that they are valid"""
    presets = CubeboxesScoringPresets.make_from_config()
    assert presets is not None
    for preset_name, calculator in presets.items():
        assert calculator.is_valid(), f"preset {preset_name} is not valid: {calculator}"

    print("All tests passed")
    exit(0)


def test_cubeboxes_scoring():
    """generates sample cubeboxes 1 to 12, then checks that the calculate_box_score method returns the expected value"""
    cubeboxes = [CubeboxStatus(cube_id=i) for i in cubeid.CUBEBOX_IDS]
    for box in cubeboxes:
        import random
        box.start_timestamp = random.uniform(0, 100)
        box.win_timestamp = random.uniform(0, 2000) + box.start_timestamp
    score_settings = CubeboxesScoringSettings.make_from_config()
    assert score_settings is not None
    defined_presets = CubeboxesScoringPresets.make_from_config()
    assert defined_presets is not None
    for box in cubeboxes:
        calc = defined_presets.get_calculator_for_cube_id(box.cube_id)
        assert calc is not None
        preset_name = score_settings.get_preset_name_for_cube_id(box.cube_id)
        assert preset_name is not None
        score = box.calculate_box_score()
        assert score is not None
        assert calc.compute_score(box.win_timestamp - box.start_timestamp) == score
        print(f"box {box.cube_id} : scoring preset = {preset_name} ; score = {score}")
    exit(0)


def test_completion_time_sec():
    """generate a few completed cubeboxes in a team, then test the box.completion_time_sec method"""
    global CUBE_TIME_METHOD
    team = CubeTeamStatus(name="Budapest", max_time_sec=60.0, rfid_uid="123456789")
    ids = [1, 4, 3, 12]
    start_times = [10, 112, 980, 450]
    win_times = [100, 350, 1020, 900]
    for i in range(len(ids)):
        team.set_completed_cube(ids[i], start_times[i], win_times[i])

    boxes = team.completed_cubeboxes
    ids_out = [box.cube_id for box in boxes]
    start_times_out = [box.start_timestamp for box in boxes]
    win_times_out = [box.win_timestamp for box in boxes]
    # check that the boxes are in the right order: the previous's win time is less than the next's start time
    for i in range(1, len(boxes)):
        assert win_times_out[i - 1] < start_times_out[
            i], f"box {i - 1} : {win_times_out[i - 1]} >= {start_times_out[i]}"

    CUBE_TIME_METHOD = CUBE_TIME_RFID_TO_PRESS
    for i in range(len(ids)):
        box = boxes[i]
        expected = win_times_out[i] - start_times_out[i]
        assert box.completion_time_sec == expected, \
            f"box {i} ({box.start_timestamp} -> {box.win_timestamp}): {box.completion_time_sec} != {expected} (expected)"

    CUBE_TIME_METHOD = CUBE_TIME_BETWEEN_PRESSES
    for i in range(len(ids)):
        box = boxes[i]
        if i == 0:
            expected = win_times_out[i] - start_times_out[i]
        else:
            expected = win_times_out[i] - win_times_out[i - 1]
        assert box.completion_time_sec == expected, \
            f"box {i} ({box.start_timestamp} -> {box.win_timestamp}): {box.completion_time_sec} != {expected} (expected)"

    print("test_completion_time_sec() : all tests passed")
    exit(0)


def generate_sample_teams() -> CubeTeamsStatusList:
    from datetime import datetime, timedelta

    teams = CubeTeamsStatusList()

    # Lists of parameters for each team
    names = ["Dakar", "Paris", "Tokyo", "New York", "London"]
    custom_names = ["Riri & Jojo", "Émile et Gégé", "Sakura & Kenji", "Mikey & John", ""]
    rfid_uids = ["1234567890", "0987654321", "1122334455", "5566778899", "6677889900"]
    max_times = [3600, 3600, 7200, 5400, 3600]
    creation_timestamps = [
        datetime(2024, 5, 20, 12, 34, 56).timestamp(),  # a few weeks ago
        datetime(2024, 5, 21, 12, 34, 56).timestamp(),  # a few weeks ago
        (datetime.now() - timedelta(days=5)).timestamp(),  # 5 days ago
        (datetime.now() - timedelta(days=30)).timestamp(),  # 1 month ago
        (datetime.now() - timedelta(days=90)).timestamp()  # 3 months ago
    ]
    start_timestamps = [
        datetime(2024, 5, 21, 12, 40, 20).timestamp(),
        datetime(2024, 5, 22, 12, 55, 0).timestamp(),
        (datetime.now() - timedelta(days=4)).timestamp(),
        (datetime.now() - timedelta(days=29)).timestamp(),
        (datetime.now() - timedelta(days=89)).timestamp()
    ]
    completed_cubeboxes_list = [
        [
            CubeboxStatus(cube_id=1, start_timestamp=0, win_timestamp=1000),
            CubeboxStatus(cube_id=2, start_timestamp=1000, win_timestamp=2000),
        ],
        [
            CubeboxStatus(cube_id=3, start_timestamp=0, win_timestamp=1000),
            CubeboxStatus(cube_id=4, start_timestamp=1000, win_timestamp=2000),
            CubeboxStatus(cube_id=5, start_timestamp=2000, win_timestamp=3000),
        ],
        [
            CubeboxStatus(cube_id=6, start_timestamp=0, win_timestamp=1000),
            CubeboxStatus(cube_id=7, start_timestamp=1000, win_timestamp=2000),
        ],
        [
            CubeboxStatus(cube_id=8, start_timestamp=0, win_timestamp=1000),
            CubeboxStatus(cube_id=9, start_timestamp=1000, win_timestamp=2000),
            CubeboxStatus(cube_id=10, start_timestamp=2000, win_timestamp=3000),
        ],
        [
            CubeboxStatus(cube_id=11, start_timestamp=0, win_timestamp=1000),
            CubeboxStatus(cube_id=12, start_timestamp=1000, win_timestamp=2000),
        ]
    ]
    # get the list of valid trophies from the config, and make a list, for each teams,
    # of 0 to 4 random trophies
    valid_trophies: List[CubeTrophy] = list(CubeConfig.get_config().defined_trophies)
    valid_trophy_names = [x.name for x in valid_trophies]
    print(f"valid_trophy_names={valid_trophy_names}")
    trophies_names_list = []
    for i in range(len(names)):
        trophies_names = random.sample(valid_trophy_names, k=random.randint(0, min(4, len(valid_trophy_names))))
        trophies_names_list.append(trophies_names)
    print(f"trophies_names_list={trophies_names_list}")
    # Loop to add teams
    for name, custom_name, rfid_uid, max_time, creation_timestamp, start_timestamp, completed_cubeboxes, trophies_names in zip(
            names, custom_names, rfid_uids, max_times, creation_timestamps, start_timestamps, completed_cubeboxes_list,
            trophies_names_list
    ):
        completed_cubeboxes = CompletedCubeboxStatusList(completed_cubeboxes)
        # print(f"----- completed_cubeboxes={completed_cubeboxes}")
        team = CubeTeamStatus(
            name=name,
            custom_name=custom_name,
            rfid_uid=rfid_uid,
            max_time_sec=max_time,
            creation_timestamp=creation_timestamp,
            start_timestamp=start_timestamp,
            completed_cubeboxes=completed_cubeboxes,
            trophies_names=trophies_names
        )
        # print(f"----- team={team}")
        # OK so far
        teams.add_team(team)
        # print(teams[-1]._completed_cubeboxes)

    if not teams.is_valid():
        print("Error: teams are not valid")
        exit(1)

    print(f"Generated teams: {teams}")
    return teams

def test_custom_name():
    team = CubeTeamStatus(name="Budapest", max_time_sec=60.0, rfid_uid="123456789")
    assert team.custom_name == "Budapest", f"team.custom_name='{team.custom_name}'"
    team = CubeTeamStatus(name="Paris", custom_name="A"*40, max_time_sec=60.0, rfid_uid="123456789")
    assert team.custom_name == "A"*CubeTeamStatus.CUSTOM_NAME_MAX_LENGTH, f"team.custom_name='{team.custom_name}'"
    exit(0)

if __name__ == "__main__":
    test_custom_name()
    import thecubeivazio.cube_database as cubedb

    database = cubedb.CubeDatabase(FRONTDESK_SQLITE_DATABASE_FILEPATH)
    database.generate_sample_teams_sqlite_database()
    test_completion_time_sec()
    test_cubeboxes_scoring()
    test_ScoringPresets()
    test_CubeScoreCalculator()
    test_hashes()
    test_json()
