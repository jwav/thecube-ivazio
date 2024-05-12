"""Modelises a TheCube game session, i.e. a team trying to open a CubeBox"""
import time
from dataclasses import dataclass
from typing import List, Optional

import cube_identification as cubeid


@dataclass
class CubeGame:
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
        return time.strftime("%H:%M:%S", time.gmtime(completion_time))

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


class CubeGamesList(List[CubeGame]):
    """List of CubeGame instances, one for each CubeBox in TheCube game. Meant to be used by the CubeServer and FrontDesk."""

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.clear()
        self.extend([CubeGame(cube_id) for cube_id in cubeid.CUBE_IDS])

    def free_cubes(self) -> List[int]:
        return [cube.cube_id for cube in self if cube.is_free()]

    def played_cubes(self) -> List[int]:
        return [cube.cube_id for cube in self if not cube.is_free()]


class CubeTeam:
    """Represents a team playing a CubeGame"""

    def __init__(self, rfid_uid: int, name: str, allocated_time: float):
        self.rfid_uid = rfid_uid
        self.name = name
        self.allocated_time = allocated_time
        self.starting_timestamp = None
        self.completed_cubes: List[CubeGame] = []

    def is_time_over(self, current_time: float = None) -> bool:
        if current_time is None:
            current_time = time.time()
        return current_time - self.starting_timestamp > self.allocated_time

    def has_started(self) -> bool:
        return self.starting_timestamp is not None

    def calculate_score(self) -> int:
        return sum([cube.calculate_score() for cube in self.completed_cubes])

    def generate_score_sheet(self) -> str:
        ret = f"Équipe {self.name} : {self.calculate_score()} points\n"
        for cube in self.completed_cubes:
            ret += f"Cube {cube.cube_id} : {cube.completion_time_str()} : {cube.calculate_score()} points\n"
        return ret

class CubeTeamsList(List[CubeTeam]):
    """List of CubeTeam instances, one for each team playing a CubeGame. Meant to be used by the CubeServer and FrontDesk."""

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



if __name__ == "__main__":
    teams_list = CubeTeamsList()
    teams_list.append(CubeTeam(rfid_uid=1234567890, name="Budapest", allocated_time=60.0))
