import sqlite3
import json
import time
import os

from thecubeivazio.cube_common_defines import *
from thecubeivazio import cube_game as cg
from thecubeivazio.cube_logger import CubeLogger

@cubetry
def create_database(db_filename=None) -> bool:
    db_filename = db_filename or TEAMS_SQLITE_DATABASE_FILEPATH

    # first, check if the file exists
    if os.path.exists(db_filename):
        return True

    conn = sqlite3.connect(db_filename)
    c = conn.cursor()

    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS teams
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  custom_name TEXT,
                  rfid_uid TEXT,
                  max_time_sec REAL,
                  creation_timestamp REAL,
                  start_timestamp REAL,
                  use_alarm BOOLEAN,
                  current_cubebox_id INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS completed_cubeboxes
                 (team_id INTEGER,
                  cube_id INTEGER,
                  current_team_name TEXT,
                  start_timestamp REAL,
                  win_timestamp REAL,
                  last_valid_rfid_line TEXT,
                  state TEXT,
                  FOREIGN KEY(team_id) REFERENCES teams(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS trophies
                 (team_id INTEGER,
                  name TEXT,
                  description TEXT,
                  points INTEGER,
                  image_filename TEXT,
                  FOREIGN KEY(team_id) REFERENCES teams(id))''')

    conn.commit()
    conn.close()
    return True

@cubetry
def update_database_from_teams_list(teams: cg.CubeTeamsStatusList, db_filename=None) -> bool:
    db_filename = db_filename or TEAMS_SQLITE_DATABASE_FILEPATH
    # if the database doesnt exist, create it
    if not os.path.exists(db_filename):
        create_database(db_filename)

    conn = sqlite3.connect(db_filename)
    c = conn.cursor()

    for team in teams:
        c.execute('''INSERT INTO teams (name, custom_name, rfid_uid, max_time_sec, creation_timestamp, 
                                        start_timestamp, use_alarm, current_cubebox_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (team.name, team.custom_name, team.rfid_uid, team.max_time_sec,
                   team.creation_timestamp, team.start_timestamp, team.use_alarm, team.current_cubebox_id))

        team_id = c.lastrowid

        for cubebox in team.completed_cubeboxes:
            c.execute('''INSERT INTO completed_cubeboxes (team_id, cube_id, current_team_name, start_timestamp,
                                                          win_timestamp, last_valid_rfid_line, state)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (team_id, cubebox.cube_id, cubebox.current_team_name, cubebox.start_timestamp,
                       cubebox.win_timestamp, cubebox.last_valid_rfid_line, cubebox._state.value))

        for trophy in team.trophies:
            c.execute('''INSERT INTO trophies (team_id, name, description, points, image_filename)
                         VALUES (?, ?, ?, ?, ?)''',
                      (team_id, trophy.name, trophy.description, trophy.points, trophy.image_filename))

    conn.commit()
    conn.close()
    return True

@cubetry
def find_teams_matching(name=None, custom_name=None, rfid_uid=None,
                        min_creation_timestamp=None, max_creation_timestamp=None,
                        db_filename=None) -> Optional[cg.CubeTeamsStatusList]:
    """Find teams matching the given parameters in the database.
    for name and custom_name, the search is case-insensitive and partial (i.e. 'abc' will match 'xAbCy').
    """
    db_filename = db_filename or TEAMS_SQLITE_DATABASE_FILEPATH
    conn = sqlite3.connect(db_filename)
    c = conn.cursor()

    query = "SELECT * FROM teams WHERE 1=1"
    params = []

    if name:
        query += " AND LOWER(name) LIKE ?"
        params.append(f"%{name.lower()}%")
    if custom_name:
        query += " AND LOWER(custom_name) LIKE ?"
        params.append(f"%{custom_name.lower()}%")
    if rfid_uid:
        query += " AND rfid_uid = ?"
        params.append(rfid_uid)
    if min_creation_timestamp:
        query += " AND creation_timestamp >= ?"
        params.append(min_creation_timestamp)
    if max_creation_timestamp:
        query += " AND creation_timestamp <= ?"
        params.append(max_creation_timestamp)

    c.execute(query, params)
    rows = c.fetchall()

    teams_list = cg.CubeTeamsStatusList()
    for row in rows:
        team_id, name, custom_name, rfid_uid, max_time_sec, creation_timestamp, start_timestamp, use_alarm, current_cubebox_id = row
        c.execute("SELECT * FROM completed_cubeboxes WHERE team_id = ?", (team_id,))
        completed_cubeboxes_rows = c.fetchall()
        completed_cubeboxes = [
            cg.CompletedCubeboxStatus(
                cube_id=cube_id,
                current_team_name=current_team_name,
                start_timestamp=start_timestamp,
                end_timestamp=win_timestamp,
                last_valid_rfid_line=last_valid_rfid_line,
                state=cg.CubeboxState(state)
            )
            for _, cube_id, current_team_name, start_timestamp, win_timestamp, last_valid_rfid_line, state in
            completed_cubeboxes_rows
        ]

        c.execute("SELECT * FROM trophies WHERE team_id = ?", (team_id,))
        trophies_rows = c.fetchall()
        trophies = [
            cg.CubeTrophy(
                name=name,
                description=description,
                points=points,
                image_filename=image_filename
            )
            for _, name, description, points, image_filename in trophies_rows
        ]

        team = cg.CubeTeamStatus(
            name=name,
            custom_name=custom_name,
            rfid_uid=rfid_uid,
            max_time_sec=max_time_sec,
            creation_timestamp=creation_timestamp,
            start_timestamp=start_timestamp,
            current_cubebox_id=current_cubebox_id,
            completed_cubeboxes=completed_cubeboxes,
            trophies=trophies,
            use_alarm=use_alarm
        )

        teams_list.append(team)

    conn.close()
    return teams_list

# Test function
def test_find_teams_matching():
    test_db_filename = 'test_teams_database.db'
    create_database(test_db_filename)

    # Create some test data
    teams = cg.CubeTeamsStatusList([
        cg.CubeTeamStatus(
            name="TestTeam1",
            custom_name="Custom1",
            rfid_uid="1111",
            max_time_sec=3600,
            creation_timestamp=time.time(),
            start_timestamp=time.time(),
            current_cubebox_id=1,
            completed_cubeboxes=[
                cg.CompletedCubeboxStatus(
                    cube_id=1,
                    current_team_name="TestTeam1",
                    start_timestamp=time.time(),
                    end_timestamp=time.time() + 1000,
                    state=cg.CubeboxState.STATE_PLAYING
                )
            ],
            trophies=[
                cg.CubeTrophy(
                    name="Trophy1",
                    description="First trophy",
                    points=100,
                    image_filename="default_trophy_image.png"
                )
            ],
            use_alarm=False
        ),
        cg.CubeTeamStatus(
            name="TestTeam2",
            custom_name="Custom2",
            rfid_uid="2222",
            max_time_sec=7200,
            creation_timestamp=time.time(),
            start_timestamp=time.time(),
            current_cubebox_id=2,
            completed_cubeboxes=[
                cg.CompletedCubeboxStatus(
                    cube_id=2,
                    current_team_name="TestTeam2",
                    start_timestamp=time.time(),
                    end_timestamp=time.time() + 2000,
                    state=cg.CubeboxState.STATE_READY_TO_PLAY
                )
            ],
            trophies=[
                cg.CubeTrophy(
                    name="Trophy2",
                    description="Second trophy",
                    points=200,
                    image_filename="default_trophy_image.png"
                )
            ],
            use_alarm=True
        )
    ])

    update_database_from_teams_list(teams, test_db_filename)

    # Find teams by name
    found_teams = find_teams_matching(name="TestTeam1", db_filename=test_db_filename)
    print("Found teams by name 'TestTeam1':", found_teams)

    # Find teams by custom name
    found_teams = find_teams_matching(custom_name="Custom2", db_filename=test_db_filename)
    print("Found teams by custom name 'Custom2':", found_teams)

    # Find teams by RFID UID
    found_teams = find_teams_matching(rfid_uid="1111", db_filename=test_db_filename)
    print("Found teams by RFID UID '1111':", found_teams)


def expanded_test_find_teams_matching():
    test_db_filename = 'test_teams_database.db'
    create_database(test_db_filename)

    # Create some test data
    teams = cg.CubeTeamsStatusList([
        cg.CubeTeamStatus(
            name="TestTeam1",
            custom_name="Custom1",
            rfid_uid="1111",
            max_time_sec=3600,
            creation_timestamp=time.time() - 10000,  # Old timestamp
            start_timestamp=time.time() - 10000,
            current_cubebox_id=1,
            completed_cubeboxes=[
                cg.CompletedCubeboxStatus(
                    cube_id=1,
                    current_team_name="TestTeam1",
                    start_timestamp=time.time() - 10000,
                    end_timestamp=time.time() - 9000,
                    state=cg.CubeboxState.STATE_PLAYING
                )
            ],
            trophies=[
                cg.CubeTrophy(
                    name="Trophy1",
                    description="First trophy",
                    points=100,
                    image_filename="default_trophy_image.png"
                )
            ],
            use_alarm=False
        ),
        cg.CubeTeamStatus(
            name="TestTeam2",
            custom_name="Custom2",
            rfid_uid="2222",
            max_time_sec=7200,
            creation_timestamp=time.time() - 5000,  # Recent timestamp
            start_timestamp=time.time() - 5000,
            current_cubebox_id=2,
            completed_cubeboxes=[
                cg.CompletedCubeboxStatus(
                    cube_id=2,
                    current_team_name="TestTeam2",
                    start_timestamp=time.time() - 5000,
                    end_timestamp=time.time() - 4000,
                    state=cg.CubeboxState.STATE_READY_TO_PLAY
                )
            ],
            trophies=[
                cg.CubeTrophy(
                    name="Trophy2",
                    description="Second trophy",
                    points=200,
                    image_filename="default_trophy_image.png"
                )
            ],
            use_alarm=True
        ),
        cg.CubeTeamStatus(
            name="AlphaTeam",
            custom_name="AlphaCustom",
            rfid_uid="3333",
            max_time_sec=5400,
            creation_timestamp=time.time() - 2000,
            start_timestamp=time.time() - 2000,
            current_cubebox_id=3,
            completed_cubeboxes=[],
            trophies=[],
            use_alarm=False
        )
    ])

    update_database_from_teams_list(teams, test_db_filename)

    # Find teams by partial name (case insensitive)
    found_teams = find_teams_matching(name="test", db_filename=test_db_filename)
    assert len(found_teams) == 2, "Test Failed: Expected 2 teams with partial name 'test'"
    print("Test Passed: Found teams by partial name 'test'")

    # Find teams by partial custom name (case insensitive)
    found_teams = find_teams_matching(custom_name="custom", db_filename=test_db_filename)
    assert len(found_teams) == 3, "Test Failed: Expected 3 teams with partial custom name 'custom'"
    print("Test Passed: Found teams by partial custom name 'custom'")

    # Find teams by creation timestamp range
    min_timestamp = time.time() - 7000
    max_timestamp = time.time() - 1000
    found_teams = find_teams_matching(min_creation_timestamp=min_timestamp, max_creation_timestamp=max_timestamp, db_filename=test_db_filename)
    assert len(found_teams) == 2, f"Test Failed: Expected 2 teams in timestamp range {min_timestamp} to {max_timestamp}"
    print(f"Test Passed: Found teams by creation timestamp range {min_timestamp} to {max_timestamp}")

    # Find teams with no matches
    found_teams = find_teams_matching(name="NonExistent", db_filename=test_db_filename)
    assert len(found_teams) == 0, "Test Failed: Expected 0 teams with name 'NonExistent'"
    print("Test Passed: Found no teams with name 'NonExistent'")

    # Find teams by multiple parameters
    found_teams = find_teams_matching(name="AlphaTeam", custom_name="AlphaCustom", rfid_uid="3333", db_filename=test_db_filename)
    assert len(found_teams) == 1, "Test Failed: Expected 1 team with name 'AlphaTeam', custom name 'AlphaCustom', and rfid_uid '3333'"
    print("Test Passed: Found teams by multiple parameters (name='AlphaTeam', custom_name='AlphaCustom', rfid_uid='3333')")




if __name__ == "__main__":
    # test_find_teams_matching()
    expanded_test_find_teams_matching()