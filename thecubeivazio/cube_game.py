"""Modelises a TheCube game session, i.e. a team trying to open a CubeBox"""
import enum
import json
import time
from typing import List, Optional, Dict, Tuple, Iterable
import pickle

from thecubeivazio.cube_common_defines import *
from thecubeivazio import cube_identification as cubeid
from thecubeivazio import cube_utils
import thecubeivazio.cube_rfid as cube_rfid

# todo: use seconds and timestamps from cube_common_defines
from thecubeivazio.cube_common_defines import *
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
    EASY_CUBES = (1, 2, 3, 4)
    MEDIUM_CUBES = (5, 6, 7, 8)
    HARD_CUBES = (9, 10, 11, 12)
    MAX_SCORE = 300
    EASY_MIN_TIME = 5 * 60
    MEDIUM_MIN_TIME = 8 * 60
    HARD_MIN_TIME = 12 * 60

    # TODO: set unknown state as the default
    def __init__(self, cube_id: CubeId = None, current_team_name: TeamName = None, starting_timestamp: Seconds = None,
                 win_timestamp: Seconds = None, last_valid_rfid_line: cube_rfid.CubeRfidLine = None,
                 state: CubeboxState = CubeboxState.STATE_READY_TO_PLAY):
        self.cube_id: Optional[CubeId] = cube_id
        self.current_team_name: Optional[TeamName] = None
        self.starting_timestamp: Optional[Seconds] = None
        self.win_timestamp: Optional[Seconds] = None
        self.last_valid_rfid_line: Optional[cube_rfid.CubeRfidLine] = None
        self._state = state

    def __str__(self):
        return self.to_string()

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.__eq__ {e}")
            return False


    def is_valid(self):
        """if this function returns False, then it might have been made from corrupted data"""
        return all((self.cube_id in cubeid.CUBEBOX_IDS, self._state in CubeboxState))

    @property
    def hash(self) -> Hash:
        import hashlib
        return hashlib.sha256(self.to_string().encode()).hexdigest()

    def __repr__(self):
        ret = f"CubeboxStatus({self.to_string()}, last_valid_rfid_line={self.last_valid_rfid_line})"

    def to_string(self) -> str:
        sep = ","
        return sep.join([f"{k}={v}" for k, v in self.to_dict().items()])

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def make_from_json(cls, json_str:str):
        try:
            return cls.make_from_dict(json.loads(json_str))
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.make_from_json {e.with_traceback()}")
            return None

    def to_dict(self) -> Dict:
        return {
            "cube_id": self.cube_id,
            "current_team_name": self.current_team_name,
            "starting_timestamp": self.starting_timestamp,
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
            ret.starting_timestamp = d.get("starting_timestamp",None)
            if ret.starting_timestamp is not None:
                ret.starting_timestamp = float(ret.starting_timestamp)
            ret.win_timestamp = d.get("win_timestamp", None)
            if ret.win_timestamp is not None:
                ret.win_timestamp = float(ret.win_timestamp)
            # skip the rfid line. it will not be useful for whomever asks for it
            # ret.last_valid_rfid_line = cube_rfid.CubeRfidLine.make_from_string(kwargs.get("last_valid_rfid_line"))
            ret._state = CubeboxState(d.get("state"))
            return ret
        except Exception as e:
            CubeLogger.static_error(f"CubeboxStatus.make_from_dict {e.with_traceback()}")
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
        self.current_team_name = None
        self.starting_timestamp = None
        self.win_timestamp = None
        self._state = CubeboxState.STATE_READY_TO_PLAY

    def set_state_playing(self, team_name: str = None, start_timestamp: Seconds = None):
        self.current_team_name = team_name
        self.starting_timestamp = start_timestamp
        self.win_timestamp = None
        self._state = CubeboxState.STATE_PLAYING

    # obsolete
    def reset(self):
        self.set_state_ready_to_play()

    def set_state_waiting_for_reset(self):
        self._state = CubeboxState.STATE_WAITING_FOR_RESET

    def copy(self) -> 'CubeboxStatus':
        ret = CubeboxStatus(self.cube_id)
        ret.build_from_copy(self)
        return ret

    def build_from_copy(self, other: 'CubeboxStatus'):
        self.cube_id = other.cube_id
        self.current_team_name = other.current_team_name
        self.starting_timestamp = other.starting_timestamp
        self.win_timestamp = other.win_timestamp
        self.last_valid_rfid_line = other.last_valid_rfid_line
        self._state = other.get_state()

    @property
    def completion_time_sec(self) -> Optional[Seconds]:
        if self.starting_timestamp is None or self.win_timestamp is None:
            return None
        return self.win_timestamp - self.starting_timestamp

    @property
    def completion_time_str(self) -> str:
        completion_time = self.completion_time_sec
        if completion_time is None:
            return "N/A"
        return cube_utils.seconds_to_hhmmss_string(completion_time)

    def calculate_score(self) -> Optional[int]:
        try:
            cts = self.completion_time_sec
            cube_id = self.cube_id
            if cube_id in CubeboxStatus.EASY_CUBES:
                return CubeboxStatus.MAX_SCORE if cts < CubeboxStatus.EASY_MIN_TIME else int(
                    CubeboxStatus.EASY_MIN_TIME - 1 / 3 * (cts - CubeboxStatus.EASY_MIN_TIME))
            elif cube_id in CubeboxStatus.MEDIUM_CUBES:
                return CubeboxStatus.MAX_SCORE if cts < CubeboxStatus.MEDIUM_MIN_TIME else int(
                    CubeboxStatus.MEDIUM_MIN_TIME - 1 / 3 * (cts - CubeboxStatus.MEDIUM_MIN_TIME))
            elif cube_id in CubeboxStatus.HARD_CUBES:
                return CubeboxStatus.MAX_SCORE if cts < CubeboxStatus.HARD_MIN_TIME else int(
                    CubeboxStatus.HARD_MIN_TIME - 1 / 3 * (cts - CubeboxStatus.HARD_MIN_TIME))
            else:
                return 0
        except Exception as e:
            print(e)
            return None


# an alias just for clarity, we'll use this one to refer exclusively to completed cubeboxes
CompletedCubeboxStatus = CubeboxStatus
CompletedCubeboxStatus.__doc__ = "Represents a CubeBox that has been successfully played by a team"


class CubeboxesStatusList(List[CubeboxStatus]):
    """List of CubeGame instances, one for each CubeBox in TheCube game. Meant to be used by the CubeMaster and FrontDesk."""
    SEPARATOR = ";"
    JSON_ROOT_OBJECT_NAME = "cubeboxes"

    def __init__(self, cubeboxes:Optional[List[CubeboxStatus]]=None):
        super().__init__()
        self.reset()
        if cubeboxes:
            self.update_from_cubeboxes(cubeboxes)

    def update_from_cubeboxes(self, cubeboxes: Iterable[CubeboxStatus]):
        for box in cubeboxes:
            self.update_cubebox(box)

    def extend(self, cubeboxes_list:Iterable[CubeboxStatus]):
        self.update_from_cubeboxes(cubeboxes_list)

    def append(self, box:CubeboxStatus):
        self.update_cubebox(box)

    @property
    def hash_dict(self) -> Dict[NodeName, Hash]:
        return {cubeid.cubebox_index_to_node_name(box.cube_id): box.hash for box in self}

    def compare_with_hashlist(self, hash_dict: Dict[NodeName, Hash]) -> Optional[Tuple[NodeName,...]]:
        """Returns the names of the teams whose hash is different from the one in the hash_dict.
        If the returned tuple is empty, it means that the hash_dict is up-to-date with the teams list.
        If None is returned, it means that there was an error."""
        try:
            return tuple([node_name for node_name, hash in hash_dict.items() if hash != self.get_cubebox_by_node_name(node_name).hash])
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
        sep = self.SEPARATOR
        return sep.join([box.to_string() for box in self])

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self) -> Dict:
        return {
            self.JSON_ROOT_OBJECT_NAME : [box.to_dict() for box in self]
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
                ret.update_cubebox(CubeboxStatus.make_from_dict(box_data))
            return ret
        except Exception as e:
            CubeLogger.static_error(f"CubeboxesStatusList.make_from_dict {e.with_traceback()}")
            return None

    @classmethod
    def make_from_json(cls, json_str:str):
        try:
            return cls.make_from_dict(json.loads(json_str))
        except Exception as e:
            CubeLogger.static_error(f"CubeboxesStatusList.make_from_json {e}")
            return None

    @classmethod
    def make_from_kwargs(cls, **kwargs):
        return cls.make_from_dict(kwargs)

    def update_cubebox(self, cubebox: CubeboxStatus) -> bool:
        if not cubebox:
            return False
        for box in self:
            if box.cube_id == cubebox.cube_id:
                box.build_from_copy(cubebox)
                return True
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

    def reset(self):
        self.clear()
        super().extend([CubeboxStatus(cube_id) for cube_id in cubeid.CUBEBOX_IDS])

    def free_cubes(self) -> List[CubeId]:
        return [box.cube_id for box in self if box.is_ready_to_play()]

    def played_cubes(self) -> List[int]:
        return [box.cube_id for box in self if not box.is_ready_to_play()]


class CubeTeamTrophy:
    """Represents a trophy that a team can win by playing a CubeGame"""

    def __init__(self, name: str, description: str, points: int, image_path: str=None):
        self.name = name
        self.description = description
        self.points = points
        self.image_path = image_path
        if image_path is not None:
            self.image_path = DEFAULT_TROPHY_IMAGE_FILENAME

    def to_string(self):
        sep = ","
        return sep.join([f"{k}={v}" for k, v in self.to_dict().items()])

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return f"CubeTrophy({self.to_string()})"

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamTrophy.__eq__ {e}")
            return False

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "points": self.points,
            "image_path": self.image_path
        }

    @classmethod
    def make_from_dict(cls, d: Dict) -> Optional['CubeTeamTrophy']:
        try:
            return cls(d.get("name"),
                       d.get("description"),
                       int(d.get("points")),
                       d.get("image_path", None))
        except Exception as e:
            print(e)
            return None


class CubeTeamStatus:
    """Represents a team playing a CubeGame"""

    def __init__(self, name: str, rfid_uid: str, max_time_sec: Seconds, custom_name: str = "",
                 starting_timestamp: Seconds = None, current_cubebox_id: int = None,
                 completed_cubeboxes: List[CompletedCubeboxStatus] = None,
                 trophies: List[CubeTeamTrophy] = None):
        # the team's code name (a city name)
        self.name = name
        # the custom names chosen by the customers
        self.custom_name = custom_name
        # the RFID UID of the team
        self.rfid_uid = rfid_uid
        # the maximum time allowed to play the CubeGame
        self.max_time_sec: Seconds = max_time_sec
        # the time when the team starts playing its first cubebox
        self.starting_timestamp: Optional[Seconds] = None
        # the cubebox ID currently being played by the team
        self.current_cubebox_id: Optional[CubeId] = None
        # the list of the cubeboxes IDs that the team has successfully played, with their completion times
        self.completed_cubeboxes: List[CompletedCubeboxStatus] = []
        # the trophies collected by the team, awarded by the frontdesk
        self.trophies: List[CubeTeamTrophy] = []

    def __eq__(self, other):
        try:
            return self.to_dict() == other.to_dict()
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.__eq__ {e}")
            return False

    def __repr__(self):
        ret = f"CubeTeam({self.to_string()})"

    def __str__(self):
        return self.to_string()

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "custom_name": self.custom_name,
            "rfid_uid": self.rfid_uid,
            "max_time_sec": self.max_time_sec,
            "starting_timestamp": self.starting_timestamp,
            "current_cubebox_id": self.current_cubebox_id,
            "completed_cubeboxes": [box.to_dict() for box in self.completed_cubeboxes]
        }

    @classmethod
    def make_from_dict(cls, d: Optional[Dict]) -> Optional['CubeTeamStatus']:
        # CubeLogger.static_debug(f"CubeTeamStatus.make_from_dict {d}")
        try:
            ret = cls(d.get("name"), d.get("rfid_uid"), d.get("max_time_sec"))
            ret.custom_name = d.get("custom_name", "")
            ret.starting_timestamp = d.get("starting_timestamp", None)
            if ret.starting_timestamp is not None:
                ret.starting_timestamp = float(ret.starting_timestamp)
            ret.current_cubebox_id = d.get("current_cubebox_id", None)
            if ret.current_cubebox_id is not None:
                ret.current_cubebox_id = int(ret.current_cubebox_id)
            ret.completed_cubeboxes = [
                CompletedCubeboxStatus.make_from_dict(box) for box in d.get("completed_cubeboxes", [])]
            ret.trophies = [
                CubeTeamTrophy.make_from_dict(trophy) for trophy in d.get("trophies", [])]
            return ret
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.make_from_dict {e}")
            return None


    @classmethod
    def make_from_kwargs(cls, **kwargs) -> Optional['CubeTeamStatus']:
        return cls.make_from_dict(kwargs)


    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def make_from_json(cls, json_str:Optional[str]):
        try:
            d = json.loads(json_str)
            return cls.make_from_dict(d)
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.make_from_json {e}")
            return None

    def to_string(self) -> Optional[str]:
        sep = ","
        try:
            return sep.join([f"{k}={v}" for k, v in self.to_dict().items()])
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.make_from_string {e}")
            return None

    @staticmethod
    def make_from_string(line:Optional[str]) -> Optional['CubeTeamStatus']:
        try:
            kwargs = {}
            for part in line.split(","):
                key, value = part.split("=")
                kwargs[key.strip()] = value.strip()
            return CubeTeamStatus.make_from_kwargs(**kwargs)
        except Exception as e:
            CubeLogger.static_error(f"CubeTeamStatus.make_from_string {e}")
            return None

    @property
    def completed_cubebox_ids(self) -> List[CubeId]:
        return [box.cube_id for box in self.completed_cubeboxes]

    @property
    def hash(self) -> Hash:
        import hashlib
        return hashlib.sha256(self.to_string().encode()).hexdigest()

    # TODO: test
    def is_time_up(self, current_time: Seconds = None) -> bool:
        if current_time is None:
            current_time = time.time()
        return current_time - self.starting_timestamp > self.max_time_sec

    # TODO: test
    def has_played_today(self, current_time: Seconds = None) -> bool:
        if current_time is None:
            current_time = time.time()
        return any(
            [box.win_timestamp > cube_utils.timestamps_are_in_same_day(self.starting_timestamp, current_time) for box in
             self.completed_cubeboxes])

    # TODO: test
    def has_played_this_week(self, current_time: Seconds = None) -> bool:
        if current_time is None:
            current_time = time.time()
        return any(
            [box.win_timestamp > cube_utils.timestamps_are_in_same_week(self.starting_timestamp, current_time) for box
             in self.completed_cubeboxes])

    # TODO: test
    def has_played_this_month(self, current_time: Seconds = None) -> bool:
        if current_time is None:
            current_time = time.time()
        return any(
            [box.win_timestamp > cube_utils.timestamps_are_in_same_month(self.starting_timestamp, current_time) for box
             in self.completed_cubeboxes])

    # TODO: test
    def has_completed_cube(self, cube_id: int) -> bool:
        return cube_id in [box.cube_id for box in self.completed_cubeboxes]

    # TODO: test
    def set_completed_cube(self, cube_id: int, start_timestamp: float, win_timestamp: float) -> bool:
        if self.has_completed_cube(cube_id):
            return False
        self.completed_cubeboxes.append(CompletedCubeboxStatus(
            cube_id=cube_id, current_team_name=self.name, starting_timestamp=start_timestamp,
            win_timestamp=win_timestamp))
        return True

    def has_started(self) -> bool:
        return self.starting_timestamp is not None

    def calculate_score(self) -> int:
        """Calculate the total score of the team, based on the completion times of the cubeboxes it has played."""
        # memo: cid means cube_id, cts means completion_time_sec
        return sum([box.calculate_score() for box in self.completed_cubeboxes])

    def generate_raw_score_sheet(self) -> str:
        ret = f"Équipe {self.name} : {self.calculate_score()} points\n"
        for box in self.completed_cubeboxes:
            ret += f"Cube {box.cube_id} : {box.completion_time_str} : {box.calculate_score()} points\n"
        return ret

    def save_markdown_score_sheet(self) -> bool:
        # if the scoresheet folder is not present, create it
        if not os.path.exists(SCORESHEETS_DIR):
            os.makedirs(SCORESHEETS_DIR)
        filename = os.path.join(SCORESHEETS_DIR, f"{self.name}_scoresheet.md")
        text = f"# Équipe {self.name}\n\n"
        text += f"**Total Score:** {self.calculate_score()} points\n\n"
        text += "## Completed Cubes\n\n"
        for cube in self.completed_cubeboxes:
            text += f"- **Cube {cube.cube_id}:** {cube.completion_time_str} - {cube.calculate_score()} points\n"
        try:
            with open(filename, 'w') as f:
                f.write(text)
            return True
        except Exception as e:
            print(e)
            return False

    # TODO: testme
    def save_html_score_sheet(self) -> bool:
        # if the scoresheet folder is not present, create it
        if not os.path.exists(SCORESHEETS_DIR):
            os.makedirs(SCORESHEETS_DIR)
        filename = os.path.join(SCORESHEETS_DIR, f"{self.name}_scoresheet.html")
        content = f"<h1>Équipe {self.name}</h1>\n\n"
        content += f"<p><strong>Date:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>\n\n"
        content += f"<p><strong>Temps alloué:</strong> {cube_utils.seconds_to_hhmmss_string(self.max_time_sec)}</p>\n\n"
        content += f"<p><strong>Score total:</strong> {self.calculate_score()} points</p>\n\n"
        content += "<h2>Score détaillé</h2>\n\n"
        content += "<ul>\n"
        for cube in self.completed_cubeboxes:
            content += f"<li><strong>Cube {cube.cube_id} : </strong> {cube.completion_time_str} - {cube.calculate_score()} points</li>\n"
        content += "</ul>\n"
        content = "<center>\n" + content + "</center>\n"
        html = f"<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n<title>Ivazio - The Cube</title>\n<link rel='stylesheet' type='text/css' href='../resources/scoresheet_style.css'>\n</head>\n<body>\n{content}\n</body>\n</html>"

        try:
            with open(filename, 'w', encoding="utf-8") as f:
                f.write(html)
            return True
        except Exception as e:
            print(e)
            return False

    def copy(self):
        ret = CubeTeamStatus(self.name, self.rfid_uid, self.max_time_sec)
        ret.current_cubebox_id = self.current_cubebox_id
        ret.starting_timestamp = self.starting_timestamp
        ret.completed_cubeboxes = [box.copy() for box in self.completed_cubeboxes]
        return ret

    def resign_current_cube(self):
        # TODO: do we need to actually do something more here?
        self.current_cubebox_id = None

    def has_played_cube(self, cubebox_id):
        return cubebox_id in [box.cube_id for box in self.completed_cubeboxes]

    def is_same_team_as(self, team):
        """Returns True if the team has the same name, custom_name, RFID UID, and starting timestamp as the other team.
        Any other difference could simply mean that the team has been updated."""
        return all((self.name == team.name, self.custom_name == team.custom_name, self.rfid_uid == team.rfid_uid,
                    self.starting_timestamp == team.starting_timestamp))

    def update_from_team(self, team):
        """If this team is the same as the other team, update its data with the other team's data,
        preserving the completed cubeboxes and trophies
        If this is another team, return False"""
        if self.is_same_team_as(team):
            for completed_cube in team.completed_cubeboxes:
                self.set_completed_cube(completed_cube.cube_id, completed_cube.starting_timestamp,
                                        completed_cube.win_timestamp)
            for trophy in team.trophies:
                self.add_trophy(trophy)
            self.current_cubebox_id = team.current_cubebox_id
            return True
        else:
            return False

    def add_trophy(self, trophy: CubeTeamTrophy):
        if not trophy in self.trophies:
            self.trophies.append(trophy)

    def is_valid(self):
        """if this function returns False, then it might have been made from corrupted data"""
        return all((self.name, self.rfid_uid, self.max_time_sec))


# TODO : add ranks for the day, week, mont, all-time
class CubeTeamsStatusList(List[CubeTeamStatus]):
    """List of CubeTeam instances, one for each team playing a CubeGame. Meant to be used by the CubeMaster and FrontDesk."""

    DEFAULT_PICKLE_FILE = "cube_teams_list.pkl"
    DEFAULT_JSON_FILE = "cube_teams_list.json"
    JSON_ROOT_OBJECT_NAME = "teams"

    def __init__(self, teams:Optional[List[CubeTeamStatus]]=None):
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

    def compare_with_hashlist(self, hash_dict: Dict[TeamName, Hash]) -> Optional[Tuple[TeamName,...]]:
        """Returns the names of the teams whose hash is different from the one in the hash_dict.
        If the returned tuple is empty, it means that the hash_dict is up-to-date with the teams list.
        If None is returned, it means that there was an error."""
        try:
            return tuple([team_name for team_name, hash in hash_dict.items() if self.get_team_by_name(team_name).hash != hash])
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
    def make_from_json(cls, json_str:str):
        try:
            return cls.make_from_dict(json.loads(json_str))
        except Exception as e:
            print(e)
            return None

    def add_team(self, team: CubeTeamStatus) -> bool:
        if self.get_team_by_name(team.name) is not None:
            return False
        self.append(team)
        return True

    def remove_team_by_name(self, name: str) -> bool:
        for team in self:
            if team.name == name:
                self.remove(team)
                return True
        return False

    def get_team_by_rfid_uid(self, rfid_uid: str) -> Optional[CubeTeamStatus]:
        for team in self:
            if team.rfid_uid == rfid_uid:
                return team
        return None

    def get_team_by_name(self, name: str) -> Optional[CubeTeamStatus]:
        for team in self:
            if team.name == name:
                return team
        return None

    def get_team_by_current_cube_id(self, cube_id: int) -> Optional[CubeTeamStatus]:
        for team in self:
            if team.current_cubebox_id == cube_id:
                return team
        return None

    # TODO: testme
    def save_to_pickle(self, filename=None) -> bool:
        if filename is None:
            filename = self.DEFAULT_PICKLE_FILE
        try:
            with open(filename, 'wb') as f:
                pickle.dump(self, f)
            return True
        except Exception as e:
            print(e)
            return False

    # TODO: testme
    def load_from_pickle(self, filename=None) -> bool:
        if filename is None:
            filename = self.DEFAULT_PICKLE_FILE
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
            self.clear()
            self.extend(data)
            return True
        except Exception as e:
            print(e)
            self.reset()
            return False

    # TODO: testme
    def save_to_json_file(self, filename:str=None) -> bool:
        filename = filename or self.DEFAULT_JSON_FILE
        try:
            with open(filename, 'w') as f:
                f.write(self.to_json())
            return True
        except Exception as e:
            CubeLogger.static_error(e)
            return False

    # TODO: testme
    def load_from_json_file(self, filename:str=None) -> bool:
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


    # TODO: testme
    def update_team(self, team: CubeTeamStatus) -> bool:
        for i, t in enumerate(self):
            if t.is_same_team_as(team):
                return self[i].update_from_team(team)
            else:
                self.append(team)
                return True
        return False

    def update_from_teams_list(self, teams_list: 'CubeTeamsStatusList'):
        for team in teams_list:
            self.update_team(team)

    def remove_team(self, team_name: str) -> bool:
        for team in self:
            if team.name == team_name:
                self.remove(team)
                return True
        return False


def test_cube_team():
    team = CubeTeamStatus(rfid_uid="1234567890", name="Budapest", max_time_sec=60.0)
    assert team.rfid_uid == "1234567890"
    assert team.name == "Budapest"
    assert team.max_time_sec == 60.0
    assert not team.has_started()
    assert not team.is_time_up()
    team.starting_timestamp = time.time()
    assert team.has_started()
    assert not team.is_time_up()
    team.max_time_sec = 0.1
    assert team.is_time_up()
    team.completed_cubeboxes.append(
        CubeboxStatus(cube_id=1, starting_timestamp=time.time(), win_timestamp=time.time() + 1))
    assert team.calculate_score() == 300
    assert team.generate_raw_score_sheet() == "Équipe Budapest : 300 points\nCube 1 : 00:00:01 : 300 points\n"
    assert team.save_markdown_score_sheet()
    assert team.save_html_score_sheet()


def test_cube_teams_list():
    teams_list = CubeTeamsStatusList()
    assert len(teams_list) == 0
    team1 = CubeTeamStatus(rfid_uid="1234567890", name="Budapest", max_time_sec=60.0)
    team2 = CubeTeamStatus(rfid_uid="1234567891", name="Paris", max_time_sec=60.0)
    assert teams_list.add_team(team1)
    assert len(teams_list) == 1
    assert teams_list.add_team(team2)
    assert len(teams_list) == 2
    assert not teams_list.add_team(team1)
    assert len(teams_list) == 2
    assert teams_list.get_team_by_rfid_uid("1234567890") == team1
    assert teams_list.get_team_by_name("Budapest") == team1
    assert teams_list.get_team_by_rfid_uid("1234567891") == team2
    assert teams_list.get_team_by_name("Paris") == team2
    assert teams_list.get_team_by_rfid_uid("1234567892") is None
    assert teams_list.get_team_by_name("London") is None
    assert teams_list.remove_team_by_name("Paris")
    assert len(teams_list) == 1
    assert not teams_list.remove_team_by_name("Paris")
    assert len(teams_list) == 1
    assert teams_list.remove_team_by_name("Budapest")
    assert len(teams_list) == 0
    assert not teams_list.remove_team_by_name("Budapest")
    assert len(teams_list) == 0
    # test pickle
    assert teams_list.save_to_pickle()
    teams_list.append(team1)
    assert len(teams_list) == 1
    assert teams_list.load_from_pickle()
    assert len(teams_list) == 0
    assert teams_list.get_team_by_rfid_uid("1234567890") == team1
    assert teams_list.get_team_by_name("Budapest") == team1
    assert teams_list.remove_team_by_name("Budapest")
    assert len(teams_list) == 0
    assert not teams_list.load_from_pickle("foo")
    assert len(teams_list) == 0


def save_scoresheet():
    team = CubeTeamStatus(rfid_uid="1234567890", name="Budapest", max_time_sec=60.0)
    team.completed_cubeboxes.append(
        CubeboxStatus(cube_id=1, starting_timestamp=time.time(), win_timestamp=time.time() + 1150))
    team.completed_cubeboxes.append(
        CubeboxStatus(cube_id=2, starting_timestamp=time.time(), win_timestamp=time.time() + 200))
    team.save_html_score_sheet()


def test_hashes():
    team1 = CubeTeamStatus(rfid_uid="1234567890", name="Budapest", max_time_sec=60.0)
    team1_2 = team1.copy()
    team2 = CubeTeamStatus(rfid_uid="1234567891", name="Paris", max_time_sec=60.0)
    print(f"team1 hash: {team1.hash}")
    print(f"team2 hash: {team2.hash}")
    print(f"team1_2 hash: {team1_2.hash}")
    assert team1.hash != team2.hash
    assert team1.hash == team1_2.hash

    box1 = CubeboxStatus(cube_id=1, current_team_name="Budapest", starting_timestamp=1.0, win_timestamp=2.0)
    box1_2 = box1.copy()
    box2 = CubeboxStatus(cube_id=2, current_team_name="Paris", starting_timestamp=1.0, win_timestamp=2.0)
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

    box1 = CubeboxStatus(cube_id=1, current_team_name="Budapest", starting_timestamp=1.0, win_timestamp=2.0)
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
    boxes_list.update_cubebox(CubeboxStatus(cube_id=1, current_team_name="Budapest", starting_timestamp=1.0, win_timestamp=2.0))
    boxes_list.update_cubebox(CubeboxStatus(cube_id=2, current_team_name="Paris", starting_timestamp=1.0, win_timestamp=2.0))
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


if __name__ == "__main__":
    # test_hashes()
    test_json()
    exit(0)

    teams_list = CubeTeamsStatusList()
    teams_list.append(CubeTeamStatus(name="Budapest", custom_name="FooCustomName",
                                     rfid_uid="123456789", max_time_sec=60.0))
    teams_list.append(CubeTeamStatus(name="Paris", custom_name="BarCustomName",
                                     rfid_uid="987654321", max_time_sec=60.0))
    team1 = teams_list.get_team_by_name("Budapest")
    team1.trophies.append(
        CubeTeamTrophy(name="FooTrophy", description="FooDescription", points=100, image_path="foo.png"))
    team1.trophies.append(
        CubeTeamTrophy(name="BarTrophy", description="BarDescription", points=200, image_path="bar.png"))
    print(teams_list)
