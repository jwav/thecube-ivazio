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

        self.log = cube_logger.make_logger(name="CubeGui", log_filename=cube_logger.CUBEGUI_LOG_FILENAME)

        if self.initial_setup():
            self.log.info("Initial setup done.")
        else:
            self.log.error("Initial setup failed.")
            exit(1)

        self.fd = cfd.CubeServerFrontdesk()
        self.fd.run()
        atexit.register(self.fd.stop)
        self.log.info("FrontDesk started.")

        self._backend_thread = threading.Thread(target=self._backend_loop)
        self._keep_running = True
        self._backend_thread.start()

    def initial_setup(self):


        self.setup_create_tab()
        self.setup_manage_tab()
        self.setup_admin_tab()

        return True

    def setup_create_tab(self):
        """Sets up the widgets of the tab 'Créer une nouvelle équipe'"""
        # read the resource file "team_names.txt" and fill the combo box with its lines
        self.ui.comboCreateTeamName.clear()
        # use pyqt resource system to get the filename
        filename = ":team_names.txt"
        file = QFile(filename)

        if not file.open(QFile.ReadOnly | QFile.Text):
            self.log.error(f"Unable to open the file {filename}")
            return False

        text_stream = QTextStream(file)
        while not text_stream.atEnd():
            line = text_stream.readLine()
            self.ui.comboCreateTeamName.addItem(line.strip())
        file.close()

        # fill the duration combo box

        self.ui.comboCreateDuration.clear()
        # use pyqt resource system to get the filename
        filename = ":game_durations.txt"
        file = QFile(filename)

        if not file.open(QFile.ReadOnly | QFile.Text):
            self.log.error(f"Unable to open the file {filename}")
            return False

        text_stream = QTextStream(file)
        while not text_stream.atEnd():
            line = text_stream.readLine()
            self.ui.comboCreateDuration.addItem(line.strip())
        file.close()

        self.ui.btnCreateNewTeam.clicked.connect(self.create_new_team)
        self.ui.btnCreateRfidClear.clicked.connect(lambda: (self.ui.lineCreateRfid.clear(), self.log.info("RFID cleared")))

        self.ui.btnIconCreateNewTeamStatus.setIcon(QtGui.QIcon())
        self.ui.lblCreateNewTeamStatusText.setText("")

    def setup_manage_tab(self):
        pass

    def setup_admin_tab(self):
        pass

    def create_new_team(self):
        team_name = self.ui.comboCreateTeamName.currentText()
        rfid = self.ui.lineCreateRfid.text()
        allocated_time = cube_utils.hhmmmsss_string_to_seconds(self.ui.comboCreateDuration.currentText())
        if any([not team_name, not rfid, not allocated_time]):
            self.ui.lblCreateNewTeamStatusText.setText(f"Informations manquantes ou erronées")
            self.ui.btnIconCreateNewTeamStatus.setIcon(QtGui.QIcon.fromTheme("error"))
            QApplication.processEvents()
            self.log.error("Missing information to create a new team.")
            return
        self.log.info(f"Creating new team: {team_name} with RFID: {rfid} and {allocated_time} seconds.")
        team = cube_game.CubeTeamStatus(team_name, rfid, allocated_time)
        self.ui.lblCreateNewTeamStatusText.setText(f"Création de l'équipe {team_name} en cours...")
        self.ui.btnIconCreateNewTeamStatus.setIcon(QtGui.QIcon.fromTheme("hourglass"))
        QApplication.processEvents()
        if self.fd.add_new_team(team):
            self.ui.lblCreateNewTeamStatusText.setText(f"Équipe {team_name} créée avec succès.")
            self.ui.btnIconCreateNewTeamStatus.setIcon(QtGui.QIcon.fromTheme("ok"))
        else:
            self.ui.lblCreateNewTeamStatusText.setText(f"Échec de la création de l'équipe {team_name}.")
            self.ui.btnIconCreateNewTeamStatus.setIcon(QtGui.QIcon.fromTheme("error"))

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
            #self.log.debug("Backend loop iteration")
            self.handle_rfid()
            time.sleep(1)



    def handle_rfid(self):
        try:
            if self.fd.rfid.is_setup():
                self.ui.btnIconCreateRfidStatus.setIcon(QtGui.QIcon())
                self.ui.btnIconCreateRfidStatus.setToolTip("")
            else:
                icon = QtGui.QIcon.fromTheme("error")
                self.ui.btnIconCreateRfidStatus.setIcon(icon)
                self.ui.btnIconCreateRfidStatus.setToolTip("Le lecteur RFID n'est pas connecté.")
                self.fd.rfid.setup()
            if self.fd.rfid.has_new_lines():
                lines = self.fd.rfid.get_completed_lines()
                for line in lines:
                    self.log.info(f"RFID line: {line}")
                    self.ui.lineCreateRfid.setText(f"{line.uid}")
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