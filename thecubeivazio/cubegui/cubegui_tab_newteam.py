"""File for the mixin class (partial for CubeGuiForm) for the new team tab."""

import time

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow
from cubegui_ui import Ui_Form

from thecubeivazio import cubeserver_frontdesk as cfd, cube_game, cube_utils, cube_rfid

import sys
import atexit
import traceback as tb

from typing import TYPE_CHECKING

from thecubeivazio.cube_messages import CubeAckInfos

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
        # set the RFID status to empty
        self.update_new_team_rfid_status_label("", None)

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

    def update_new_team_status_label(self: 'CubeGuiForm', text: str, icon_name: str = None):
        try:
            self.ui.lblNewteamNewTeamStatusText.setText(text)
            if icon_name:
                self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon.fromTheme(icon_name))
            QApplication.processEvents()
        except Exception as e:
            self.log.error(f"Error in update_new_team_status_label: {e}")
            self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon.fromTheme("error"))
            self.ui.lblNewteamNewTeamStatusText.setText("{e}")

    def update_new_team_rfid_status_label(self: 'CubeGuiForm', text: str, icon_name: str = None):
        try:
            self.ui.lblNewteamRfidStatusText.setText(text)
            if icon_name:
                self.ui.btnIconNewteamRfidStatus.setIcon(QtGui.QIcon.fromTheme(icon_name))
            QApplication.processEvents()
        except Exception as e:
            self.log.error(f"Error in update_new_team_rfid_status_label: {e}")
            self.ui.btnIconNewteamRfidStatus.setIcon(QtGui.QIcon.fromTheme("error"))
            self.ui.lblNewteamRfidStatusText.setText("{e}")

    def create_new_team(self: 'CubeGuiForm'):
        team_name = self.ui.comboNewteamTeamName.currentText()
        custom_name = self.ui.lineNewteamTeamCustomName.text()
        rfid_uid = self.ui.lineNewteamRfid.text()
        max_time_sec = cube_utils.hhmmss_string_to_seconds(self.ui.comboNewteamDuration.currentText())
        creation_timestamp = time.time()
        use_alarm = self.ui.checkNewteamUseAlarm.isChecked()

        if cube_rfid.CubeRfidLine.is_uid_in_resetter_list(rfid_uid):
            self.update_new_team_status_label("Ce RFID est un resetter, il ne peut pas servir à une équipe", "error")
            self.log.info(f"RFID is in resetter list: {rfid_uid}")
            return
        try:
            team = cube_game.CubeTeamStatus(
                name=team_name, custom_name=custom_name, rfid_uid=rfid_uid,
                max_time_sec=max_time_sec, creation_timestamp=creation_timestamp,
                use_alarm=use_alarm)
            assert team.is_valid()
        except Exception as e:
            self.update_new_team_status_label(f"Informations manquantes ou erronées", "error")
            self.log.error(f"Missing or erroneous information to create a new team: {e}"
                           f" name={team_name}, custom_name={custom_name}, rfid_uid={rfid_uid}, max_time={max_time_sec}")
            return

        self.log.info(f"Creating new team: {team.to_string()}")
        self.update_new_team_status_label(f"Création de l'équipe {team_name} en cours...", "hourglass")
        # send the new team creation message to the cubemaster and check that the ack is ok
        report = self.fd.add_new_team(team)

        if not report.success:
            self.update_new_team_status_label(
                f"Échec de la création de l'équipe {team_name} : pas réussi à envoyer le message!",
                "error")
            return
        elif not report.ack_info:
            self.update_new_team_status_label(
                f"Échec de la création de l'équipe {team_name} : pas de réponse du CubeMaster!",
                "error")
            return
        elif not report.ok:
            self.update_new_team_status_label(
                f"Échec de la création de l'équipe {team_name} : {report.ack_info}",
                "error")
            return
        self.update_new_team_status_label(f"Équipe {team_name} créée avec succès.", "ok")


if __name__ == "__main__":
    from cubegui import CubeGuiForm
    CubeGuiForm.main()