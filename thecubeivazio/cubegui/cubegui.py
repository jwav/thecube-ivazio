import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from cubegui_ui import Ui_Form

class MyForm(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyForm()
    window.show()
    sys.exit(app.exec_())