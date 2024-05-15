"""Modelises a TheCube game session, i.e. a team trying to open a CubeBox"""
import time
from dataclasses import dataclass
from typing import List, Optional
import pickle

from thecubeivazio import cube_identification as cubeid
from thecubeivazio import cube_utils
import os


@dataclass
class CubeBoxGame:
    """Represents a game session, i.e. a team trying to open a CubeBox"""
    cube_id: int
    current_team: Optional[int] = None
    starting_timestamp: Optional[float] = None
    victory_timestamp: Optional[float] = None

    EASY_CUBES = (1, 2, 3, 4)
    MEDIUM_CUBES = (5, 6, 7, 8)
    HARD_CUBES = (9, 10, 11, 12)
    MAX_SCORE = 300
    EASY_MIN_TIME = 5 * 60
    MEDIUM_MIN_TIME = 8 * 60
    HARD_MIN_TIME = 12 * 60

    def to_string(self) -> str:
        return f"CubeBoxGame {self.cube_id}: team={self.current_team}, start={self.starting_timestamp}, victory={self.victory_timestamp}"

    def reset(self):
        self.current_team = None
        self.starting_timestamp = None
        self.victory_timestamp = None

    def is_free(self) -> bool:
        return self.current_team is None and self.starting_timestamp is None and self.victory_timestamp is None

    def completion_time(self) -> Optional[float]:
        if self.starting_timestamp is None or self.victory_timestamp is None:
            return None
        return self.victory_timestamp - self.starting_timestamp

    def elapsed_time(self) -> Optional[float]:
        if self.starting_timestamp is None:
            return None
        return time.time() - self.starting_timestamp

    def completion_time_str(self) -> str:
        completion_time = self.completion_time()
        if completion_time is None:
            return "N/A"
        return cube_utils.seconds_to_hhmmss_string(completion_time)

    def calculate_score(self) -> int:
        total_time = self.completion_time()
        if self.cube_id in self.EASY_CUBES:
            return self.MAX_SCORE if total_time < self.EASY_MIN_TIME else int(
                self.EASY_MIN_TIME - 1 / 3 * (total_time - self.EASY_MIN_TIME))
        elif self.cube_id in self.MEDIUM_CUBES:
            return self.MAX_SCORE if total_time < self.MEDIUM_MIN_TIME else int(
                self.MEDIUM_MIN_TIME - 1 / 3 * (total_time - self.MEDIUM_MIN_TIME))
        elif self.cube_id in self.HARD_CUBES:
            return self.MAX_SCORE if total_time < self.HARD_MIN_TIME else int(
                self.HARD_MIN_TIME - 1 / 3 * (total_time - self.HARD_MIN_TIME))
        else:
            return 0


class CubeGamesList(List[CubeBoxGame]):
    """List of CubeGame instances, one for each CubeBox in TheCube game. Meant to be used by the CubeServer and FrontDesk."""

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.clear()
        self.extend([CubeBoxGame(cube_id) for cube_id in cubeid.CUBE_IDS])

    def free_cubes(self) -> List[int]:
        return [cube.cube_id for cube in self if cube.is_free()]

    def played_cubes(self) -> List[int]:
        return [cube.cube_id for cube in self if not cube.is_free()]


class CubeTeam:
    """Represents a team playing a CubeGame"""

    SCORESHEETS_FOLDER = "scoresheets"

    def to_string(self) -> str:
        ret = f"CubeTeam {self.name}: rfid={self.rfid_uid}, max_time={self.max_time_sec}, started={self.starting_timestamp}, "
        ret += f"current_cube={self.current_cube}, won_cubes={len(self.completed_cubes)}"
        return ret

    def __init__(self, rfid_uid: int, name: str, allocated_time: float):
        self.rfid_uid = rfid_uid
        self.name = name
        self.max_time_sec = allocated_time
        self.starting_timestamp = None
        self.current_cube = None
        self.completed_cubes: List[CubeBoxGame] = []

        # if the scoresheet folder is not present, create it
        if not os.path.exists(self.SCORESHEETS_FOLDER):
            os.makedirs(self.SCORESHEETS_FOLDER)


    def is_time_over(self, current_time: float = None) -> Optional[bool]:
        try:
            return current_time - self.starting_timestamp > self.max_time_sec
        except TypeError:
            return None

    def has_started(self) -> bool:
        return self.starting_timestamp is not None

    def calculate_score(self) -> int:
        return sum([cube.calculate_score() for cube in self.completed_cubes])

    def generate_raw_score_sheet(self) -> str:
        ret = f"Équipe {self.name} : {self.calculate_score()} points\n"
        for cube in self.completed_cubes:
            ret += f"Cube {cube.cube_id} : {cube.completion_time_str()} : {cube.calculate_score()} points\n"
        return ret

    def save_markdown_score_sheet(self) -> bool:
        filename = os.path.join(self.SCORESHEETS_FOLDER, f"{self.name}_scoresheet.md")
        text = f"# Équipe {self.name}\n\n"
        text += f"**Total Score:** {self.calculate_score()} points\n\n"
        text += "## Completed Cubes\n\n"
        for cube in self.completed_cubes:
            text += f"- **Cube {cube.cube_id}:** {cube.completion_time_str()} - {cube.calculate_score()} points\n"
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
        for cube in self.completed_cubes:
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


# TODO : add ranks for the day, week, mont, all-time
class CubeTeamsList(List[CubeTeam]):
    """List of CubeTeam instances, one for each team playing a CubeGame. Meant to be used by the CubeServer and FrontDesk."""

    DEFAULT_PICKLE_FILE = "cube_teams_list.pkl"

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.clear()

    def add_team(self, team: CubeTeam) -> bool:
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

    def find_team_by_rfid_uid(self, rfid_uid: int) -> Optional[CubeTeam]:
        for team in self:
            if team.rfid_uid == rfid_uid:
                return team
        return None

    def find_team_by_name(self, name: str) -> Optional[CubeTeam]:
        for team in self:
            if team.name == name:
                return team
        return None

    def find_team_by_cube_id(self, cube_id: int) -> Optional[CubeTeam]:
        for team in self:
            for cube in team.completed_cubes:
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

class OverallGameStatus:
    """Container for the overall game state, i.e. the CubeGamesList and CubeTeamsList instances"""

    def __init__(self):
        self.cube_games = CubeGamesList()
        self.cube_teams = CubeTeamsList()
        self.reset()

    def reset(self):
        self.cube_games.reset()
        self.cube_teams.reset()



def test_cube_team():
    team = CubeTeam(rfid_uid=1234567890, name="Budapest", allocated_time=60.0)
    assert team.rfid_uid == 1234567890
    assert team.name == "Budapest"
    assert team.max_time_sec == 60.0
    assert not team.has_started()
    assert not team.is_time_over()
    team.starting_timestamp = time.time()
    assert team.has_started()
    assert not team.is_time_over()
    team.max_time_sec = 0.1
    assert team.is_time_over()
    team.completed_cubes.append(CubeBoxGame(cube_id=1, starting_timestamp=time.time(), victory_timestamp=time.time() + 1))
    assert team.calculate_score() == 300
    assert team.generate_raw_score_sheet() == "Équipe Budapest : 300 points\nCube 1 : 00:00:01 : 300 points\n"
    assert team.save_markdown_score_sheet()
    assert team.save_html_score_sheet()


def test_cube_teams_list():
    teams_list = CubeTeamsList()
    assert len(teams_list) == 0
    team1 = CubeTeam(rfid_uid=1234567890, name="Budapest", allocated_time=60.0)
    team2 = CubeTeam(rfid_uid=1234567891, name="Paris", allocated_time=60.0)
    assert teams_list.add_team(team1)
    assert len(teams_list) == 1
    assert teams_list.add_team(team2)
    assert len(teams_list) == 2
    assert not teams_list.add_team(team1)
    assert len(teams_list) == 2
    assert teams_list.find_team_by_rfid_uid(1234567890) == team1
    assert teams_list.find_team_by_name("Budapest") == team1
    assert teams_list.find_team_by_rfid_uid(1234567891) == team2
    assert teams_list.find_team_by_name("Paris") == team2
    assert teams_list.find_team_by_rfid_uid(1234567892) is None
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
    assert teams_list.find_team_by_rfid_uid(1234567890) == team1
    assert teams_list.find_team_by_name("Budapest") == team1
    assert teams_list.remove_team_by_name("Budapest")
    assert len(teams_list) == 0
    assert not teams_list.load_from_pickle("foo")
    assert len(teams_list) == 0


if __name__ == "__main__":
    team = CubeTeam(rfid_uid=1234567890, name="Budapest", allocated_time=60.0)
    team.completed_cubes.append(CubeBoxGame(cube_id=1, starting_timestamp=time.time(), victory_timestamp=time.time() + 1150))
    team.completed_cubes.append(CubeBoxGame(cube_id=2, starting_timestamp=time.time(), victory_timestamp=time.time() + 200))
    team.save_html_score_sheet()

    exit(0)
    teams_list = CubeTeamsList()
    teams_list.append(CubeTeam(rfid_uid=1234567890, name="Budapest", allocated_time=60.0))
