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

HIGHSCORES_SUBTABLE_LEFT_FILEPATH = os.path.join(HIGHSCORES_DIR, "highscores_subtable_left.html")
HIGHSCORES_SUBTABLE_CENTER_FILEPATH = os.path.join(HIGHSCORES_DIR, "highscores_subtable_center.html")
HIGHSCORES_SUBTABLE_RIGHT_FILEPATH = os.path.join(HIGHSCORES_DIR, "highscores_subtable_right.html")
HIGHSCORES_PLAYING_TEAMS_SUBTABLE_FILEPATH = os.path.join(HIGHSCORES_DIR, "playing_teams_subtable.html")
HIGHSCORES_MAIN_FILEPATH = os.path.join(HIGHSCORES_DIR, "highscores_main.html")
BROWSER_NAMES = ['brave', 'chromium', 'firefox']
PLAYING_TEAMS_UPDATE_PERIOD_SEC = 5
FULL_UPDATE_PERIOD_SEC = 30
DEFAULT_BROWSER_NAME = "brave"

import webbrowser
import psutil


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

class CubeHighscorePlayingTeamsSubtable:
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
                if not team.has_completed_cube(cubebox.cube_id) or cubebox_score is None:
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


class CubeHighscoreSubtable:
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


class CubeHighscoreScreen:
    HEAD_HTML = textwrap.dedent("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Highscores TheCube</title>
            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Roboto+Slab:wght@700&family=Saira+Condensed:wght@400&display=swap" rel="stylesheet">
            <link rel="stylesheet" href="highscores_main.css">
            <!-- TOO MUCH FLICKER -->
            <!--<meta http-equiv="refresh" content="1">-->
        </head>
        """)

    def __init__(self, playing_teams: cg.CubeTeamsStatusList, cubeboxes: cg.CubeboxesStatusList):
        self.playing_teams = playing_teams.copy()
        assert isinstance(self.playing_teams,
                          cg.CubeTeamsStatusList), f"self.teams is not a CubeTeamsStatusList: {self.playing_teams}"
        self.playing_teams.sort_by_score()
        self.cubeboxes = cubeboxes.copy()
        self.highscores_subtable_left_filepath = HIGHSCORES_SUBTABLE_LEFT_FILEPATH
        self.highscores_subtable_center_filepath = HIGHSCORES_SUBTABLE_CENTER_FILEPATH
        self.highscores_subtable_right_filepath = HIGHSCORES_SUBTABLE_RIGHT_FILEPATH
        self.playing_teams_subtable_filepath = HIGHSCORES_PLAYING_TEAMS_SUBTABLE_FILEPATH
        self.title_icon_filepath = os.path.join(IMAGES_DIR, "icon_thecube_dark_396x395.png")
        self._is_initialized = False
        self._last_full_update_timestamp = None
        self._last_playing_teams_update_timestamp = None
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._keep_running = False

    def run(self):
        self._keep_running = True
        self._thread.start()

    def stop(self):
        self._keep_running = False
        self._thread.join()

    def _update_loop(self):
        while self._keep_running:
            if any((self.is_time_for_full_update(),
                    self.is_time_for_playing_teams_update(),
                    not self._is_initialized)):
                full_update = self.is_time_for_full_update()
                result = self.save_to_html_file(full_update=self.is_time_for_full_update())
                if not result:
                    continue
                if full_update:
                    self._last_full_update_timestamp = time.time()
                self._last_playing_teams_update_timestamp = time.time()
                self.refresh_browser()
            time.sleep(LOOP_PERIOD_SEC)

    def refresh_browser(self):
        refresh_chromium()

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

    def generate_html(self, update_all=True) -> str:
        if update_all or not self._is_initialized:
            all_time_teams = cdb.find_teams_matching()
            month_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_month_start_timestamp())
            week_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_week_start_timestamp())
            CubeHighscoreSubtable(all_time_teams, "DEPUIS TOUJOURS").save_subtable_to_html_file(
                self.highscores_subtable_left_filepath)
            CubeHighscoreSubtable(month_teams, "CE MOIS-CI").save_subtable_to_html_file(
                self.highscores_subtable_center_filepath)
            CubeHighscoreSubtable(week_teams, "CETTE SEMAINE").save_subtable_to_html_file(
                self.highscores_subtable_right_filepath)

        CubeHighscorePlayingTeamsSubtable(self.playing_teams, self.cubeboxes).save_playing_teams_subtable_to_html_file(
            self.playing_teams_subtable_filepath)
        ret = textwrap.dedent(f""" 
            {self.HEAD_HTML}
            <body>
            <div class="title">
                <img src="{self.title_icon_filepath}"/>
                HIGHSCORES
                <img src="{self.title_icon_filepath}"/>
            </div>
            <!--<div class="subtitle">THE CUBE</div>-->
            <div class="highscores">
                <div class="iframe-container">
                    <iframe src="{self.highscores_subtable_left_filepath}"></iframe>
                </div>
                <div class="iframe-container">
                    <iframe src="{self.highscores_subtable_right_filepath}"></iframe>
                </div>
                <div class="iframe-container">
                    <iframe src="{self.highscores_subtable_right_filepath}"></iframe>
                </div>

            </div>
            <div class="playing-teams">
                <iframe src="{self.playing_teams_subtable_filepath}"></iframe>
            </div>
            </body>
            
            </html>
            """)
        self._is_initialized = True
        return ret

    @cubetry
    def save_to_html_file(self, filepath: str = None) -> bool:
        filepath = filepath or HIGHSCORES_MAIN_FILEPATH
        with open(filepath, "w") as f:
            f.write(self.generate_html())
        return True

    def launch_browser(self, browser_name: str) -> bool:
        """check that the browser is not already open, if it is, do nothing, if it is not, open the browser.
        Returns True if success"""
        import subprocess


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

    cube_highscore_screen = CubeHighscorePlayingTeamsSubtable(teams_status_list, cubeboxes)
    filepath = os.path.join("scores_screen", "test_playing_teams_subtable.html")
    cube_highscore_screen.save_playing_teams_subtable_to_html_file(filepath)


def test_CubeHighscoreSubtable():
    from thecubeivazio import cube_database as cdb
    all_time_teams = cdb.find_teams_matching()
    month_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_month_start_timestamp())
    week_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_week_start_timestamp())

    highscores_all_time = CubeHighscoreSubtable(all_time_teams, "DEPUIS TOUJOURS")
    highscores_month = CubeHighscoreSubtable(month_teams, "CE MOIS-CI")
    highscores_week = CubeHighscoreSubtable(week_teams, "CETTE SEMAINE")

    highscores_all_time.save_subtable_to_html_file(os.path.join("scores_screen", "test_highscores_all_time.html"))
    highscores_month.save_subtable_to_html_file(os.path.join("scores_screen", "test_highscores_month.html"))
    highscores_week.save_subtable_to_html_file(os.path.join("scores_screen", "test_highscores_week.html"))


def test_CubeHighscoreScreen():
    from thecubeivazio import cube_database as cdb
    teams = cdb.find_teams_matching()
    cubeboxes = cg.CubeboxesStatusList()
    cube_highscore_screen = CubeHighscoreScreen(teams, cubeboxes)
    cube_highscore_screen.save_to_html_file(os.path.join("scores_screen", "test_highscores_screen.html"))

def test_run():
    playing_teams_1 = cfd.generate_sample_teams()
    playing_teams_2 = playing_teams_1.copy()
    playing_teams_2[0].completed_cubeboxes[0].win_timestamp += 100
    cubeboxes = cg.CubeboxesStatusList()
    cube_highscore_screen = CubeHighscoreScreen(playing_teams_1, cubeboxes)
    cube_highscore_screen.run()
    try:
        while True:
            time.sleep(1)
            cube_highscore_screen.playing_teams = playing_teams_2
            time.sleep(1)
            cube_highscore_screen.playing_teams = playing_teams_1
    except KeyboardInterrupt:
        pass
    finally:
        cube_highscore_screen.stop()

if __name__ == "__main__":
    # test_CubeHighscorePlayingTeamsSubtable()
    # test_CubeHighscoreSubtable()
    # test_CubeHighscoreScreen()
    # filepath = os.path.join(HIGHSCORES_DIR, "test_highscores_screen.html")
    # launch_chromium(filepath)
    test_run()
