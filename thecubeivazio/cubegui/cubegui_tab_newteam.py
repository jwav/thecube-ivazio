"""File for the mixin class (partial for CubeGuiForm) for the new team tab."""

import threading
import time

from PyQt5 import QtGui
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication, QMainWindow
from cubegui_ui import Ui_Form

from thecubeivazio import cubeserver_frontdesk as cfd, cube_game, cube_utils
from thecubeivazio import cube_logger as cube_logger

import sys
import atexit
import traceback as tb


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cubegui import CubeGuiForm

class CubeGuiTabNewTeamMixin:
    def setup_tab_newteam(self: 'CubeGuiForm'):
        """Sets up the widgets of the tab 'Créer une nouvelle équipe'"""

        # fill the team names combo box
        team_names = self.fd.config.team_names
        self.ui.comboNewteamTeamName.clear()
        self.ui.comboNewteamTeamName.addItems(team_names)

        # clear the RFID line edit
        self.ui.lineNewteamRfid.clear()

        # fill the game durations combo box
        game_durations_str = self.fd.config.game_durations_str
        self.ui.comboNewteamDuration.clear()
        self.ui.comboNewteamDuration.addItems(game_durations_str)

        # set up the buttons
        self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon())
        self.ui.btnNewteamNewTeam.clicked.connect(self.create_new_team)
        self.ui.btnNewteamRfidClear.clicked.connect(
            lambda: (self.ui.lineNewteamRfid.clear(), self.log.info("RFID cleared")))

        # set up the status label
        self.update_new_team_status_label("", None)


    def update_new_team_status_label(self:'CubeGuiForm', text: str, icon_name: str=None):
        try:
            self.ui.lblNewteamNewTeamStatusText.setText(text)
            if icon_name:
                self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon.fromTheme(icon_name))
            QApplication.processEvents()
        except Exception as e:
            self.log.error(f"Error in update_new_team_status_label: {e}")
            self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon.fromTheme("error"))
            self.ui.lblNewteamNewTeamStatusText.setText("{e}")

    def create_new_team(self: 'CubeGuiForm'):
        team_name = self.ui.comboNewteamTeamName.currentText()
        team_custom_name = self.ui.lineNewteamTeamCustomName.text()
        rfid = self.ui.lineNewteamRfid.text()
        allocated_time = cube_utils.hhmmss_string_to_seconds(self.ui.comboNewteamDuration.currentText())
        if any([not team_name, not rfid, not allocated_time]):
            self.update_new_team_status_label(f"Informations manquantes ou erronées", "error")
            self.log.error("Missing information to create a new team.")
            return
        team = cube_game.CubeTeamStatus(team_name, rfid, allocated_time)
        self.log.info(f"Creating new team: {team.to_string()}")
        self.update_new_team_status_label(f"Création de l'équipe {team_name} en cours...", "hourglass")
        # send the new team creation message to the cubemaster and check that the ack is ok
        report = self.fd.add_new_team(team)
        if report.ok:
            self.update_new_team_status_label(f"Équipe {team_name} créée avec succès.", "ok")
        else:
            self.update_new_team_status_label(f"Échec de la création de l'équipe {team_name} : {report.ack_info}", "error")
