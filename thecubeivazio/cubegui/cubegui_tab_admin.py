"""File for the mixin class (partial for CubeGuiForm) for the admin tab."""
import sys
import time
import traceback as tb
from typing import TYPE_CHECKING

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QTableWidgetItem

from cubegui_ui import Ui_Form
from thecubeivazio import cube_identification as ci, cube_networking
from thecubeivazio import cube_utils
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_rfid import CubeRfidLine

from thecubeivazio.cubegui.cubegui_common import CubeGuiTaskResult

if TYPE_CHECKING:
    from thecubeivazio.cubegui.cubegui import CubeGuiForm


class CubeGuiTabAdminMixin:
    ui: Ui_Form

    def setup_tab_admin(self: 'CubeGuiForm'):
        # server info region
        self.ui.lblAdminCommandStatusText.setText("")
        self.ui.lblAdminServersInfoStatusText.setText("")
        self.ui.btnAdminUpdateServersInfo.clicked.connect(self.request_servers_infos)

        # resetter rfid region
        self.ui.lineAdminRfidResetter.setText("")
        self.ui.btnAdminAddRfidResetter.clicked.connect(self.add_rfid_resetter)
        self.ui.btnAdminRemoveRfidResetter.clicked.connect(self.remove_rfid_resetter)

        # server orders region
        self.ui.comboAdminServerToOrder.clear()
        self.ui.comboAdminServerToOrder.addItems(ci.CUBEBOXES_NODENAMES)
        self.ui.comboAdminServerToOrder.addItems([ci.CUBEMASTER_NODENAME])
        self.ui.btnAdminOrderServerReset.clicked.connect(self.order_server_reset)
        self.ui.btnAdminOrderServerReboot.clicked.connect(self.order_server_reboot)

        # commands region
        self.ui.btnAdminSendCommand.clicked.connect(self.send_command_clicked)
        # set up the command line so that enter key triggers the send command button
        self.ui.lineAdminCommand.returnPressed.connect(self.ui.btnAdminSendCommand.click)

        # on startup, request the servers infos
        self.request_servers_infos(background_task=True)
        self.log.success("setup_tab_admin done")

    @cubetry
    def order_server_reset(self: 'CubeGuiForm'):
        def task():
            nodename = self.ui.comboAdminServerToOrder.currentText()
            full_command = f"{nodename} reset"
            self.ui.lineAdminCommand.setText(full_command)
            self.send_command_clicked()
        # self.start_in_thread(task)
        task()

    @cubetry
    def order_server_reboot(self: 'CubeGuiForm'):
        nodename = self.ui.comboAdminServerToOrder.currentText()
        full_command = f"{nodename} reboot"
        self.ui.lineAdminCommand.setText(full_command)
        self.send_command_clicked()

    @cubetry
    def set_admin_command_status_text(self: 'CubeGuiForm', text: str):
        self.ui.lblAdminCommandStatusText.setText(text)
        self.update_gui()

    @cubetry
    def add_rfid_resetter(self: 'CubeGuiForm'):
        uid = self.ui.lineAdminRfidResetter.text()
        rfid_line = CubeRfidLine(uid=uid, timestamp=time.time())
        if not rfid_line.is_valid():
            self.set_admin_command_status_text(f"❌ RFID non valide.")
            return False
        self.set_admin_command_status_text("⌛ Ajout de la carte RFID en cours...")
        report = self.fd.add_resetter_rfid(uid)
        if report:
            self.set_admin_command_status_text("✔️ Carte RFID ajoutée avec succès.")
        else:
            self.set_admin_command_status_text(f"❌ Erreur lors de l'ajout de la carte RFID: {report.ack_info}")
        return report

    @cubetry
    def remove_rfid_resetter(self: 'CubeGuiForm'):
        uid = self.ui.lineAdminRfidResetter.text()
        rfid_line = CubeRfidLine(uid)
        if not rfid_line.is_valid():
            self.set_admin_command_status_text(f"❌ RFID non valide.")
            return False
        self.set_admin_command_status_text("⌛ Suppression de la carte RFID en cours...")
        report = self.fd.remove_resetter_rfid(uid)
        if report:
            self.set_admin_command_status_text("✔️ Carte RFID supprimée avec succès.")
        else:
            if report is None:
                self.set_admin_command_status_text("❌ Erreur lors de la suppression de la carte RFID: Exception levée.")
            else:
                self.set_admin_command_status_text(f"❌ Erreur lors de la suppression de la carte RFID: {report.ack_info}")
        return report

    @cubetry
    def request_servers_infos(self: 'CubeGuiForm', background_task=False) -> 'CubeGuiTaskResult':
        """Request the servers infos from the CubeMaster and CubeBoxes and update the GUI accordingly.
        If background_task is True, the task will be started in a background thread."""

        def _task_request_servers_infos() -> 'CubeGuiTaskResult':
            task_success_info = ""
            success = True
            reply_timeout = STATUS_REPLY_TIMEOUT
            reply_timeout = 1
            give_up_if_cubemaster_unresponsive = False
            self.set_servers_info_status_label("hourglass", "En attente de réponse du CubeMaster...")
            report = self.fd.request_cubemaster_status(reply_timeout=reply_timeout)
            if not report.ack_ok:
                self.set_servers_info_status_label("error", "Erreur lors de la mise à jour totale.")
                task_success_info = "❌ Le CubeMaster n'a pas répondu. "
                success = False
            else:
                task_success_info = "✔️ CubeMaster a répondu. "

            if success or not give_up_if_cubemaster_unresponsive:
                self.set_servers_info_status_label("hourglass", "En attente de réponse des Cubeboxes...")
                report = self.fd.request_all_cubeboxes_statuses_one_by_one(
                    reply_timeout=reply_timeout,
                    stop_at_first_failure=True)
                if not report.ack_ok:
                    success = False
                    task_success_info += f"❌ CubeBoxes sans réponse: {str(report.ack_info)}"
                else:
                    task_success_info += "✔️ Toutes les CubeBoxes ont répondu."

            if success:
                self.log.success(task_success_info)
            else:
                self.log.error(task_success_info)
            self.set_servers_info_status_label(icon="", info=task_success_info)
            self.update_tab_admin()
            return CubeGuiTaskResult(success, task_success_info)

        if background_task:
            self.start_in_thread(_task_request_servers_infos)
            return CubeGuiTaskResult(True, "Task started in the background.")
        else:
            result = _task_request_servers_infos()
            self.set_servers_info_status_label(icon="", info=result.info)
            return result

    @cubetry
    def set_servers_info_status_label(self: 'CubeGuiForm', icon: str, info: str):
        # print(f"set_servers_info_status_label: {icon}, {info} called from {tb.extract_stack(limit=2)[0].name}")
        icon = ""
        if icon == "ok":
            icon = "✅"
        elif icon == "error":
            icon = "❌"
        elif icon == "warning":
            icon = "⚠️"
        elif icon in ("hourglass", "wait"):
            icon = "⌛"
        info = f"{icon} {info}"
        self.ui.lblAdminServersInfoStatusText.setText(info)
        # self.ui.btnIconAdminStatus.setIcon(QtGui.QIcon.fromTheme(icon))
        self.update_gui()

    def update_tab_admin(self: 'CubeGuiForm'):
        # print("update_tab_admin")
        try:
            # if True:
            print("update_tab_admin")
            table = self.ui.tableAdminServersInfo
            table.clearContents()
            node_names = [ci.CUBEFRONTDESK_NODENAME, ci.CUBEMASTER_NODENAME] + list(ci.CUBEBOXES_NODENAMES)
            # rows: FrontDesk, CubeMaster, CubeBoxes 1 to NB_CUBEBOXES
            # vertical headers: Node name
            # columns: last message time (hh:mm:ss) IP address, Status
            table.setRowCount(ci.NB_CUBEBOXES + 2)
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(
                ["Heure dernier msg", "IP", "Statut"])
            table.setVerticalHeaderLabels(node_names)
            for i, node_name in enumerate(node_names):
                last_msg_timestamp = self.fd.net.nodes_list.get_last_msg_timestamp_from_node_name(node_name)
                last_msg_hhmmss = cube_utils.timestamp_to_hhmmss_time_of_day_string(last_msg_timestamp,
                                                                                    separators="::")
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
            self.set_servers_info_status_label("error", f" {e}")

    @cubetry
    def send_command_clicked(self: 'CubeGuiForm'):
        self.ui.lblAdminCommandStatusText.setText("⌛ Envoi de la commande en cours...")
        self.update_gui()
        command = self.ui.lineAdminCommand.text()
        report = self.fd.send_full_command(command)
        if not report.ack_ok:
            self.ui.lblAdminCommandStatusText.setText(
                f"❌ Erreur lors de l'envoi de la commande '{command}': {report.ack_info}")
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
