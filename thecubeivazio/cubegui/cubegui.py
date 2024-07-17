# icon names : https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
import os
import sys
import threading
import time
import atexit
import traceback as tb
from functools import partial
from typing import Optional
from PyQt5 import QtGui
from PyQt5.QtCore import QFile, QTextStream, QThread, QMetaObject, Qt, QTimer, QObject
from PyQt5.QtWidgets import QApplication, QMainWindow


sys.path.append(os.path.abspath('..'))




def update_py_from_ui_and_qrc():
    """Utility function to update the python files from the ui and qrc files:
    pyuic5 cubegui.ui -o cubegui_ui.py
    pyrcc5 -o resources_rc.py resources.qrc
    """
    import os
    print("Updating py files from ui and qrc files...")
    os.system("pyuic5 cubegui.ui -o cubegui_ui.py")
    os.system("pyrcc5 -o resources_rc.py resources.qrc")
    print("Done updating py files from ui and qrc files.")

# TODO: set this to False before deploying
AUTO_UPDATE_PY_FROM_UI_AND_QRC = True

if AUTO_UPDATE_PY_FROM_UI_AND_QRC:
    update_py_from_ui_and_qrc()

from cubegui_ui import Ui_Form
from thecubeivazio import cubeserver_frontdesk as cfd, cube_rfid
from thecubeivazio.cube_logger import CubeLogger, CUBEGUI_LOG_FILENAME
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cubegui.cubegui_tab_newteam import CubeGuiTabNewTeamMixin
from thecubeivazio.cubegui.cubegui_tab_teams import CubeGuiTabTeamsMixin
from thecubeivazio.cubegui.cubegui_tab_admin import CubeGuiTabAdminMixin
from thecubeivazio.cubegui.cubegui_tab_config import CubeGuiTabConfigMixin





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


class CubeGuiForm(QMainWindow,
                  CubeGuiTabNewTeamMixin,
                  CubeGuiTabTeamsMixin,
                  CubeGuiTabAdminMixin,
                  CubeGuiTabConfigMixin
                  ):
    TABINDEX_NEWTEAM = 0
    TABINDEX_TEAMS = 1
    TABINDEX_ADMIN = 2
    TABINDEX_CONFIG = 3

    _threads = []

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
        self._tabs_update_timer = QTimer()
        self._tabs_update_timer.timeout.connect(self.update_all_tabs)
        self._tabs_update_timer.start(1000)

    @classmethod
    def start_in_thread(cls, function, *args, **kwargs):
        print(f"Starting {function.__name__} in a thread.")
        thread = QThread()
        thread.run = lambda: function(*args, **kwargs)
        thread.finished.connect(lambda: cls.cleanup_threads())
        cls._threads.append(thread)
        thread.start()
        return thread

    @classmethod
    @cubetry
    def cleanup_threads(cls):
        # print(f"Cleaning up threads...")
        # for thread in cls._threads:
        #     if not thread.isRunning():
        #         # print(f"Removing thread {thread}")
        #         cls.threads.remove(thread)
        cls._threads = [thread for thread in cls._threads if thread.isRunning()]
        # print(f"Done cleaning up threads.")


    # @classmethod
    # def update_whole_gui(cls):
    #     """just a handier alias for `QApplication.processEvents()`"""
    #     verbose = False
    #     try:
    #         if verbose:
    #             print(f"Calling update_whole_gui from {tb.extract_stack()[-2].name}...  ")
    #         QApplication.processEvents()
    #         if verbose:
    #             print("Done calling update_whole_gui.")
    #     except Exception as e:
    #         print(f"Error in update_whole_gui: {e}")
    #         print(tb.format_exc())
    @cubetry
    def update_gui(self):
        QApplication.processEvents()


    @cubetry
    def update_all_tabs(self):
        # print(f"{self._last_displayed_servers_info_hash.hash}, {ServersInfoHash.get_current_servers_info(self.fd).hash}")
        # print(f"{self.fd.teams.hash}, {self.fd.cubeboxes.hash}, {self.fd.net.nodes_list.hash}\n")
        current_servers_info_hash = ServersInfoHasher.get_current_servers_info_hash(self.fd)

        # print(f"{self.fd.net.nodes_list}\n---({self.fd.net.nodes_list.hash})---\n")
        # if received a new servers info hash, update the tab admin
        if self._last_displayed_servers_info_hash != current_servers_info_hash:
            self.set_servers_info_status_label("ok", "Mise à jour partielle effectuée.")
            self.update_tab_admin()
            self._last_displayed_servers_info_hash = current_servers_info_hash

        # in new teams tab, remove the team names (cities) that are already in use
        self.update_tab_newteam()

        self.update_tab_teams()

        self.update_tab_config()

        self.update_gui()



    def initial_setup(self):
        self.setup_tab_newteam()
        self.setup_tab_teams()
        self.setup_tab_admin()
        self.setup_tab_config()
        self.setup_debug()
        # self.request_servers_infos()
        return True

    def setup_debug(self):
        """Initial setup for when we're debugging"""
        self.ui.tabWidget.setCurrentIndex(2)
        self.click_search_teams()

    def closeEvent(self, event):
        event.accept()
        self.log.info("Closing CubeGui...")
        self.fd.stop()
        self._tabs_update_timer.stop()
        self._rfid_timer.stop()
        self.log.info("CubeGui closed")

    def check_rfid(self):
        try:
            if not self.fd.rfid.is_setup():
                self.update_new_team_rfid_status_label("Lecteur RFID non connecté", "error")
                self.fd.rfid.setup()
                return
            if self.fd.rfid.has_new_lines():
                lines = self.fd.rfid.get_completed_lines()
                for line in lines:
                    self.fd.rfid.remove_line(line)
                    if not line.is_valid():
                        self.update_new_team_rfid_status_label("RFID non valide", "error")
                        break
                    self.log.info(f"RFID line: {line}")
                    # update the rfid display according to the current tab
                    if self.ui.tabWidget.currentIndex() == self.TABINDEX_NEWTEAM:
                        self.ui.lineNewteamRfid.setText(f"{line.uid}")
                        if cube_rfid.CubeRfidLine.is_uid_in_resetter_list(line.uid):
                            self.log.info(f"RFID is in resetter list: {line.uid}")
                            self.update_new_team_rfid_status_label("Ce RFID est un resetter", "attention")
                            break
                        else:
                            self.update_new_team_rfid_status_label("RFID valide", "ok")
                            break
                    elif self.ui.tabWidget.currentIndex() == self.TABINDEX_TEAMS:
                        self.ui.lineTeamsRfid.setText(f"{line.uid}")


        except Exception as e:
            self.log.error(f"Error in handle_rfid: {e}")
            self.log.error(tb.format_exc())

    @staticmethod
    def main():
        import atexit
        app = QApplication(sys.argv)
        window = CubeGuiForm()
        atexit.register(window.close)
        window.show()
        sys.exit(app.exec_())


if __name__ == "__main__":
    CubeGuiForm.main()
