"""File for the mixin class (partial for CubeGuiForm) for the teams management tab."""

import time

from PyQt5 import QtGui
from PyQt5.QtCore import QFile
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QTableWidgetItem
from cubegui_ui import Ui_Form

from thecubeivazio import cube_game
from thecubeivazio import cube_utils
from thecubeivazio import cube_logger as cube_logger
from thecubeivazio import cube_database as cubedb

from thecubeivazio.cube_common_defines import *
import sys

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cubegui import CubeGuiForm


# _noinspection PyUnresolvedReferences
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

        # clear and setup the results table
        self.ui.tableTeamsResults.clearContents()
        self.ui.tableTeamsResults.cellClicked.connect(self.on_teams_results_cell_clicked)


        # fill the trophy combo box
        trophies = self.fd.config.all_trophies
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

    @cubetry
    def get_trophy_pixmap(self, trophy: cube_game.CubeTrophy, width: int=None, height: int=None) -> QtGui.QPixmap:
        """Get the pixmap for a trophy"""
        assert trophy
        assert QFile.exists(trophy.image_filepath)
        pixmap = QtGui.QPixmap(trophy.image_filepath)
        if not pixmap:
            pixmap = QtGui.QPixmap(DEFAULT_TROPHY_IMAGE_FILEPATH)
        if width and height:
            pixmap = pixmap.scaled(width, height)
        assert pixmap
        return pixmap

    @cubetry
    def on_teams_results_cell_clicked(self, row, col):
        self.ui: Ui_Form
        self.log: cube_logger.CubeLogger
        table = self.ui.tableTeamsTrophyList
        table.clearContents()

        # identify the team from the row of the cell clicked
        team_creation_timestamp_text = self.ui.tableTeamsResults.item(row, 0).text()
        self.log.debug(f"team_creation_timestamp_text: {team_creation_timestamp_text}")
        team_creation_timestamp = float(team_creation_timestamp_text)
        team = cubedb.find_team_by_creation_timestamp(team_creation_timestamp)
        if not team:
            self.log.error(f"Could not find team with creation timestamp {team_creation_timestamp}")
            return
        self.log.debug(f"Selected team: {team}")
        # update the trophies table
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Trophée", "Image", "Points", "Description"])
        table.setRowCount(len(team.trophies_names))
        for i, trophy_name in enumerate(team.trophies_names):
            trophy = cube_game.CubeTrophy.make_from_name(trophy_name)
            if not trophy:
                self.log.error(f"Could not find trophy with name {trophy_name}")
                continue
            trophy_pixmap = self.get_trophy_pixmap(trophy, width=20, height=20)
            self.log.debug(f"trophy_pixmap: {trophy_pixmap}")
            # Create an icon from the QPixmap
            icon = QIcon(trophy_pixmap)
            # Create a QTableWidgetItem and set the icon
            trophy_pixmap_item = QTableWidgetItem()
            trophy_pixmap_item.setIcon(icon)
            table.setItem(i, 0, QTableWidgetItem(str(trophy.name)))
            table.setItem(i, 1, trophy_pixmap_item)
            table.setItem(i, 2, QTableWidgetItem(str(trophy.points)))
            table.setItem(i, 3, QTableWidgetItem(str(trophy.description)))
        total_row_height = sum(table.rowHeight(row) for row in range(table.rowCount()))
        total_row_height += table.horizontalHeader().height() + 2
        max_row_height = 5*table.rowHeight(0) + table.horizontalHeader().height() + 2
        table.setFixedHeight(min(total_row_height, max_row_height))



    def on_spinTeamsAmountOfDays_valueChanged(self, value):
        """Check the radio button when the spinbox value is changed"""
        self.ui: Ui_Form
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
            ["CrTmstmp", "Date", "Nom", "Nom personnalisé", "Score", "Cubes faits", "Trophées", "Création", "Début", "Fin", "RFID"])
        self.ui.tableTeamsResults.setRowCount(len(teams))

        for i, team in enumerate(teams):
            #french_date = cube_utils.timestamp_to_french_date(team.start_timestamp)
            short_date = cube_utils.timestamp_to_date(team.start_timestamp)
            creation_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.creation_timestamp, separators=":", secs=False)
            start_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.start_timestamp, separators=":", secs=False)
            end_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.end_timestamp, separators=":", secs=False)
            trophies_str = ", ".join((trophy_name for trophy_name in team.trophies_names))

            # print(f"team: {team}")
            self.ui.tableTeamsResults.setItem(i, 0, QTableWidgetItem(str(team.creation_timestamp)))
            self.log.debug(f"team.creation_timestamp: {team.name} : {team.creation_timestamp} : {self.ui.tableTeamsResults.item(i, 0).text()}")
            self.ui.tableTeamsResults.setItem(i, 1, QTableWidgetItem(short_date))
            self.ui.tableTeamsResults.setItem(i, 2, QTableWidgetItem(team.name))
            self.ui.tableTeamsResults.setItem(i, 3, QTableWidgetItem(team.custom_name))
            self.ui.tableTeamsResults.setItem(i, 4, QTableWidgetItem(str(team.calculate_score())))
            self.ui.tableTeamsResults.setItem(i, 5, QTableWidgetItem(str(team.completed_cubebox_ids)))
            self.ui.tableTeamsResults.setItem(i, 6, QTableWidgetItem(trophies_str))
            self.ui.tableTeamsResults.setItem(i, 7, QTableWidgetItem(creation_tod))
            self.ui.tableTeamsResults.setItem(i, 8, QTableWidgetItem(start_tod))
            self.ui.tableTeamsResults.setItem(i, 9, QTableWidgetItem(end_tod))
            self.ui.tableTeamsResults.setItem(i, 10, QTableWidgetItem(team.rfid_uid))

        self.ui.tableTeamsResults.hideColumn(0)
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
    window.ui.spinTeamsAmountOfDays.setValue(100)
    window.click_search_teams()

    sys.exit(app.exec_())

