"""File for the mixin class (partial for CubeGuiForm) for the teams management tab."""

import threading
import time

from PyQt5 import QtGui
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from cubegui_ui import Ui_Form

from thecubeivazio import cubeserver_frontdesk as cfd, cube_game, cube_utils
from thecubeivazio import cube_logger as cube_logger
from thecubeivazio.cube_common_defines import *
import sys
import atexit
import traceback as tb

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cubegui import CubeGuiForm


class CubeGuiTabTeamsMixin:

    def setup_tab_teams(self: 'CubeGuiForm'):
        self.ui: Ui_Form

        # fill the team names combo box
        team_names = [""]  # empty string for "all teams"
        team_names.extend(self.fd.config.team_names)
        # print(team_names)
        self.ui.comboTeamsTeamName.clear()
        self.ui.comboTeamsTeamName.addItems(team_names)

        # clear the RFID line edit
        self.ui.lineTeamsRfid.clear()

        # select the default radio button to "today"
        self.ui.radioTeamsToday.setChecked(True)

        # connect the "search" button
        self.ui.btnTeamsSearch.clicked.connect(self.search_teams)

        # fill the trophy combo box
        trophies = self.fd.config.trophies
        self.ui.comboTeamsAddTrophy.clear()
        self.ui.comboTeamsAddTrophy.addItems((t.name for t in trophies))

        # connect the "add trophy" button
        self.ui.btnTeamsAddTrophy.clicked.connect(self.add_trophy)

        # connect the "remove trophy" button
        self.ui.btnTeamsRemoveSelectedTrophy.clicked.connect(self.remove_trophy)

        # clear the trophy table
        self.ui.tableTeamsTrophyList.clearContents()

        # connect the "print scoresheet" button
        self.ui.btnTeamsPrintScoresheet.clicked.connect(self.print_scoresheet)

        # update the tab
        self.update_tab_teams()

    def update_tab_teams(self: 'CubeGuiForm'):
        pass

    def print_scoresheet(self: 'CubeGuiForm'):
        pass

    def add_trophy(self: 'CubeGuiForm'):
        pass

    def remove_trophy(self: 'CubeGuiForm'):
        pass

    def search_teams(self: 'CubeGuiForm'):
        self.ui: Ui_Form

        team_name = self.ui.comboTeamsTeamName.currentText()
        custom_name: str = self.ui.lineTeamsCustomName.text()
        rfid_uid = self.ui.lineTeamsRfid.text()
        search_currently_playing = self.ui.radioTeamsCurrentlyPlaying.isChecked()
        self.log.info(f"Searching teams matching: name={team_name}, custom_name={custom_name}, "
                      f"rfid={rfid_uid}, currently_playing={search_currently_playing}")

        # get the search parameters

        if self.ui.radioTeamsToday.isChecked():
            start_timestamp = cube_utils.today_start_timestamp()
        elif self.ui.radioTeamsThisWeek.isChecked():
            start_timestamp = cube_utils.this_week_start_timestamp()
        elif self.ui.radioTeamsThisMonth.isChecked():
            start_timestamp = cube_utils.this_month_start_timestamp()
        else:
            start_timestamp = 1  # not 0 to avoid erroneous null checks
        self.log.debug(f"start_timestamp: {start_timestamp}, i.e. {cube_utils.timestamp_to_french_date(start_timestamp)}")

        # if we're looking for a team currently playing, search fd.teams
        if search_currently_playing:
            teams = self.fd.teams
            self.log.info(f"Searching currently playing teams: {teams}")
        else:
            # search the teams in the database
            teams = cube_game.CubeTeamsStatusList()
            teams.load_from_json_file(TEAMS_DATABASE_FILEPATH)
            self.log.info(f"Searching teams in the database: {teams}")

        # find matching teams: name, custom_name, rfid, and timestamp
        matching_teams = []
        for team in teams:
            if team_name and team_name != team.name:
                continue
            if custom_name and str.lower(custom_name) in str.lower(team.custom_name):
                continue
            if rfid_uid and rfid_uid != team.rfid_uid:
                continue
            if start_timestamp and team.start_timestamp < start_timestamp:
                continue
            matching_teams.append(team)

        self.ui.tableTeamsResults.clearContents()
        self.ui.tableTeamsResults.setColumnCount(9)
        self.ui.tableTeamsResults.setHorizontalHeaderLabels(
            ["Date", "Nom", "Nom personnalisé", "Score", "Cubes faits", "Trophées", "Début", "Fin", "RFID"])
        self.ui.tableTeamsResults.setRowCount(len(matching_teams))

        for i, team in enumerate(matching_teams):
            french_date = cube_utils.timestamp_to_french_date(team.start_timestamp)
            start_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.start_timestamp, separators=":", secs=False)
            end_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.end_timestamp, separators=":", secs=False)
            trophies_str = "".join(["🏆" for t in team.trophies])
            trophies_str = ",".join([t.name for t in team.trophies])
            print(f"team: {team}")
            self.ui.tableTeamsResults.setItem(i, 0, QTableWidgetItem(french_date))
            self.ui.tableTeamsResults.setItem(i, 1, QTableWidgetItem(team.name))
            self.ui.tableTeamsResults.setItem(i, 2, QTableWidgetItem(team.custom_name))
            self.ui.tableTeamsResults.setItem(i, 3, QTableWidgetItem(str(team.calculate_score())))
            self.ui.tableTeamsResults.setItem(i, 4, QTableWidgetItem(str(team.completed_cubebox_ids)))
            self.ui.tableTeamsResults.setItem(i, 5, QTableWidgetItem(trophies_str))
            self.ui.tableTeamsResults.setItem(i, 6, QTableWidgetItem(start_tod))
            self.ui.tableTeamsResults.setItem(i, 7, QTableWidgetItem(end_tod))
            self.ui.tableTeamsResults.setItem(i, 8, QTableWidgetItem(team.rfid_uid))
        # Resize columns to fit contents and headers
        self.ui.tableTeamsResults.resizeColumnsToContents()

if __name__ == "__main__":
    from cubegui import CubeGuiForm
    app = QApplication(sys.argv)
    window = CubeGuiForm()
    window.show()
    sys.exit(app.exec_())