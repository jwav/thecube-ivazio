import shutil
import sqlite3
import time

from thecubeivazio import cube_game as cg
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_logger import CubeLogger


class CubeDatabase:

    def __init__(self, db_filename):
        self.db_filename = db_filename
        if not self.does_database_exist():
            self.create_database()

    @cubetry
    def does_database_exist(self) -> bool:
        return os.path.exists(self.db_filename)

    @cubetry
    def get_database_file_last_modif_timestamp(self) -> Optional[float]:
        if os.path.exists(self.db_filename):
            return os.path.getmtime(self.db_filename)
        else:
            return None

    @cubetry
    def clear_database(self) -> bool:
        self.delete_database()
        return self.create_database()

    @cubetry
    def create_database(self) -> bool:
        if os.path.exists(self.db_filename):
            return True

        conn = sqlite3.connect(self.db_filename)
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS teams
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT,
                      custom_name TEXT,
                      rfid_uid TEXT,
                      max_time_sec REAL,
                      creation_timestamp REAL,
                      start_timestamp REAL,
                      use_alarm BOOLEAN,
                      current_cubebox_id INTEGER,
                      last_modification_timestamp REAL)''')

        c.execute('''CREATE TABLE IF NOT EXISTS completed_cubeboxes
                     (team_id INTEGER,
                      cube_id INTEGER,
                      current_team_name TEXT,
                      start_timestamp REAL,
                      win_timestamp REAL,
                      last_valid_rfid_line TEXT,
                      state TEXT,
                      FOREIGN KEY(team_id) REFERENCES teams(id))''')

        c.execute('''CREATE TABLE IF NOT EXISTS team_trophies
                     (team_id INTEGER,
                      trophy_name TEXT,
                      FOREIGN KEY(team_id) REFERENCES teams(id))''')

        conn.commit()
        conn.close()
        return True

    def delete_database(self):
        if os.path.exists(self.db_filename):
            os.remove(self.db_filename)
            print(f"Database {self.db_filename} deleted.")
        else:
            print(f"Database {self.db_filename} does not exist.")

    def backup_database(self, backup_filename=None):
        backup_filename = backup_filename or f"{self.db_filename}.backup"
        if os.path.exists(self.db_filename):
            shutil.copy2(self.db_filename, backup_filename)
            print(f"Database {self.db_filename} backed up as {backup_filename}.")
        else:
            print(f"Database {self.db_filename} does not exist.")

    @cubetry
    def update_database_from_teams_list(self, teams: cg.CubeTeamsStatusList) -> bool:
        if not os.path.exists(self.db_filename):
            self.create_database()

        conn = sqlite3.connect(self.db_filename)
        c = conn.cursor()

        for team in teams:
            c.execute('SELECT id FROM teams WHERE creation_timestamp = ?', (team.creation_timestamp,))
            existing_team = c.fetchone()

            if existing_team:
                team_id = existing_team[0]
                c.execute('''UPDATE teams SET name=?, custom_name=?, rfid_uid=?, max_time_sec=?, 
                 start_timestamp=?, use_alarm=?, current_cubebox_id=?, last_modification_timestamp=? WHERE id=?''',
                          (team.name, team.custom_name, team.rfid_uid, team.max_time_sec,
                           team.start_timestamp, team.use_alarm, team.current_cubebox_id,
                           team.last_modification_timestamp, team_id))
            else:
                c.execute('''INSERT INTO teams (name, custom_name, rfid_uid, max_time_sec, creation_timestamp, 
                                                start_timestamp, use_alarm, current_cubebox_id, last_modification_timestamp)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (team.name, team.custom_name, team.rfid_uid, team.max_time_sec,
                           team.creation_timestamp, team.start_timestamp, team.use_alarm, team.current_cubebox_id,
                           team.last_modification_timestamp))
                team_id = c.lastrowid

            c.execute('DELETE FROM completed_cubeboxes WHERE team_id = ?', (team_id,))
            c.execute('DELETE FROM team_trophies WHERE team_id = ?', (team_id,))

            for cubebox in team.completed_cubeboxes:
                c.execute('''INSERT INTO completed_cubeboxes (team_id, cube_id, current_team_name, start_timestamp,
                                                              win_timestamp, last_valid_rfid_line, state)
                             VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (team_id, cubebox.cube_id, cubebox.current_team_name, cubebox.start_timestamp,
                           cubebox.win_timestamp, cubebox.last_valid_rfid_line, cubebox.get_state().value))

            for trophy_name in team.trophies_names:
                c.execute('''INSERT INTO team_trophies (team_id, trophy_name)
                             VALUES (?, ?)''',
                          (team_id, trophy_name))

        conn.commit()
        conn.close()
        return True

    @cubetry
    def find_teams_matching(self, name=None, custom_name=None, rfid_uid=None,
                            min_creation_timestamp=None, max_creation_timestamp=None,
                            min_modification_timestamp=None) -> Optional[cg.CubeTeamsStatusList]:
        conn = sqlite3.connect(self.db_filename)
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
        if min_modification_timestamp:
            query += " AND last_modification_timestamp >= ?"
            params.append(min_modification_timestamp)

        c.execute(query, params)
        rows = c.fetchall()

        teams_list = cg.CubeTeamsStatusList()
        for row in rows:
            team_id, name, custom_name, rfid_uid, max_time_sec, creation_timestamp, start_timestamp, use_alarm, current_cubebox_id, last_modification_timestamp = row
            c.execute("SELECT * FROM completed_cubeboxes WHERE team_id = ?", (team_id,))
            completed_cubeboxes_rows = c.fetchall()
            completed_cubeboxes = cg.CompletedCubeboxStatusList([
                cg.CompletedCubeboxStatus(
                    cube_id=cube_id,
                    current_team_name=current_team_name,
                    start_timestamp=start_timestamp,
                    win_timestamp=win_timestamp,
                    last_valid_rfid_line=last_valid_rfid_line,
                    state=cg.CubeboxState(state)
                )
                for _, cube_id, current_team_name, start_timestamp, win_timestamp, last_valid_rfid_line, state in
                completed_cubeboxes_rows
            ])

            c.execute("SELECT trophy_name FROM team_trophies WHERE team_id = ?", (team_id,))
            trophies_names_rows = c.fetchall()
            trophies_names = [trophy_name for (trophy_name,) in trophies_names_rows]

            team = cg.CubeTeamStatus(
                name=name,
                custom_name=custom_name,
                rfid_uid=rfid_uid,
                max_time_sec=max_time_sec,
                creation_timestamp=creation_timestamp,
                start_timestamp=start_timestamp,
                current_cubebox_id=current_cubebox_id,
                completed_cubeboxes=completed_cubeboxes,
                trophies_names=trophies_names,
                use_alarm=bool(use_alarm)
            )

            teams_list.append(team)

        conn.close()
        return teams_list

    @cubetry
    def get_latest_creation_timestamp(self) -> Optional[float]:
        conn = sqlite3.connect(self.db_filename)
        c = conn.cursor()

        c.execute("SELECT MAX(creation_timestamp) FROM teams")
        row = c.fetchone()
        latest_timestamp = row[0] if row else None

        conn.close()
        return latest_timestamp

    @cubetry
    def load_all_teams(self) -> cg.CubeTeamsStatusList:
        return self.find_teams_matching()

    @cubetry
    def add_team_to_database(self, team: cg.CubeTeamStatus) -> bool:
        return self.update_team_in_database(team)

    @cubetry
    def update_team_in_database(self, team: cg.CubeTeamStatus) -> bool:
        team.update_modification_timestamp()
        return self.update_database_from_teams_list(cg.CubeTeamsStatusList([team]))

    def find_team_by_creation_timestamp(self, team_creation_timestamp) -> Optional[cg.CubeTeamStatus]:
        epsilon = TIMESTAMP_EPSILON
        teams = self.find_teams_matching(min_creation_timestamp=team_creation_timestamp - epsilon,
                                         max_creation_timestamp=team_creation_timestamp + epsilon)
        if len(teams) == 1:
            return teams[0]
        elif len(teams) > 1:
            CubeLogger.static_error(
                f"Found multiple teams with creation timestamp {team_creation_timestamp}. This shouldn't happen.")
            return teams[0]
        else:
            return None

    def generate_sample_teams_sqlite_database(self):
        teams = cg.generate_sample_teams()
        self.delete_database()
        self.create_database()
        if self.update_database_from_teams_list(teams):
            print("Sample teams sqlite database generated:")
            print(teams.to_string())

    def display_teams_sqlite_database(self):
        teams = self.load_all_teams()
        print(teams.to_string())
        print(f"nb teams: {len(teams)}")


def expanded_test_find_teams_matching():
    test_db_filepath = os.path.join(SAVES_DIR, 'test_teams_database.db')
    db = CubeDatabase(test_db_filepath)
    db.delete_database()
    db.create_database()

    teams = cg.CubeTeamsStatusList([
        cg.CubeTeamStatus(
            name="TestTeam1",
            custom_name="Custom1",
            rfid_uid="1111",
            max_time_sec=3600,
            creation_timestamp=time.time() - 10000,
            start_timestamp=time.time() - 10000,
            current_cubebox_id=1,
            completed_cubeboxes=cg.CompletedCubeboxStatusList([
                cg.CompletedCubeboxStatus(
                    cube_id=1,
                    current_team_name="TestTeam1",
                    start_timestamp=time.time() - 10000,
                    win_timestamp=time.time() - 9000,
                    state=cg.CubeboxState.STATE_PLAYING
                )
            ]),
            trophies_names=["Trophy1"],
            use_alarm=False
        ),
        cg.CubeTeamStatus(
            name="TestTeam2",
            custom_name="Custom2",
            rfid_uid="2222",
            max_time_sec=7200,
            creation_timestamp=time.time() - 5000,
            start_timestamp=time.time() - 5000,
            current_cubebox_id=2,
            completed_cubeboxes=cg.CompletedCubeboxStatusList([
                cg.CompletedCubeboxStatus(
                    cube_id=2,
                    current_team_name="TestTeam2",
                    start_timestamp=time.time() - 5000,
                    win_timestamp=time.time() - 4000,
                    state=cg.CubeboxState.STATE_READY_TO_PLAY
                )
            ]),
            trophies_names=["Trophy2"],
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
            completed_cubeboxes=cg.CompletedCubeboxStatusList(),
            trophies_names=[],
            use_alarm=False
        )
    ])

    db.update_database_from_teams_list(teams)

    found_teams = db.find_teams_matching(name="test")

    assert found_teams.is_valid()

    CubeLogger.static_debug(f"Found teams by partial name 'test': {found_teams}")
    err_msg = f"Test Failed: Expected 2 teams with partial name 'test' (actual len={len(found_teams)})"
    assert len(found_teams) == 2, err_msg
    print("Test Passed: Found teams by partial name 'test'")

    found_teams = db.find_teams_matching(custom_name="custom")
    CubeLogger.static_debug(f"Found teams by partial custom name 'custom': {found_teams}")
    assert len(found_teams) == 3, "Test Failed: Expected 3 teams with partial custom name 'custom'"
    print("Test Passed: Found teams by partial custom name 'custom'")

    min_timestamp = time.time() - 7000
    max_timestamp = time.time() - 1000
    found_teams = db.find_teams_matching(min_creation_timestamp=min_timestamp, max_creation_timestamp=max_timestamp)
    CubeLogger.static_debug(
        f"Found teams by creation timestamp range {min_timestamp} to {max_timestamp}: {found_teams}")
    assert len(found_teams) == 2, f"Test Failed: Expected 2 teams in timestamp range {min_timestamp} to {max_timestamp}"
    print(f"Test Passed: Found teams by creation timestamp range {min_timestamp} to {max_timestamp}")

    found_teams = db.find_teams_matching(name="NonExistent")
    CubeLogger.static_debug(f"Found teams with no matches (name='NonExistent'): {found_teams}")
    assert len(found_teams) == 0, "Test Failed: Expected 0 teams with name 'NonExistent'"
    print("Test Passed: Found no teams with name 'NonExistent'")

    found_teams = db.find_teams_matching(name="AlphaTeam", custom_name="AlphaCustom", rfid_uid="3333")
    CubeLogger.static_debug(
        f"Found teams by multiple parameters (name='AlphaTeam', custom_name='AlphaCustom', rfid_uid='3333'): {found_teams}")
    assert len(
        found_teams) == 1, "Test Failed: Expected 1 team with name 'AlphaTeam', custom name 'AlphaCustom', and rfid_uid '3333'"
    print(
        "Test Passed: Found teams by multiple parameters (name='AlphaTeam', custom_name='AlphaCustom', rfid_uid='3333')")
    return True


if __name__ == "__main__":
    db = CubeDatabase(CUBEMASTER_SQLITE_DATABASE_FILEPATH)
    db.generate_sample_teams_sqlite_database()
    db = CubeDatabase(FRONTDESK_SQLITE_DATABASE_FILEPATH)
    db.generate_sample_teams_sqlite_database()
    db.display_teams_sqlite_database()
    expanded_test_find_teams_matching()
