"""File for the mixin class (partial for CubeGuiForm) for the admin tab."""


from PyQt5 import QtGui
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from cubegui_ui import Ui_Form

from thecubeivazio import cubeserver_frontdesk as cfd, cube_game, cube_utils
from thecubeivazio import cube_logger as cube_logger
from thecubeivazio.cube_common_defines import *
from thecubeivazio import cube_identification as ci
import sys
import atexit
import traceback as tb

from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from cubegui import CubeGuiForm


class CubeGuiTabAdminMixin:

    def setup_tab_admin(self: 'CubeGuiForm'):
        self.ui: Ui_Form
        self.ui.btnAdminUpdateServersInfo.clicked.connect(self.request_servers_infos)
        self.ui.btnAdminOrderCubeboxReset.clicked.connect(self.order_cubebox_reset)
        self.ui.comboAdminCubeboxToOrder.addItems(ci.CUBEBOX_NODENAMES)

        self.ui.btnAdminSendCommand.clicked.connect(self.send_command_clicked)
        self.ui.lblAdminCommandStatusText.setText("")
        self.ui.lblAdminServersInfoStatusText.setText("")
        self.ui.btnIconAdminStatus.setIcon(QtGui.QIcon())
        # set up the command line so that enter key triggers the send command button
        self.ui.lineAdminCommand.returnPressed.connect(self.ui.btnAdminSendCommand.click)


    def order_cubebox_reset(self: 'CubeGuiForm'):
        self.ui: Ui_Form
        cubebox_nodename = self.ui.comboAdminCubeboxToOrder.currentText()
        cubebox_id = ci.node_name_to_cubebox_index(cubebox_nodename)
        self.fd.order_cubebox_to_reset(cubebox_id=cubebox_id)

    def request_servers_infos(self: 'CubeGuiForm'):
        self.ui: Ui_Form
        self.set_servers_info_status_label("hourglass", "En attente de réponse des Cubeboxes...")
        self.fd.request_all_cubeboxes_statuses_one_by_one(reply_timeout=STATUS_REPLY_TIMEOUT)
        self.set_servers_info_status_label("hourglass", "En attente de réponse du CubeMaster...")
        if self.fd.request_cubemaster_status(reply_timeout=STATUS_REPLY_TIMEOUT*4):
            self.set_servers_info_status_label("ok", "Mise à jour totale effectuée.")
        else:
            self.set_servers_info_status_label("error", "Erreur lors de la mise à jour totale.")

    @cubetry
    def set_servers_info_status_label(self: 'CubeGuiForm', icon:str, info:str):
        self.ui: Ui_Form
        self.ui.lblAdminServersInfoStatusText.setText(info)
        self.ui.btnIconAdminStatus.setIcon(QtGui.QIcon.fromTheme(icon))
        QApplication.processEvents()

    def update_tab_admin(self: 'CubeGuiForm'):
        self.ui: Ui_Form
        # print("update_tab_admin")
        try:
        # if True:
            print("update_tab_admin")
            table = self.ui.tableAdminServersInfo
            table.clearContents()
            node_names = [ci.CUBEFRONTDESK_NODENAME, ci.CUBEMASTER_NODENAME] + list(ci.CUBEBOX_NODENAMES)
            # rows: FrontDesk, CubeMaster, CubeBoxes 1 to NB_CUBEBOXES
            # vertical headers: Node name
            # columns: last message time (hh:mm:ss) IP address, Status
            table.setRowCount(ci.NB_CUBEBOXES+2)
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(
                ["Heure dernier msg", "IP", "Statut"])
            table.setVerticalHeaderLabels(node_names)
            for i, node_name in enumerate(node_names):
                last_msg_timestamp = self.fd.net.nodes_list.get_last_msg_timestamp_from_node_name(node_name)
                last_msg_hhmmss = cube_utils.timestamp_to_hhmmss_time_of_day_string(last_msg_timestamp, separators="::")
                ip = self.fd.net.nodes_list.get_node_ip_from_node_name(node_name)
                # self.log.debug(f"node_name: {node_name}, ip: {ip}, last_msg_hhmmss: {last_msg_hhmmss}")
                # print(f"nodes_list: {self.fd.net.nodes_list.to_string()}")
                if node_name == ci.CUBEFRONTDESK_NODENAME or node_name == ci.CUBEMASTER_NODENAME:
                    status_str = ""
                else:
                    status_str = self.fd.cubeboxes.get_cubebox_by_node_name(node_name).get_state().to_french()
                table.setItem(i, 0, QTableWidgetItem(last_msg_hhmmss))
                table.setItem(i, 1, QTableWidgetItem(ip))
                table.setItem(i, 2, QTableWidgetItem(status_str))
                # table.resizeColumnsToContents()
                # table.resizeRowsToContents()
                total_row_height = sum([table.rowHeight(row) for row in range(table.rowCount())])
                total_height = total_row_height + table.horizontalHeader().height() + 2 * table.frameWidth()
                table.setFixedHeight(total_height)
        except Exception as e:
            traceback = tb.format_exc()
            self.log.error(f"Error in update_tab_admin: {e.with_traceback(e.__traceback__)}")
            self.ui.lblAdminServersInfoStatusText.setText("{e}")
            self.ui.btnIconAdminStatus.setIcon(QtGui.QIcon.fromTheme("error"))

    @cubetry
    def send_command_clicked(self: 'CubeGuiForm'):
        self.ui: Ui_Form
        command = self.ui.lineAdminCommand.text()
        result = self.fd.send_full_command(command)
        if not result:
            self.ui.lblAdminCommandStatusText.setText("❌ Erreur lors de l'envoi de la commande.")
            return False
        self.ui.lblAdminCommandStatusText.setText("✔️ Commande envoyée et exécutée avec succès.")
        return True


if __name__ == "__main__":
    from cubegui import CubeGuiForm
    app = QApplication(sys.argv)
    window = CubeGuiForm()
    window.show()
    window.ui.lineAdminCommand.setText("CubeMaster update_rgb")
    window.send_command_clicked()
    sys.exit(app.exec_())