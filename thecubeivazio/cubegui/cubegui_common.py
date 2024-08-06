import traceback as tb

from PyQt5.QtCore import QThread, QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow

from thecubeivazio import cubeserver_frontdesk as cfd, cube_rfid
from thecubeivazio.cube_common_defines import *


from typing import NamedTuple

class CubeGuiTaskResult(NamedTuple):
    success: bool
    info: str

class CubeGuiThreadWorker(QObject):
    finished = pyqtSignal(object)
    progress = pyqtSignal(object)

    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self):
        result = None
        try:
            result = self.function(*self.args, **self.kwargs)
        except Exception as e:
            result = e
        finally:
            self.finished.emit(result)



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