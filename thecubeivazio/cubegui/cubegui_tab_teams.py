"""File for the mixin class (partial for CubeGuiForm) for the new team tab."""

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
        team_names = [""] # empty string for "all teams"
        team_names.extend(self.fd.config.team_names)
        print(team_names)
        self.ui.comboTeamsTeamName.clear()
        self.ui.comboTeamsTeamName.addItems(team_names)

        # clear the RFID line edit
        self.ui.lineTeamsRfid.clear()

        # select the default radio button to "today"
        self.ui.radioTeamsToday.setChecked(True)

        # connect the "search" button
        self.ui.btnTeamsSearch.clicked.connect(self.search_teams)

        # clear the search results list
        self.ui.listTeamsSearchResults.clear()

        # clear the team info table
        self.ui.tableTeamsTeamInfo.clearContents()

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
        self.update_teams_info_table()

    def print_scoresheet(self: 'CubeGuiForm'):
        pass
    def add_trophy(self: 'CubeGuiForm'):
        pass
    def remove_trophy(self: 'CubeGuiForm'):
        pass


    def search_teams(self: 'CubeGuiForm'):
        self.ui: Ui_Form

        team_name = self.ui.comboTeamsTeamName.currentText()
        custom_name:str = self.ui.lineTeamsCustomName.text()
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

        # if we're looking for a team currently playing, search fd.teams
        if search_currently_playing:
            teams = self.fd.teams
        else:
            # search the teams in the database
            teams = cube_game.CubeTeamsStatusList()
            teams.load_from_json_file(PAST_TEAMS_JSON_DATABASE)

        # find matching teams: name, custom_name, rfid, and timestamp
        matching_teams = []
        for team in teams:
            if team_name and team_name != team.name:
                continue
            if custom_name and str.lower(custom_name) in str.lower(team.custom_name):
                continue
            if rfid_uid and rfid_uid != team.rfid_uid:
                continue
            if start_timestamp and team.start_timestamp > start_timestamp:
                continue
            matching_teams.append(team)

        # display the search results in the list
        # Format : name - custom_name : french_dat : hhhmm_start -> hhmm_end : points
        self.ui.listTeamsSearchResults.clear()

        for team in matching_teams:
            french_date = cube_utils.timestamp_to_french_date(team.start_timestamp)
            start_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(team.start_timestamp, separators=":", secs=False)
            end_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(team.end_timestamp, separators=":", secs=False)
            self.ui.listTeamsSearchResults.addItem(
                f"{team.name} - {team.custom_name} : {french_date} : "
                f"{start_tod} -> {start_tod} : {team.calculate_score()} points")

        # if there are results, select the first one
        if matching_teams:
            self.ui.listTeamsSearchResults.setCurrentRow(0)
            self.ui.tableTeamsResults.clearContents()
            self.ui.tableTeamsResults.setColumnCount(9)
            # columns : date, name, custom_name, score, completed cubes, trophies, start time, end time, rfid uid
            self.ui.tableTeamsResults.setHorizontalHeaderLabels([
                "Date", "Nom", "Nom personnalisé", "Score", "Cubes faits", "Trophées", "Début", "Fin", "RFID UID"])


            self.ui.tableTeamsResults.setRowCount(len(matching_teams))

            for i, team in enumerate(matching_teams):
                french_date = cube_utils.timestamp_to_french_date(team.start_timestamp)
                start_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(team.start_timestamp, separators=":", secs=False)
                end_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(team.end_timestamp, separators=":", secs=False)
                trophies_names = [t.name for t in team.trophies]
                self.ui.tableTeamsResults.setItem(i, 0, QTableWidgetItem(french_date))
                self.ui.tableTeamsResults.setItem(i, 1, QTableWidgetItem(team.name))
                self.ui.tableTeamsResults.setItem(i, 2, QTableWidgetItem(team.custom_name))
                self.ui.tableTeamsResults.setItem(i, 3, QTableWidgetItem(str(team.calculate_score())))
                self.ui.tableTeamsResults.setItem(i, 4, QTableWidgetItem(str(team.completed_cubebox_ids)))
                self.ui.tableTeamsResults.setItem(i, 5, QTableWidgetItem(", ".join(trophies_names)))
                self.ui.tableTeamsResults.setItem(i, 6, QTableWidgetItem(start_tod))
                self.ui.tableTeamsResults.setItem(i, 7, QTableWidgetItem(end_tod))
                self.ui.tableTeamsResults.setItem(i, 8, QTableWidgetItem(team.rfid_uid))




        # update this tab so as to display the selected team's info in the table
        self.update_teams_info_table()


    def update_teams_info_table(self: 'CubeGuiForm'):
        # get the selected team in the list
        selected_row = self.ui.listTeamsSearchResults.currentRow()
        print(f"selected_row: {selected_row}")
        if selected_row < 0 or selected_row >= len(self.fd.teams):
            return
        team = self.fd.teams[selected_row]

        # fill the team info table. Rows:
        # - Nom
        # - Nom personnalisé
        # - Date
        # - Score
        # - Cubes faits
        # - Trophées
        # - Durée
        # - Heure début
        # - Heure fin
        # - RFID UID
        self.ui.tableTeamsTeamInfo.clearContents()
        self.ui.tableTeamsTeamInfo.setRowCount(10)
        self.ui.tableTeamsTeamInfo.setColumnCount(2)

        french_date = cube_utils.timestamp_to_french_date(team.start_timestamp)
        start_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(team.start_timestamp, separators=":", secs=False)
        end_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(team.end_timestamp, separators=":", secs=False)
        trophies_names = [t.name for t in team.trophies]

        self.ui.tableTeamsTeamInfo.setItem(0, 0, QTableWidgetItem("Nom"))
        self.ui.tableTeamsTeamInfo.setItem(0, 1, QTableWidgetItem(team.name))
        self.ui.tableTeamsTeamInfo.setItem(1, 0, QTableWidgetItem("Nom personnalisé"))
        self.ui.tableTeamsTeamInfo.setItem(1, 1, QTableWidgetItem(team.custom_name))
        self.ui.tableTeamsTeamInfo.setItem(2, 0, QTableWidgetItem("Date"))
        self.ui.tableTeamsTeamInfo.setItem(2, 1, QTableWidgetItem(french_date))
        self.ui.tableTeamsTeamInfo.setItem(3, 0, QTableWidgetItem("Score"))
        self.ui.tableTeamsTeamInfo.setItem(3, 1, QTableWidgetItem(str(team.calculate_score())))
        self.ui.tableTeamsTeamInfo.setItem(4, 0, QTableWidgetItem("Durée"))
        self.ui.tableTeamsTeamInfo.setItem(4, 1, QTableWidgetItem(cube_utils.seconds_to_hhmmss_string(team.allocated_time)))
        self.ui.tableTeamsTeamInfo.setItem(5, 0, QTableWidgetItem("Cubes faits"))
        self.ui.tableTeamsTeamInfo.setItem(5, 1, QTableWidgetItem(str(team.completed_cubebox_ids)))
        self.ui.tableTeamsTeamInfo.setItem(6, 0, QTableWidgetItem("Trophées"))
        self.ui.tableTeamsTeamInfo.setItem(6, 1, QTableWidgetItem(", ".join(trophies_names)))
        self.ui.tableTeamsTeamInfo.setItem(7, 0, QTableWidgetItem("Heure début"))
        self.ui.tableTeamsTeamInfo.setItem(7, 1, QTableWidgetItem(start_tod))
        self.ui.tableTeamsTeamInfo.setItem(8, 0, QTableWidgetItem("Heure fin"))
        self.ui.tableTeamsTeamInfo.setItem(8, 1, QTableWidgetItem(end_tod))
        self.ui.tableTeamsTeamInfo.setItem(9, 0, QTableWidgetItem("RFID UID"))
        self.ui.tableTeamsTeamInfo.setItem(9, 1, QTableWidgetItem(team.rfid_uid))

        QApplication.processEvents()
