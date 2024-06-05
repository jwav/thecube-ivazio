"""File for the mixin class (partial for CubeGuiForm) for the teams management tab."""

import threading
import time

from PyQt5 import QtGui
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from cubegui_ui import Ui_Form

from thecubeivazio import cubeserver_frontdesk as cfd
from thecubeivazio import cube_game
from thecubeivazio import cube_utils
from thecubeivazio import cube_logger as cube_logger
from thecubeivazio import cube_database as cubedb

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

        # select the default radio button for the search period
        # self.ui.radioTeamsCurrentlyPlaying.setChecked(True)
        self.ui.spinTeamsAmountOfDays.valueChanged.connect(lambda value: self.ui.radioTeamsLessThanXDays.setChecked(True))
        self.ui.radioTeamsCurrentlyPlaying.setChecked(True)

        # connect the "search" button
        self.ui.btnTeamsSearch.clicked.connect(self.click_search_teams)

        # fill the trophy combo box
        trophies = self.fd.config.trophies
        self.ui.comboTeamsAddTrophy.clear()
        self.ui.comboTeamsAddTrophy.addItems((t.name for t in trophies))

        # connect the "add trophy" button
        self.ui.btnTeamsAddTrophy.clicked.connect(self.click_add_trophy)

        # connect the "remove trophy" button
        self.ui.btnTeamsRemoveSelectedTrophy.clicked.connect(self.click_remove_trophy)

        # clear the trophy table
        self.ui.tableTeamsTrophyList.clearContents()

        # connect the "print scoresheet" button
        self.ui.btnTeamsPrintScoresheet.clicked.connect(self.click_print_scoresheet)

        # update the tab
        self.update_tab_teams()

    def on_spinTeamsAmountOfDays_valueChanged(self, value):
        # Check the radio button when the spinbox value is changed
        self.ui.radioTeamsLessThanXDays.setChecked(True)

    def update_tab_teams(self: 'CubeGuiForm'):
        pass

    def click_print_scoresheet(self: 'CubeGuiForm'):
        pass

    def click_add_trophy(self: 'CubeGuiForm'):
        pass

    @cubetry
    def click_remove_trophy(self: 'CubeGuiForm'):
        pass

    @cubetry
    def click_search_teams(self: 'CubeGuiForm'):
        self.ui: Ui_Form
        # assert False
        team_name = self.ui.comboTeamsTeamName.currentText()
        custom_name: str = self.ui.lineTeamsCustomName.text()
        rfid_uid = self.ui.lineTeamsRfid.text()

        if self.ui.radioTeamsCurrentlyPlaying.isChecked():
            # TODO: query current teams from the cubemaster
            # TODO: apply filters?
            matching_teams = self.fd.teams
        else:
            nb_days = self.ui.spinTeamsAmountOfDays.value()
            min_timestamp = time.time() - nb_days * 24 * 3600
            self.log.debug(f"min_timestamp: {min_timestamp}, i.e. {cube_utils.timestamp_to_date(min_timestamp)}")
            matching_teams = cubedb.find_teams_matching(name=team_name, custom_name=custom_name, rfid_uid=rfid_uid,
                                               min_creation_timestamp=min_timestamp, max_creation_timestamp=time.time())

        self.display_teams(matching_teams)

    @cubetry
    def display_teams(self, teams: cube_game.CubeTeamsStatusList):
        self.ui: Ui_Form

        if not teams:
            self.log.info("No matching teams found.")
            teams = cube_game.CubeTeamsStatusList()
        if not teams.is_valid():
            self.log.error("Invalid teams list.")
            return

        self.ui.tableTeamsResults.clearContents()
        self.ui.tableTeamsResults.setColumnCount(9)
        self.ui.tableTeamsResults.setHorizontalHeaderLabels(
            ["Date", "Nom", "Nom personnalisé", "Score", "Cubes faits", "Trophées", "Création", "Début", "Fin", "RFID"])
        self.ui.tableTeamsResults.setRowCount(len(teams))

        for i, team in enumerate(teams):
            french_date = cube_utils.timestamp_to_french_date(team.start_timestamp)
            short_date = cube_utils.timestamp_to_date(team.start_timestamp)
            creation_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.creation_timestamp, separators=":", secs=False)
            start_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.start_timestamp, separators=":", secs=False)
            end_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.end_timestamp, separators=":", secs=False)
            trophies_str = "".join(["🏆" for t in team.trophies])
            trophies_str = ",".join([t.name for t in team.trophies])
            print(f"team: {team}")
            self.ui.tableTeamsResults.setItem(i, 0, QTableWidgetItem(short_date))
            self.ui.tableTeamsResults.setItem(i, 1, QTableWidgetItem(team.name))
            self.ui.tableTeamsResults.setItem(i, 2, QTableWidgetItem(team.custom_name))
            self.ui.tableTeamsResults.setItem(i, 3, QTableWidgetItem(str(team.calculate_score())))
            self.ui.tableTeamsResults.setItem(i, 4, QTableWidgetItem(str(team.completed_cubebox_ids)))
            self.ui.tableTeamsResults.setItem(i, 5, QTableWidgetItem(trophies_str))
            self.ui.tableTeamsResults.setItem(i, 6, QTableWidgetItem(creation_tod))
            self.ui.tableTeamsResults.setItem(i, 7, QTableWidgetItem(start_tod))
            self.ui.tableTeamsResults.setItem(i, 8, QTableWidgetItem(end_tod))
            self.ui.tableTeamsResults.setItem(i, 9, QTableWidgetItem(team.rfid_uid))
        # Resize columns to fit contents and headers
        self.ui.tableTeamsResults.resizeColumnsToContents()


if __name__ == "__main__":
    from cubegui import CubeGuiForm
    import atexit
    app = QApplication(sys.argv)
    window = CubeGuiForm()
    atexit.register(window.close)
    window.show()

    window.ui.tabWidget.setCurrentIndex(1)
    window.click_search_teams()

    sys.exit(app.exec_())

