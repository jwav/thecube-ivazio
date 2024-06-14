import subprocess
import textwrap
import threading
import time
from typing import List
import datetime
from thecubeivazio.cube_common_defines import *
from thecubeivazio import cube_game as cg
from thecubeivazio import cube_identification as cid
from thecubeivazio import cube_utils as cu
from thecubeivazio import cube_database as cdb
from thecubeivazio import cubeserver_frontdesk as cfd
import random

NB_TEAMS_PER_HIGHSCORE_SUBTABLE = 5
# TODO: implement
NB_TEAMS_IN_PLAYING_TEAMS_SUBTABLE = 10

HIGHSCORES_MAIN_FILENAME = "highscores_main.html"
HIGHSCORES_SUBTABLE_LEFT_FILENAME = "highscores_subtable_left.html"
HIGHSCORES_SUBTABLE_CENTER_FILENAME = "highscores_subtable_center.html"
HIGHSCORES_SUBTABLE_RIGHT_FILENAME = "highscores_subtable_right.html"
HIGHSCORES_PLAYING_TEAMS_SUBTABLE_FILENAME = "playing_teams_subtable.html"
TITLE_ICON_FILENAME = "icon_thecube_highscores_title.png"

HIGHSCORES_SUBTABLE_LEFT_FILEPATH = os.path.join(HIGHSCORES_DIR, HIGHSCORES_SUBTABLE_LEFT_FILENAME)
HIGHSCORES_SUBTABLE_CENTER_FILEPATH = os.path.join(HIGHSCORES_DIR, HIGHSCORES_SUBTABLE_CENTER_FILENAME)
HIGHSCORES_SUBTABLE_RIGHT_FILEPATH = os.path.join(HIGHSCORES_DIR, HIGHSCORES_SUBTABLE_RIGHT_FILENAME)
HIGHSCORES_PLAYING_TEAMS_SUBTABLE_FILEPATH = os.path.join(HIGHSCORES_DIR, HIGHSCORES_PLAYING_TEAMS_SUBTABLE_FILENAME)
HIGHSCORES_MAIN_FILEPATH = os.path.join(HIGHSCORES_DIR, HIGHSCORES_MAIN_FILENAME)

BROWSER_NAMES = ["chromium-browser"]
PLAYING_TEAMS_UPDATE_PERIOD_SEC = 5
FULL_UPDATE_PERIOD_SEC = 30
DEFAULT_BROWSER_NAME = "brave"
HTTP_SERVER_PORT = 8000
HTTP_HIGHSCORES_MAIN_URL = "http://localhost:8000/highscores_main.html"

import psutil

from thecubeivazio.cube_http import CubeHttpServer


def launch_chromium(url):
    # Suppress GTK warnings
    # doesnt work...
    # os.environ['GTK_DEBUG'] = '0'
    # os.environ['GTK_MODULES'] = ''
    # os.environ['FONTCONFIG_PATH'] = '/etc/fonts'

    # Construct the command to launch Chromium in fullscreen mode
    command = [
        'chromium-browser',  # or 'chromium' depending on your system
        '--kiosk',  # Fullscreen mode
        '--noerrdialogs',  # Suppress error dialogs
        '--disable-infobars',  # Disable info bars
        '--incognito',  # Incognito mode
        '--force-device-scale-factor=0.8',  # set zoom
        url  # The URL to open
    ]

    # Execute the command
    subprocess.run(command)


def refresh_chromium():
    return
    # Find the Chromium process
    for process in psutil.process_iter():
        if process.name() == 'chromium-browser':
            # Reload the page by sending a signal
            process.send_signal(psutil.signal.SIGHUP)
            break


class CubeHighscoresPlayingTeamsSubtable:
    def __init__(self, teams: cg.CubeTeamsStatusList, cubeboxes: cg.CubeboxesStatusList):
        self.teams = teams.copy()
        assert isinstance(self.teams, cg.CubeTeamsStatusList), f"self.teams is not a CubeTeamsStatusList: {self.teams}"
        self.teams.sort_by_score()
        self.cubeboxes = cubeboxes.copy()

    def generate_html(self) -> str:
        team_rows = self.generate_teams_rows()
        cubebox_headers = self.generate_cubebox_headers()

        html_content = textwrap.dedent(f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Playing Teams</title>
            <link rel="stylesheet" href="playing_teams_subtable.css">
        </head>
        <body>
        <div class="container">
            <table>
                <thead>
                    <tr>
                        <th>Rang</th>
                        <th>Équipe</th>
                        <th>Score</th>
                        <th>Cubes</th>
                        {cubebox_headers}
                    </tr>
                </thead>
                <tbody>
                    {team_rows}
                </tbody>
            </table>
        </div>
        </body>
        </html>
        """)
        return html_content

    def generate_cubebox_headers(self):
        cubebox_headers = ""
        for cubebox in self.cubeboxes:
            classname = self.get_cubebox_css_class(cubebox)
            text = f"C{cubebox.cube_id}"
            cubebox_headers += f'<th class="{classname}">{text}</th>'
        return cubebox_headers

    def generate_teams_rows(self) -> str:
        team_rows = ""
        for i, team in enumerate(self.teams):
            assert isinstance(team.completed_cubeboxes,
                              cg.CubeboxesStatusList), f"team.completed_cubeboxes is not a CubeboxesStatusList: {team.completed_cubeboxes}"
            cubeboxes_data = ""
            for cubebox in self.cubeboxes:
                completed_cubebox = team.completed_cubeboxes.get_cubebox_by_cube_id(cubebox.cube_id)
                cubebox_score = None if not completed_cubebox else completed_cubebox.calculate_score()
                if team.current_cubebox_id == cubebox.cube_id:
                    cubeboxes_data += textwrap.dedent("""
                        <td class='current-cubebox'>
                        <img src="icon_playing.png" alt="X"/>
                        </td>""")
                    continue
                elif not team.has_completed_cube(cubebox.cube_id) or cubebox_score is None:
                    cubeboxes_data += "<td></td>"
                    continue
                cubebox_timestr = self.format_cubebox_completion_time(completed_cubebox.completion_time_sec)
                cubeboxes_data += textwrap.dedent(f"""
                    <td>
                        <span class="cubepoints">{cubebox_score} pts</span><br/>
                        <span class="datetime">{cubebox_timestr}</span>
                    </td>
                    """)

            team_rows += textwrap.dedent(f"""
                <tr>
                    <td class="bold-white">{i + 1}.</td>
                    <td class="bold-white">
                        <span>{team.custom_name}</span><br>
                        <span class="datetime">{self.format_datetime(team.creation_timestamp)}</span>
                    </td>
                    <td class="bold-white
                    ">{team.calculate_score()}</td>
                    <td class="bold-white
                    ">{len(team.completed_cubeboxes)}</td>
                    {cubeboxes_data}
                </tr>
                """)
        return team_rows

    @cubetry
    def format_datetime(self, timestamp: Timestamp):
        return datetime.datetime.fromtimestamp(timestamp).strftime('%b %d %Y %H:%M')

    @cubetry
    def format_cubebox_completion_time(self, secs: Seconds):
        return datetime.datetime.fromtimestamp(secs).strftime('%H:%M:%S')

    @cubetry
    def get_cubebox_css_class(self, cubebox):
        if cubebox.is_ready_to_play():
            return "available"
        elif cubebox.is_playing():
            return "occupied"
        elif cubebox.is_waiting_for_reset():
            return "waiting-for-reset"
        else:
            return ""

    def save_playing_teams_subtable_to_html_file(self, filepath: str = None):
        filepath = filepath or HIGHSCORES_PLAYING_TEAMS_SUBTABLE_FILEPATH
        with open(filepath, "w") as f:
            f.write(self.generate_html())


class CubeHighscoresSubtable:
    def __init__(self, teams: cg.CubeTeamsStatusList, title: str, max_teams: int = NB_TEAMS_PER_HIGHSCORE_SUBTABLE):
        self.teams = teams.copy()
        assert isinstance(self.teams, cg.CubeTeamsStatusList), f"self.teams is not a CubeTeamsStatusList: {self.teams}"
        self.teams.sort_by_score()
        self.title = title
        self.nb_teams = max_teams

    def generate_html(self):
        team_rows = self.generate_teams_rows()

        html_content = textwrap.dedent(f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.title}</title>
            <link rel="stylesheet" href="highscores_subtable.css">
        </head>
        <body>
        <div class="container">
            <div class="orange-line"></div>
            <div class="highscore-header">
                <img src="ribbon.png" alt="Ribbon Icon">
                <h2 class="bold-white">{self.title}</h2>
            </div>
            <div class="highscore-table">
                {team_rows}
            </div>
            <div class="orange-line-bottom"></div>
        </div>
        </body>
        </html>
        """)
        return html_content

    def generate_teams_rows(self) -> str:
        team_rows = ""
        for i, team in enumerate(self.teams):
            if i >= self.nb_teams:
                break
            team_rows += textwrap.dedent(f"""
                <div class="highscore-row">
                    <div class="col1 bold-white">{i + 1}.</div>
                    <div class="col2">
                        <span class="team-name bold-white">{team.custom_name}</span>
                        <span class="datetime">{self.format_datetime(team.creation_timestamp)}</span>
                    </div>
                    <div class="col3 bold-white">{team.calculate_score()}</div>
                </div>
                """)
        # if there werent enough teams to fill the table, fill the remaining rows with empty rows
        # use an em-dash to fill the empty rows, except the number column
        for i in range(self.nb_teams - len(self.teams)):
            team_rows += textwrap.dedent(f"""
                <div class="highscore-row">
                    <div class="col1 bold-white">{i + 1}.</div>
                    <div class="col2">
                        <span class="team-name bold-white">——————</span>
                        <span class="datetime">——————</span>
                    </div>
                    <div class="col3 bold-white">—</div>
                </div>
                """)
        return team_rows

    @staticmethod
    def format_datetime(timestamp: Timestamp):
        try:
            return datetime.datetime.fromtimestamp(timestamp).strftime('%b %d %Y %H:%M')
        except:
            return "???"

    @cubetry
    def save_subtable_to_html_file(self, filepath: str) -> bool:
        with open(filepath, "w") as f:
            f.write(self.generate_html())
        return True


class CubeHighscoresScreenManager:

    def __init__(self, playing_teams: cg.CubeTeamsStatusList, cubeboxes: cg.CubeboxesStatusList):
        self.playing_teams = playing_teams.copy()
        assert isinstance(self.playing_teams,
                          cg.CubeTeamsStatusList), f"self.teams is not a CubeTeamsStatusList: {self.playing_teams}"
        self.playing_teams.sort_by_score()
        self.cubeboxes = cubeboxes.copy()

        self._is_initialized = False
        self._last_full_update_timestamp = None
        self._last_playing_teams_update_timestamp = None

        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._keep_running = False

        self.http_server = CubeHttpServer(HIGHSCORES_DIR)

    def run(self):
        self._keep_running = True
        self._thread.start()
        self.http_server.run()

    def stop(self):
        self.http_server.stop()
        self._keep_running = False
        self._thread.join()

    def _update_loop(self):
        while self._keep_running:
            #TODO: do something here. not just periodic updates,
            # but actual checks on the game status.
            # actually no, updates shall be triggered by the cubemaster
            time.sleep(LOOP_PERIOD_SEC)

    @cubetry
    def is_time_for_full_update(self) -> bool:
        if self._last_full_update_timestamp is None:
            return True
        return time.time() - self._last_full_update_timestamp > FULL_UPDATE_PERIOD_SEC

    @cubetry
    def is_time_for_playing_teams_update(self) -> bool:
        if self._last_playing_teams_update_timestamp is None:
            return True
        return time.time() - self._last_playing_teams_update_timestamp > PLAYING_TEAMS_UPDATE_PERIOD_SEC

    # TODO: make into a class static string
    def generate_html(self, update_all=True) -> str:
        ret = textwrap.dedent(f""" 
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Highscores TheCube</title>
                <link rel="stylesheet" href="highscores_main.css">
                <script src="highscores_smart_refresh.js" defer></script>
                <!--<script src="highscores_periodic_refresh.js" defer></script>-->
            </head>
            <body>
            <div class="title">
                <img src="{TITLE_ICON_FILENAME}"/>
                HIGHSCORES
                <img src="{TITLE_ICON_FILENAME}"/>
            </div>
            <!--<div class="subtitle">THE CUBE</div>-->
            <div id="highscores" class="highscores">
                <div class="iframe-container">
                    <iframe id="highscores_left" src="{HIGHSCORES_SUBTABLE_LEFT_FILENAME}"></iframe>
                </div>
                <div class="iframe-container">
                    <iframe id="highscores_center" src="{HIGHSCORES_SUBTABLE_CENTER_FILENAME}"></iframe>
                </div>
                <div class="iframe-container">
                    <iframe id="highscores_right" src="{HIGHSCORES_SUBTABLE_RIGHT_FILENAME}"></iframe>
                </div>

            </div>
            <div class="playing-teams">
                <iframe id="playing_teams_subtable" src="{HIGHSCORES_PLAYING_TEAMS_SUBTABLE_FILENAME}"></iframe>
            </div>
            
            <!-- Hidden iframes for double buffering -->
            <iframe id="hidden_highscores_left" style="display:none;"></iframe>
            <iframe id="hidden_highscores_center" style="display:none;"></iframe>
            <iframe id="hidden_highscores_right" style="display:none;"></iframe>
            <iframe id="hidden_playing_teams" style="display:none;"></iframe>
            </body>
            
            </html>
            """)
        return ret

    def update_playing_teams_html_file(self):
        subtable = CubeHighscoresPlayingTeamsSubtable(self.playing_teams, self.cubeboxes)
        subtable.save_playing_teams_subtable_to_html_file()
        self.http_server.send_refresh_playing_teams()

    def update_highscores_html_files(self,
                                     all_time_teams: cg.CubeTeamsStatusList = None,
                                     month_teams: cg.CubeTeamsStatusList = None,
                                     week_teams: cg.CubeTeamsStatusList = None):
        """Update the highscores subtables with the given teams. If no teams are given, fetch them from the database.
        This is actually the way it's supposed to be, i'm just providing these arguments for debug"""
        if not all_time_teams:
            all_time_teams = cdb.find_teams_matching()
        if not month_teams:
            month_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_month_start_timestamp())
        if not week_teams:
            week_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_week_start_timestamp())

        CubeHighscoresSubtable(all_time_teams, "DEPUIS TOUJOURS").save_subtable_to_html_file(
            HIGHSCORES_SUBTABLE_LEFT_FILEPATH)
        CubeHighscoresSubtable(month_teams, "CE MOIS-CI").save_subtable_to_html_file(
            HIGHSCORES_SUBTABLE_CENTER_FILEPATH)
        CubeHighscoresSubtable(week_teams, "CETTE SEMAINE").save_subtable_to_html_file(
            HIGHSCORES_SUBTABLE_RIGHT_FILEPATH)
        self.http_server.send_refresh_highscores()

    @cubetry
    def save_main_html_file(self, filepath: str = None) -> bool:
        filepath = filepath or HIGHSCORES_MAIN_FILEPATH
        with open(filepath, "w") as f:
            f.write(self.generate_html())
            self._is_initialized = True
        return True



def test_CubeHighscorePlayingTeamsSubtable():
    from thecubeivazio.cubeserver_frontdesk import generate_sample_teams
    teams_status_list = generate_sample_teams()
    cubelisttest = cg.CompletedCubeboxStatusList()
    print(f"testlist {[box.cube_id for box in cubelisttest]}")
    for team in teams_status_list:
        print(f"team {team.name} : {[box.cube_id for box in team.completed_cubeboxes]}")
        print(f"team {team.name} : _ {[box.cube_id for box in team._completed_cubeboxes]}")
    # exit(0)
    cubeboxes = cg.CubeboxesStatusList()
    for box in cubeboxes:
        for team in teams_status_list:
            if team.current_cubebox_id == box.cube_id:
                box.set_state_playing()
            else:
                # randomly set as ready to play or waiting for reset
                if random.choice([True, False]):
                    box.set_state_ready_to_play()
                else:
                    box.set_state_waiting_for_reset()

    cube_highscore_screen = CubeHighscoresPlayingTeamsSubtable(teams_status_list, cubeboxes)
    filepath = os.path.join("scores_screen", "test_playing_teams_subtable.html")
    cube_highscore_screen.save_playing_teams_subtable_to_html_file(filepath)


def test_CubeHighscoreSubtable():
    from thecubeivazio import cube_database as cdb
    all_time_teams = cdb.find_teams_matching()
    month_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_month_start_timestamp())
    week_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_week_start_timestamp())

    highscores_all_time = CubeHighscoresSubtable(all_time_teams, "DEPUIS TOUJOURS")
    highscores_month = CubeHighscoresSubtable(month_teams, "CE MOIS-CI")
    highscores_week = CubeHighscoresSubtable(week_teams, "CETTE SEMAINE")

    highscores_all_time.save_subtable_to_html_file(os.path.join("scores_screen", "test_highscores_all_time.html"))
    highscores_month.save_subtable_to_html_file(os.path.join("scores_screen", "test_highscores_month.html"))
    highscores_week.save_subtable_to_html_file(os.path.join("scores_screen", "test_highscores_week.html"))


def test_CubeHighscoreScreen():
    from thecubeivazio import cube_database as cdb
    teams = cdb.find_teams_matching()
    cubeboxes = cg.CubeboxesStatusList()
    cube_highscore_screen = CubeHighscoresScreenManager(teams, cubeboxes)
    cube_highscore_screen.save_main_html_file(os.path.join("scores_screen", "test_highscores_screen.html"))


def test_run():
    playing_teams_1 = cfd.generate_sample_teams()
    playing_teams_1[0].current_cubebox_id = 1
    cubeboxes_1 = cg.CubeboxesStatusList()

    playing_teams_2 = playing_teams_1.copy()
    playing_teams_2[0].completed_cubeboxes[0].win_timestamp += 100
    playing_teams_2[1].completed_cubeboxes[0].win_timestamp += 100
    playing_teams_2[2].current_cubebox_id = 2
    completed_cubeboxes_2 = playing_teams_1[0].completed_cubeboxes.copy()
    for box in completed_cubeboxes_2:
        playing_teams_2[2].completed_cubeboxes.update_from_cubebox(box)

    cubeboxes_2 = cg.CubeboxesStatusList()
    for box in cubeboxes_1:
        roll = random.choice([1, 2, 3, 4, 5])
        if roll < 3:
            box.set_state_ready_to_play()
        elif roll == 4:
            box.set_state_playing()
        else:
            box.set_state_waiting_for_reset()

    cube_highscore_screen = CubeHighscoresScreenManager(playing_teams_1, cubeboxes_1)
    cube_highscore_screen.save_main_html_file()
    cube_highscore_screen.run()
    try:
        print("beginning loop")
        while True:
            cube_highscore_screen.playing_teams = playing_teams_2
            cube_highscore_screen.cubeboxes = cubeboxes_2
            time.sleep(0.5)
            cube_highscore_screen.update_playing_teams_html_file()
            time.sleep(0.5)
            cube_highscore_screen.update_highscores_html_files(
                all_time_teams=playing_teams_2,
                month_teams=playing_teams_1,
                week_teams=playing_teams_1,
            )
            cube_highscore_screen.playing_teams = playing_teams_1
            cube_highscore_screen.cubeboxes = cubeboxes_1
            # cube_highscore_screen.save_to_html_file()
            cube_highscore_screen.update_playing_teams_html_file()
            time.sleep(0.5)
            cube_highscore_screen.update_highscores_html_files()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    finally:
        cube_highscore_screen.stop()


if __name__ == "__main__":
    # test_CubeHighscorePlayingTeamsSubtable()
    # test_CubeHighscoreSubtable()
    # test_CubeHighscoreScreen()
    # filepath = os.path.join(HIGHSCORES_DIR, "test_highscores_screen.html")
    # launch_chromium(filepath)
    test_run()
