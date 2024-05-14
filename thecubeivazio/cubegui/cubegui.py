import threading

from PyQt5.QtWidgets import QApplication, QMainWindow
from cubegui_ui import Ui_Form

from thecubeivazio import cubefrontdesk as cfd
from thecubeivazio import cube_logger as cube_logger

import sys
import atexit


class MyForm(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.log = cube_logger.make_logger(name="CubeGui", log_filename=cube_logger.CUBEGUI_LOG_FILENAME)

        try:
            self.setup_ui()
        except Exception as e:
            self.log.error(f"Error in setup_ui: {e}")

        self.fd = cfd.CubeFrontDesk()
        self.fd.run()
        atexit.register(self.fd.stop)

        self._backend_thread = threading.Thread(target=self._backend_loop)
        self._keep_running = True
        self._backend_thread.start()

    def setup_ui(self):
        # read the resource file "team_names.txt" and fill the combo box with its lines
        self.ui.comboCreateTeamName.clear()
        # use pyqt resource system to get the filename
        filename = ":/resources/team_names.txt"
        with open(filename, "r") as f:
            lines = f.readlines()
            for line in lines:
                self.ui.comboCreateTeamName.addItem(line.strip())

        # read the resource file "game_durations.txt" and fill the combo box with its lines
        self.ui.comboCreateDuration.clear()
        # use pyqt resource system to get the filename
        filename = ":/resources/game_durations.txt"
        with open(filename, "r") as f:
            lines = f.readlines()
            for line in lines:
                self.ui.comboCreateDuration.addItem(line.strip())


    def _backend_loop(self):
        """check the FrontDesk events (rfid, messages), and handle them"""
        while self._keep_running:
            if self.fd.rfid.has_new_lines():
                lines = self.fd.rfid.get_completed_lines()
                for line in lines:
                    self.log.info(f"RFID line: {line}")
                    self.ui.lineCreateRfid.setText(f"{line.uid}")
                    self.ui.lineManageRfid.setText(f"{line.uid}")
                    self.fd.rfid.remove_line(line)





if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyForm()
    window.show()
    sys.exit(app.exec_())