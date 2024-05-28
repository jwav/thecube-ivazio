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
from thecubeivazio.cube_logger import CubeLogger, CUBEGUI_LOG_FILENAME
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cubegui.cubegui_tab_newteam import CubeGuiTabNewTeamMixin
from thecubeivazio.cubegui.cubegui_tab_teams import CubeGuiTabTeamsMixin
from thecubeivazio.cubegui.cubegui_tab_admin import CubeGuiTabAdminMixin
from thecubeivazio import cube_identification as ci

import sys
import atexit
import traceback as tb


class ServersInfoHasher:
    def __init__(self, fd: cfd.CubeServerFrontdesk):
        self.teams_hash = fd.teams.hash
        self.cubeboxes_hash = fd.cubeboxes.hash
        self.nodes_list = fd.net.nodes_list.hash

    @property
    def hash(self) -> Hash:
        try:
            import hashlib
            return hashlib.sha256(
                f"{self.teams_hash}{self.cubeboxes_hash}{self.nodes_list}".encode()
            ).hexdigest()
        except Exception as e:
            CubeLogger.static_error(f"Error in ServersInfoHash.hash: {e}")
            CubeLogger.static_error(tb.format_exc())
            return ""

    def __repr__(self):
        return self.hash

    def __str__(self):
        return self.hash

    @classmethod
    def get_current_servers_info_hash(cls, fd: cfd.CubeServerFrontdesk) -> Hash:
        return ServersInfoHasher(fd).hash



class CubeGuiForm(QMainWindow, CubeGuiTabNewTeamMixin, CubeGuiTabTeamsMixin, CubeGuiTabAdminMixin):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.log = CubeLogger(name="CubeGui", log_filename=CUBEGUI_LOG_FILENAME)

        self.fd = cfd.CubeServerFrontdesk()
        self.fd.run()
        atexit.register(self.fd.stop)
        self.log.info("FrontDesk Server started.")

        self._last_displayed_servers_info_hash = None

        if self.initial_setup():
            self.log.info("Initial setup done.")
        else:
            self.log.error("Initial setup failed.")
            exit(1)

        self._rfid_timer = QTimer()
        self._rfid_timer.timeout.connect(self.check_rfid)
        self._rfid_timer.start(100)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.update_all_tabs)
        self._update_timer.start(1000)

    def update_all_tabs(self):
        # print(f"{self._last_displayed_servers_info_hash.hash}, {ServersInfoHash.get_current_servers_info(self.fd).hash}")
        # print(f"{self.fd.teams.hash}, {self.fd.cubeboxes.hash}, {self.fd.net.nodes_list.hash}\n")
        current_servers_info_hash = ServersInfoHasher.get_current_servers_info_hash(self.fd)

        # print(f"{self.fd.net.nodes_list}\n---({self.fd.net.nodes_list.hash})---\n")
        if self._last_displayed_servers_info_hash != current_servers_info_hash:
            self.set_servers_info_status_label(True, "Mise à jour partielle effectuée.")
            self.update_tab_admin()
            self._last_displayed_servers_info_hash = current_servers_info_hash

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
        self._update_timer.stop()
        self._rfid_timer.stop()
        self.log.info("CubeGui closed")

    def check_rfid(self):
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
            self.log.error(tb.format_exc())


if __name__ == "__main__":
    import atexit

    app = QApplication(sys.argv)
    window = CubeGuiForm()
    atexit.register(window.close)
    window.show()
    sys.exit(app.exec_())
