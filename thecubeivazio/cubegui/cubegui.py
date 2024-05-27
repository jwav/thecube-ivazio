# icon names : https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html

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


class CubeGuiForm(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.log = cube_logger.CubeLogger(name="CubeGui", log_filename=cube_logger.CUBEGUI_LOG_FILENAME)

        self.fd = cfd.CubeServerFrontdesk()
        self.fd.run()
        atexit.register(self.fd.stop)
        self.log.info("FrontDesk Server started.")

        if self.initial_setup():
            self.log.info("Initial setup done.")
        else:
            self.log.error("Initial setup failed.")
            exit(1)

        self._backend_thread = threading.Thread(target=self._backend_loop)
        self._keep_running = True
        self._backend_thread.start()

    def initial_setup(self):

        self.setup_team_creation_tab()
        self.setup_team_management_tab()
        self.setup_admin_tab()

        return True

    def setup_team_creation_tab(self):
        """Sets up the widgets of the tab 'Créer une nouvelle équipe'"""

        # fill the team names combo box
        team_names = self.fd.config.team_names
        self.ui.comboNewteamTeamName.clear()
        self.ui.comboNewteamTeamName.addItems(team_names)

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


    def update_new_team_status_label(self, text: str, icon_name: str=None):
        try:
            self.ui.lblNewteamNewTeamStatusText.setText(text)
            if icon_name:
                self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon.fromTheme(icon_name))
            QApplication.processEvents()
        except Exception as e:
            self.log.error(f"Error in update_new_team_status_label: {e}")
            self.ui.btnIconNewteamNewTeamStatus.setIcon(QtGui.QIcon.fromTheme("error"))
            self.ui.lblNewteamNewTeamStatusText.setText("{e}")

    def update_team_creation_tab(self):
        raise NotImplementedError

    def setup_team_management_tab(self):
        pass

    def setup_admin_tab(self):
        pass

    def create_new_team(self):
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

    def closeEvent(self, event):
        self.log.info("Closing CubeGui...")
        self._keep_running = False
        event.accept()
        self._backend_thread.join(timeout=0.1)
        self.fd.stop()
        self.log.info("CubeGui closed")

    def _backend_loop(self):
        """check the FrontDesk events (rfid, messages), and handle them"""
        while self._keep_running:
            # self.log.debug("Backend loop iteration")
            self.handle_rfid()
            time.sleep(1)

    def handle_rfid(self):
        try:
            if self.fd.rfid.is_setup():
                self.ui.btnIconNewteamRfidStatus.setIcon(QtGui.QIcon())
                self.ui.btnIconNewteamRfidStatus.setToolTip("")
            else:
                icon = QtGui.QIcon.fromTheme("error")
                self.ui.btnIconNewteamRfidStatus.setIcon(icon)
                self.ui.btnIconNewteamRfidStatus.setToolTip("Le lecteur RFID n'est pas connecté.")
                self.fd.rfid.setup()
            if self.fd.rfid.has_new_lines():
                lines = self.fd.rfid.get_completed_lines()
                for line in lines:
                    self.log.info(f"RFID line: {line}")
                    self.ui.lineNewteamRfid.setText(f"{line.uid}")
                    self.ui.lineManageRfid.setText(f"{line.uid}")
                    self.fd.rfid.remove_line(line)
        except Exception as e:
            self.log.error(f"Error in handle_rfid: {e}")
            print(tb.format_exc())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CubeGuiForm()
    window.show()
    sys.exit(app.exec_())
