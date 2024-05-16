"""Modelises a TheCube game session, i.e. a team trying to open a CubeBox"""
import time
from dataclasses import dataclass
from typing import List, Optional, Dict
import pickle
import os


from thecubeivazio import cube_identification as cubeid
from thecubeivazio import cube_utils
# todo: use seconds and timestamps from cube_common_defines
from thecubeivazio.cube_common_defines import *

class CubeboxStatus:
    """Represents a game session, i.e. a team trying to open a CubeBox"""
    EASY_CUBES = (1, 2, 3, 4)
    MEDIUM_CUBES = (5, 6, 7, 8)
    HARD_CUBES = (9, 10, 11, 12)
    MAX_SCORE = 300
    EASY_MIN_TIME = 5 * 60
    MEDIUM_MIN_TIME = 8 * 60
    HARD_MIN_TIME = 12 * 60

    def __init__(self, cube_id: int, current_team_name: Optional[str] = None, starting_timestamp: Optional[float] = None, victory_timestamp: Optional[float] = None):
        self.cube_id = cube_id
        self.current_team_name = current_team_name
        self.starting_timestamp = starting_timestamp
        self.win_timestamp = victory_timestamp

    def copy(self) -> 'CubeboxStatus':
        return CubeboxStatus(self.cube_id, self.current_team_name, self.starting_timestamp, self.win_timestamp)

    def build_from_copy(self, other: 'CubeboxStatus'):
        self.cube_id = other.cube_id
        self.current_team_name = other.current_team_name
        self.starting_timestamp = other.starting_timestamp
        self.win_timestamp = other.win_timestamp

    def to_string(self) -> str:
        return f"CubeBoxGame {self.cube_id}: team={self.current_team_name}, start={self.starting_timestamp}, victory={self.win_timestamp}"

    def reset(self):
        self.current_team_name = None
        self.starting_timestamp = None
        self.win_timestamp = None

    def is_free(self) -> bool:
        return self.current_team_name is None and self.starting_timestamp is None and self.win_timestamp is None

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

    def calculate_score(self) -> int:
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

    def is_playing(self):
        return not self.is_free()

# an alias just for clarity, we'll use this one to refer exclusively to completed cubeboxes
CompletedCubeboxStatus = CubeboxStatus


class CubeboxStatusList(List[CubeboxStatus]):
    """List of CubeGame instances, one for each CubeBox in TheCube game. Meant to be used by the CubeMaster and FrontDesk."""

    def __init__(self):
        super().__init__()
        self.reset()

    def to_string(self) -> str:
        ret = f"CubeboxStatusList : {len(self)} boxes\n"
        for box in self:
            ret += f"  {box.to_string()}\n"
        return ret

    def update_cubebox(self, cubebox:CubeboxStatus) -> bool:
        for box in self:
            if box.cube_id == cubebox.cube_id:
                box.build_from_copy(cubebox)
                return True
        return False

    def find_cubebox_by_cube_id(self, cubebox_id: int) -> Optional[CubeboxStatus]:
        for box in self:
            if box.cube_id == cubebox_id:
                return box
        return None

    def find_cubebox_by_node_name(self, node_name: str) -> Optional[CubeboxStatus]:
        for box in self:
            if cubeid.node_name_to_cubebox_index(node_name) == box.cube_id:
                return box
        return None

    def reset(self):
        self.clear()
        self.extend([CubeboxStatus(cube_id) for cube_id in cubeid.CUBEBOX_IDS])

    def free_cubes(self) -> List[int]:
        return [box.cube_id for box in self if box.is_free()]

    def played_cubes(self) -> List[int]:
        return [box.cube_id for box in self if not box.is_free()]


class CubeTeamStatus:
    """Represents a team playing a CubeGame"""

    SCORESHEETS_FOLDER = "scoresheets"

    def to_string(self) -> str:
        ret = f"CubeTeam name={self.name}: rfid_uid={self.rfid_uid}, max_time={self.max_time_sec}, start_time={self.starting_timestamp}, "
        ret += f"current_cube={self.current_cube}, won_cubes={len(self.completed_cubeboxes)}"
        return ret

    def __init__(self, name: str, rfid_uid: str, max_time_sec: float):
        # the name recorded at the front desk
        self.name = name
        # the RFID UID of the team
        self.rfid_uid = rfid_uid
        # the maximum time allowed to play the CubeGame
        self.max_time_sec = max_time_sec
        # the time when the team starts playing its first cubebox
        self.starting_timestamp:float = None
        # the cubebox ID currently being played by the team
        self.current_cube:int = None
        # the list of the cubeboxes IDs that the team has successfully played, with their completion times
        self.completed_cubeboxes: List[CompletedCubeboxStatus] = []

        # if the scoresheet folder is not present, create it
        if not os.path.exists(self.SCORESHEETS_FOLDER):
            os.makedirs(self.SCORESHEETS_FOLDER)

    def has_completed_cube(self, cube_id: int) -> bool:
        return cube_id in [box.cube_id for box in self.completed_cubeboxes]

    def set_completed_cube(self, cube_id: int, start_timestamp: float, win_timestamp: float) -> bool:
        if self.has_completed_cube(cube_id):
            return False
        self.completed_cubeboxes[cube_id] = CompletedCubeboxStatus(cube_id=cube_id, current_team_name=None, starting_timestamp=start_timestamp, victory_timestamp=win_timestamp)
        return True

    def is_time_over(self, current_time: float = None) -> Optional[bool]:
        try:
            return current_time - self.starting_timestamp > self.max_time_sec
        except TypeError:
            return None

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
        filename = os.path.join(self.SCORESHEETS_FOLDER, f"{self.name}_scoresheet.md")
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

    def save_html_score_sheet(self) -> bool:
        filename = os.path.join(self.SCORESHEETS_FOLDER, f"{self.name}_scoresheet.html")
        content = f"<h1>Équipe {self.name}</h1>\n\n"
        content += f"<p><strong>Date:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>\n\n"
        content += f"<p><strong>Temps alloué:</strong> {cube_utils.seconds_to_hhmmss_string(self.max_time_sec)}</p>\n\n"
        content += f"<p><strong>Score total:</strong> {self.calculate_score()} points</p>\n\n"
        content += "<h2>Score détaillé</h2>\n\n"
        content += "<ul>\n"
        for cube in self.completed_cubeboxes:
            content += f"<li><strong>Cube {cube.cube_id} : </strong> {cube.completion_time_str()} - {cube.calculate_score()} points</li>\n"
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
        return CubeTeamStatus(self.name, self.rfid_uid, self.max_time_sec)


# TODO : add ranks for the day, week, mont, all-time
class CubeTeamsStatusList(List[CubeTeamStatus]):
    """List of CubeTeam instances, one for each team playing a CubeGame. Meant to be used by the CubeMaster and FrontDesk."""

    DEFAULT_PICKLE_FILE = "cube_teams_list.pkl"

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.clear()

    def to_string(self) -> str:
        ret = f"CubeTeamsList : {len(self)} teams\n"
        for team in self:
            ret += f"  {team.to_string()}\n"
        return ret

    def add_team(self, team: CubeTeamStatus) -> bool:
        if self.find_team_by_name(team.name) is not None:
            return False
        self.append(team)
        return True

    def remove_team_by_name(self, name: str) -> bool:
        for team in self:
            if team.name == name:
                self.remove(team)
                return True
        return False

    def find_team_by_rfid_uid(self, rfid_uid: str) -> Optional[CubeTeamStatus]:
        for team in self:
            if team.rfid_uid == rfid_uid:
                return team
        return None

    def find_team_by_name(self, name: str) -> Optional[CubeTeamStatus]:
        for team in self:
            if team.name == name:
                return team
        return None

    def find_team_by_cube_id(self, cube_id: int) -> Optional[CubeTeamStatus]:
        for team in self:
            for cube in team.completed_cubeboxes:
                if cube.cube_id == cube_id:
                    return team
        return None

    # TESTME
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

    # TESTME
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

    def update_team(self, team:CubeTeamStatus) -> bool:
        for i, t in enumerate(self):
            if t.name == team.name:
                self[i] = team.copy()
                return True
        return False


def test_cube_team():
    team = CubeTeamStatus(rfid_uid="1234567890", name="Budapest", max_time_sec=60.0)
    assert team.rfid_uid == "1234567890"
    assert team.name == "Budapest"
    assert team.max_time_sec == 60.0
    assert not team.has_started()
    assert not team.is_time_over()
    team.starting_timestamp = time.time()
    assert team.has_started()
    assert not team.is_time_over()
    team.max_time_sec = 0.1
    assert team.is_time_over()
    team.completed_cubeboxes.append(CubeboxStatus(cube_id=1, starting_timestamp=time.time(), victory_timestamp=time.time() + 1))
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
    assert teams_list.find_team_by_rfid_uid("1234567890") == team1
    assert teams_list.find_team_by_name("Budapest") == team1
    assert teams_list.find_team_by_rfid_uid("1234567891") == team2
    assert teams_list.find_team_by_name("Paris") == team2
    assert teams_list.find_team_by_rfid_uid("1234567892") is None
    assert teams_list.find_team_by_name("London") is None
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
    assert teams_list.find_team_by_rfid_uid("1234567890") == team1
    assert teams_list.find_team_by_name("Budapest") == team1
    assert teams_list.remove_team_by_name("Budapest")
    assert len(teams_list) == 0
    assert not teams_list.load_from_pickle("foo")
    assert len(teams_list) == 0


if __name__ == "__main__":
    team = CubeTeamStatus(rfid_uid="1234567890", name="Budapest", max_time_sec=60.0)
    team.completed_cubeboxes.append(CubeboxStatus(cube_id=1, starting_timestamp=time.time(), victory_timestamp=time.time() + 1150))
    team.completed_cubeboxes.append(CubeboxStatus(cube_id=2, starting_timestamp=time.time(), victory_timestamp=time.time() + 200))
    team.save_html_score_sheet()
    # aaa

    exit(0)
    teams_list = CubeTeamsList()
    teams_list.append(CubeTeam(rfid_uid="1234567890", name="Budapest", allocated_time=60.0))
