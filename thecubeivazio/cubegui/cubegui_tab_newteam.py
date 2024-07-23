"""File for the mixin class (partial for CubeGuiForm) for the new team tab."""

import sys
import time
from typing import TYPE_CHECKING

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

from thecubeivazio import cube_game, cube_utils, cube_rfid
from thecubeivazio.cube_common_defines import cubetry

if TYPE_CHECKING:
    from cubegui import CubeGuiForm




class CubeGuiTabNewTeamMixin:
    def setup_tab_newteam(self: 'CubeGuiForm'):
        """Sets up the widgets of the tab 'Créer une nouvelle équipe'"""

        # fill the team names combo box
        team_names = self.fd.config.defined_team_names
        self.ui.comboNewteamTeamName.clear()
        self.ui.comboNewteamTeamName.addItems(team_names)

        self.ui.lineTeamsCustomName.setMaxLength(cube_game.CubeTeamStatus.CUSTOM_NAME_MAX_LENGTH)

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

    @cubetry
    def update_tab_newteam(self: 'CubeGuiForm'):
        """# in new teams tab, remove the team names (cities) that are already in use """
        occupied_names = [team.name for team in self.fd.teams]
        valid_team_names = [name for name in self.fd.config.defined_team_names if name not in occupied_names]
        # if the combobox is different from the valid names (not factoring in order), update it
        combobox_team_names = [self.ui.comboNewteamTeamName.itemText(i) for i in range(self.ui.comboNewteamTeamName.count())]

        if set(combobox_team_names) != set(valid_team_names):
            self.ui.comboNewteamTeamName.clear()
            self.ui.comboNewteamTeamName.addItems(valid_team_names)

    def update_new_team_status_label(self: 'CubeGuiForm', text: str, icon_name: str = None):
        try:
            self.ui.lblNewteamNewTeamStatusText.setText(text)
            if icon_name:
                self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon.fromTheme(icon_name))
        except Exception as e:
            self.log.error(f"Error in update_new_team_status_label: {e}")
            self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon.fromTheme("error"))
            self.ui.lblNewteamNewTeamStatusText.setText("{e}")
        finally:
            self.update_gui()


    @cubetry
    def update_new_team_rfid_status_label(self: 'CubeGuiForm', text: str, icon_name: str = None):
        try:
            self.ui.lblNewteamRfidStatusText.setText(text)
            if icon_name:
                self.ui.btnIconNewteamRfidStatus.setIcon(QtGui.QIcon.fromTheme(icon_name))
        except Exception as e:
            self.log.error(f"Error in update_new_team_rfid_status_label: {e}")
            self.ui.btnIconNewteamRfidStatus.setIcon(QtGui.QIcon.fromTheme("error"))
            self.ui.lblNewteamRfidStatusText.setText("{e}")
        finally:
            self.update_gui()


    @cubetry
    def create_new_team(self: 'CubeGuiForm') -> bool:
        team_name = self.ui.comboNewteamTeamName.currentText()
        custom_name = self.ui.lineNewteamTeamCustomName.text()
        rfid_uid = self.ui.lineNewteamRfid.text()
        max_time_sec = cube_utils.hhmmss_string_to_seconds(self.ui.comboNewteamDuration.currentText())
        creation_timestamp = time.time()
        use_alarm = self.ui.checkNewteamUseAlarm.isChecked()

        if cube_rfid.CubeRfidLine.is_uid_in_resetter_list(rfid_uid):
            self.update_new_team_status_label("Ce RFID est un resetter, il ne peut pas servir à une équipe", "error")
            self.log.info(f"RFID is in resetter list: {rfid_uid}")
            return False
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
            return False

        #ok we got a valid team. Let's send it to the cubemaster
        self.log.info(f"Creating new team: {team.to_string()}")
        self.update_new_team_status_label(f"Création de l'équipe {team_name} en cours...", "hourglass")
        # send the new team creation message to the cubemaster and check that the ack is ok
        report = self.fd.add_new_team(team)

        if not report.sent_ok:
            self.update_new_team_status_label(
                f"Échec de la création de l'équipe {team_name} : pas réussi à envoyer le message!",
                "error")
            return False
        elif not report.ack_info:
            self.update_new_team_status_label(
                f"Échec de la création de l'équipe {team_name} : pas de réponse du CubeMaster!",
                "error")
            return False
        elif not report.ack_ok:
            self.update_new_team_status_label(
                f"Échec de la création de l'équipe {team_name} : {report.ack_info}",
                "error")
            return False
        self.update_new_team_status_label(f"Équipe {team_name} créée avec succès.", "ok")
        self.ui.lineNewteamRfid.clear()
        self.ui.lineNewteamTeamCustomName.clear()
        self.update_tab_newteam()
        return True


if __name__ == "__main__":
    from cubegui import CubeGuiForm
    import atexit
    app = QApplication(sys.argv)
    window = CubeGuiForm()
    atexit.register(window.close)
    window.show()

    window.ui.tabWidget.setCurrentIndex(0)
    window.ui.lineNewteamTeamCustomName.setText("Custom Name")
    rfid_uid = cube_rfid.CubeRfidLine.generate_random_rfid_line().uid
    window.ui.lineNewteamRfid.setText(rfid_uid)

    sys.exit(app.exec_())