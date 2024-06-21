"""File for the mixin class (partial for CubeGuiForm) for the new team tab."""
import json

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow
from cubegui_ui import Ui_Form

from thecubeivazio import cubeserver_frontdesk as cfd
from thecubeivazio import cube_game, cube_utils, cube_rfid, cube_logger, cube_config
from thecubeivazio.cube_common_defines import *
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QFileDialog, QPushButton, QMainWindow
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices

import sys
import atexit
import traceback as tb

from typing import TYPE_CHECKING

from thecubeivazio.cube_messages import CubeAckInfos

if TYPE_CHECKING:
    from cubegui import CubeGuiForm


class CubeGuiTabConfigMixin:
    self: 'CubeGuiForm'
    ui: Ui_Form
    log: cube_logger.CubeLogger

    def setup_tab_config(self: 'CubeGuiForm'):
        # setup the label
        self.ui.lblConfigInfo.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextBrowserInteraction)
        self.ui.lblConfigInfo.setOpenExternalLinks(True)
        self.ui.lblConfigInfo.setTextFormat(Qt.RichText)  # Ensure the label interprets the HTML
        self.ui.lblConfigInfo.linkActivated.connect(self.open_folder)

        # setup enter triggering the load_config
        self.ui.lineConfigPassword.returnPressed.connect(self.load_config)

        # set up the buttons
        self.ui.btnConfigSave.clicked.connect(self.save_config)
        self.ui.btnConfigCheck.clicked.connect(self.check_config)
        self.ui.btnConfigLoad.clicked.connect(self.load_config)
        self.ui.plainTextConfigContent.clear()
        self.ui.btnConfigSendToServers.clicked.connect(self.send_config_to_servers)

        # set the info text
        self.set_config_info_text(
            "ℹ️ Entrez un mot de passe et cliquez sur 'Charger configuration' "
            "pour éditer la configuration.")

    @cubetry
    def send_config_to_servers(self: 'CubeGuiForm') -> bool:
        try:
            self.log.info("Sending config to servers...")
            self.set_config_info_text("⏳ Envoi de la configuration en cours...")
            self.update_gui()
            if not self.save_config():
                self.log.error("Error saving config")
                return False
            json_str = self.ui.plainTextConfigContent.toPlainText()
            self.fd.config = cube_config.CubeConfig.make_from_json(json_str)
            if not self.fd.config.is_valid():
                self.log.error("Error sending config: invalid config")
                raise Exception("❌ Impossible d'envoyer une configuration invalide.")
            result = self.fd.send_config_message_to_all()
            if result is None:
                self.log.error("Error sending config: sendreport is None")
                raise Exception("❌ Erreur lors de l'envoi de la configuration (None).")
            if not result:
                self.log.error(f"Error sending config: sendreport unsuccesful : {result.ack_info}")
                raise Exception(f"❌ Erreur lors de l'envoi de la configuration : {result.ack_info}")
            self.set_config_info_text("✔️ Configuration envoyée avec succès.")
        except Exception as e:
            self.set_config_info_text(f"{str(e)}")
            self.log.error(f"Error sending config: {e}")
            return False


    @cubetry
    def open_folder(self: 'CubeGuiForm', url: str) -> bool:
        self.log.info(url)
        if not QDesktopServices.openUrl(QUrl(url)):
            self.log.error(f"Could not open folder '{url}'")
        self.log.success(f"Opened folder '{url}'")
        return True

    def set_config_info_text(self, text: str):
        # replace all \n by <br/>
        text = text.replace("\n", "<br/>")
        self.ui.lblConfigInfo.setText(text)

    @cubetry
    def load_config(self: 'CubeGuiForm') -> bool:
        folder_url = QUrl.fromLocalFile(CONFIG_DIR).toString(QUrl.FullyEncoded)
        try:
            if not os.path.exists(CONFIG_FILEPATH):
                raise Exception(f"❌ Fichier de configuration absent : '{CONFIG_FILEPATH}'<br/>")
            # use the password to load the config
            password = self.ui.lineConfigPassword.text()
            if not password:
                self.set_config_info_text("⚠️ Entrez un mot de passe.")
                return False
            config = cube_config.CubeConfig.make_from_encrypted_json_file(password=password)
            if config is None:
                raise Exception("❌ Mot de passe incorrect.")
            config.set_password(password)
            json_str = config.to_json()
            json_dict = json.loads(json_str)
            # format the json
            json_str = json.dumps(json_dict, indent=4, ensure_ascii=False)
            self.ui.plainTextConfigContent.setPlainText(json_str)
            self.set_config_info_text("✔️ Configuration chargée avec succès.")

        except Exception as e:
            self.set_config_info_text(str(e))
            self.log.error(f"Error loading config: {e}")

    @cubetry
    def check_config(self: 'CubeGuiForm') -> bool:
        if not self.ui.plainTextConfigContent.toPlainText():
            self.set_config_info_text("⚠️ Configuration non chargée.")
            return False
        try:
            json_str = self.ui.plainTextConfigContent.toPlainText()
            result, error = cube_utils.validate_json(json_str)
            if not result:
                raise Exception(f"{error}")
            config = cube_config.CubeConfig.make_from_json(json_str)
            if config.is_valid():
                self.set_config_info_text("✔️ Configuration valide.")
                return True
            else:
                raise Exception("❌ Configuration invalide.")
        except Exception as e:
            self.set_config_info_text(f"❌ Configuration invalide : {str(e)}")
            self.log.error(f"Error checking config: {e}")
            return False

    @cubetry
    def save_config(self: 'CubeGuiForm') -> bool:
        try:
            json_str = self.ui.plainTextConfigContent.toPlainText()
            config = cube_config.CubeConfig.make_from_json(json_str)
            if not self.check_config():
                raise Exception("❌ Impossible de sauvegarder une configuration invalide.")
            if not config.save_to_encrypted_json_file():
                raise Exception("❌ Erreur lors de la sauvegarde de la configuration.")
            self.fd.config = cube_config.CubeConfig.make_from_json(json_str)
            self.set_config_info_text("✔️ Configuration sauvegardée avec succès.")
            return True
        except Exception as e:
            self.set_config_info_text(f"❌ {str(e)}")
            self.log.error(f"Error saving config: {e}")
            return False


if __name__ == "__main__":
    from cubegui import CubeGuiForm
    import atexit

    app = QApplication(sys.argv)
    window = CubeGuiForm()
    atexit.register(window.close)
    window.show()

    window.ui.tabWidget.setCurrentIndex(3)
    window.ui.lineConfigPassword.setText("pwd")
    window.load_config()
    window.send_config_to_servers()

    sys.exit(app.exec_())
