# icon names : https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html

import threading
import time

from PyQt5 import QtGui
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication, QMainWindow
from cubegui_ui import Ui_Form

from thecubeivazio import cubeserver_frontdesk as cfd, cube_game, cube_utils
from thecubeivazio import cube_logger as cube_logger
from thecubeivazio.cubegui.cubegui_tab_newteam import CubeGuiTabNewTeamMixin

import sys
import atexit
import traceback as tb


class CubeGuiForm(QMainWindow, CubeGuiTabNewTeamMixin):
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

        self.setup_newteam_tab()
        self.setup_team_management_tab()
        self.setup_admin_tab()

        return True





    def update_team_creation_tab(self):
        raise NotImplementedError

    def setup_team_management_tab(self):
        pass

    def setup_admin_tab(self):
        pass


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
