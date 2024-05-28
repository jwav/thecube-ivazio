# icon names : https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html

import threading
import time
from functools import partial
from typing import Optional

from PyQt5 import QtGui
from PyQt5.QtCore import QFile, QTextStream, QThread, QMetaObject, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
from cubegui_ui import Ui_Form

from thecubeivazio import cubeserver_frontdesk as cfd, cube_game, cube_utils
from thecubeivazio import cube_logger as cube_logger
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cubegui.cubegui_tab_newteam import CubeGuiTabNewTeamMixin
from thecubeivazio.cubegui.cubegui_tab_teams import CubeGuiTabTeamsMixin
from thecubeivazio.cubegui.cubegui_tab_admin import CubeGuiTabAdminMixin

import sys
import atexit
import traceback as tb


class CubeGuiForm(QMainWindow, CubeGuiTabNewTeamMixin, CubeGuiTabTeamsMixin, CubeGuiTabAdminMixin):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.log = cube_logger.CubeLogger(name="CubeGui", log_filename=cube_logger.CUBEGUI_LOG_FILENAME)

        self.fd = cfd.CubeServerFrontdesk()
        self.fd.run()
        atexit.register(self.fd.stop)
        self.log.info("FrontDesk Server started.")

        self._last_displayed_game_status_hash:Optional[Hash] = None

        if self.initial_setup():
            self.log.info("Initial setup done.")
        else:
            self.log.error("Initial setup failed.")
            exit(1)

        self._rfid_timer = QTimer()
        self._rfid_timer.timeout.connect(self.handle_rfid)
        self._rfid_timer.start(100)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.update_all_tabs)
        self._update_timer.start(1000)

    def update_all_tabs(self):
        self.update_tab_admin()

    def initial_setup(self):
        self.setup_tab_newteam()
        self.setup_tab_teams()
        self.setup_tab_admin()
        self.setup_debug()
        return True

    def setup_debug(self):
        """Initial setup for when we're debugging"""
        self.ui.tabWidget.setCurrentIndex(2)
        self.search_teams()

    def closeEvent(self, event):
        event.accept()
        self.log.info("Closing CubeGui...")
        self.fd.stop()
        self._gui_thread.quit()
        if not self._gui_thread.wait(100):
            self.log.error("CubeGui thread did not stop in time.")
            self._gui_thread.terminate()
            self._gui_thread.wait()
        self.log.info("CubeGui closed")

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
                    self.ui.lineTeamsRfid.setText(f"{line.uid}")
                    self.fd.rfid.remove_line(line)
        except Exception as e:
            self.log.error(f"Error in handle_rfid: {e}")
            print(tb.format_exc())




if __name__ == "__main__":
    import atexit
    app = QApplication(sys.argv)
    window = CubeGuiForm()
    atexit.register(window.close)
    window.show()
    sys.exit(app.exec_())
