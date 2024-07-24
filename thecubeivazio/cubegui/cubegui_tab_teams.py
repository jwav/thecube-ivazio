"""File for the mixin class (partial for CubeGuiForm) for the teams management tab."""

import sys
import time
from typing import TYPE_CHECKING

import fitz  # PyMuPDF
from PyQt5 import QtGui
from PyQt5.QtCore import QFile
from PyQt5.QtGui import QIcon, QPainter, QImage
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QMessageBox

from cubegui_ui import Ui_Form
from thecubeivazio import cube_game
from thecubeivazio import cube_logger as cube_logger
from thecubeivazio import cube_utils
from thecubeivazio import cubeserver_frontdesk as cfd
from thecubeivazio.cube_common_defines import *

if TYPE_CHECKING:
    from cubegui import CubeGuiForm


# /_noinspection PyUnresolvedReferences
class CubeGuiTabTeamsMixin:
    self: 'CubeGuiForm'
    ui: Ui_Form
    log: cube_logger.CubeLogger
    fd: cfd.CubeServerFrontdesk

    def setup_tab_teams(self: 'CubeGuiForm'):
        self.ui: Ui_Form

        # fill the team names combo box
        team_names = [""]  # empty string for "all teams"
        team_names.extend(self.fd.config.defined_team_names)
        # print(team_names)
        self.ui.comboTeamsTeamName.clear()
        self.ui.comboTeamsTeamName.addItems(team_names)

        # clear the RFID line edit
        self.ui.lineTeamsRfid.clear()

        # select the default radio button for the search period
        # self.ui.radioTeamsCurrentlyPlaying.setChecked(True)
        self.ui.spinTeamsAmountOfDays.valueChanged.connect(lambda value: self.ui.radioTeamsLessThanXDays.setChecked(True))
        self.ui.radioTeamsCurrentlyPlaying.setChecked(True)

        # connect the "search" button
        self.ui.btnTeamsSearch.clicked.connect(self.click_search_teams)

        # connect the "delete team" button
        self.ui.btnTeamsDeleteTeam.clicked.connect(self.click_delete_team)

        # clear and setup the results table
        self.ui.tableTeamsResults.clearContents()
        self.ui.tableTeamsResults.cellClicked.connect(self.on_teams_results_cell_clicked)


        # fill the trophy combo box
        trophies = self.fd.config.defined_trophies
        self.ui.comboTeamsAddTrophy.clear()
        self.ui.comboTeamsAddTrophy.addItems((t.french_name for t in trophies))

        # connect the "add trophy" button
        self.ui.btnTeamsAddTrophy.clicked.connect(self.click_add_trophy)

        # connect the "remove trophy" button
        self.ui.btnTeamsRemoveSelectedTrophy.clicked.connect(self.click_remove_trophy)

        # clear the trophy table
        self.ui.tableTeamsTrophyList.clearContents()

        # connect the "print scoresheet" button
        self.ui.btnTeamsPrintScoresheet.clicked.connect(self.click_print_scoresheet)

        # update the tab
        self.update_tab_teams()

    @cubetry
    def set_teams_info_label_text(self, text: str):
        self.ui.lblTeamsStatusInfo.setText(text)
        QApplication.processEvents()

    @cubetry
    def get_trophy_pixmap(self, trophy: cube_game.CubeTrophy, width: int=None, height: int=None) -> QtGui.QPixmap:
        """Get the pixmap for a trophy"""
        assert trophy
        try:
            # self.log.critical(f"trophy.image_filename: {trophy.image_filename}")
            # self.log.critical(f"trophy.image_filepath: {trophy.image_filepath}")
            assert QFile.exists(trophy.image_filepath)
            pixmap = QtGui.QPixmap(trophy.image_filepath)
            # self.log.success(f"Loaded pixmap from file {trophy.image_filepath}")
        except Exception as e:
            # self.log.error(f"{e} : Could not load pixmap from file {trophy.image_filepath}")
            pixmap = QtGui.QPixmap(DEFAULT_TROPHY_IMAGE_FILEPATH)
        if width and height:
            pixmap = pixmap.scaled(width, height)
        assert pixmap
        return pixmap

    @cubetry
    def get_selected_team(self, row:int=None) -> Optional[cube_game.CubeTeamStatus]:
        """Get the team selected in the results table.
        It can be a currently playing team or a team from the database.
        """
        row = self.ui.tableTeamsResults.currentRow() if row is None else row
        if row < 0:
            self.log.error("get_selected_team: No row selected.")
            return None
        team_creation_timestamp_text = self.ui.tableTeamsResults.item(row, 0).text()
        team_name = self.ui.tableTeamsResults.item(row, 2).text()
        self.log.debug(f"team_creation_timestamp_text: {team_creation_timestamp_text}")
        team_creation_timestamp = float(team_creation_timestamp_text)
        # check the local teams list
        # team = self.fd.teams.find_team_by_creation_timestamp(team_creation_timestamp)
        team = self.fd.teams.get_team_by_name(team_name)
        # if not found in current teams, check the database
        if not team:
            team = self.fd.database.find_team_by_creation_timestamp(team_creation_timestamp)
        if not team:
            self.log.error(f"Could not find team with creation timestamp {team_creation_timestamp}")
            return None
        # self.log.debug(f"Selected team: {team}")
        # auto-compute the team's trophies
        team.auto_compute_trophies()
        return team

    @cubetry
    def get_selected_trophy_french_name(self) -> Optional[str]:
        """Get the trophy name selected in the trophies table."""
        row = self.ui.tableTeamsTrophyList.currentRow()
        if row < 0:
            self.log.error("get_selected_trophy_name: No row selected.")
            return None
        trophy_french_name = self.ui.tableTeamsTrophyList.item(row, 0).text()
        return trophy_french_name

    @cubetry
    def on_teams_results_cell_clicked(self: 'CubeGuiForm'):
        self.ui: Ui_Form
        self.log: cube_logger.CubeLogger
        table = self.ui.tableTeamsTrophyList
        table.clearContents()

        # identify the team from the row of the cell clicked
        team = self.get_selected_team()

        # update the trophies table
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Trophée", "Image", "Points", "Description"])
        table.setRowCount(len(team.trophies_names))
        for i, trophy_name in enumerate(team.trophies_names):
            trophy = cube_game.CubeTrophy.make_from_name(trophy_name)
            if not trophy:
                self.log.error(f"Could not find trophy with name {trophy_name}")
                continue
            trophy_pixmap = self.get_trophy_pixmap(trophy, width=20, height=20)
            # self.log.debug(f"trophy_pixmap: {trophy_pixmap}")
            # Create an icon from the QPixmap
            icon = QIcon(trophy_pixmap)
            # Create a QTableWidgetItem and set the icon
            trophy_pixmap_item = QTableWidgetItem()
            trophy_pixmap_item.setIcon(icon)
            table.setItem(i, 0, QTableWidgetItem(str(trophy.french_name)))
            table.setItem(i, 1, trophy_pixmap_item)
            table.setItem(i, 2, QTableWidgetItem(str(trophy.points)))
            table.setItem(i, 3, QTableWidgetItem(str(trophy.description)))
        total_row_height = sum(table.rowHeight(row) for row in range(table.rowCount()))
        total_row_height += table.horizontalHeader().height() + 2
        max_row_height = 5*table.rowHeight(0) + table.horizontalHeader().height() + 2
        table.setFixedHeight(min(total_row_height, max_row_height))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.updateGeometry()
        self.update_tab_teams()
        self.update_gui()



    def on_spinTeamsAmountOfDays_valueChanged(self, value):
        """Check the radio button when the spinbox value is changed"""
        self.ui: Ui_Form
        self.ui.radioTeamsLessThanXDays.setChecked(True)

    def update_tab_teams(self: 'CubeGuiForm'):
        pass

    def click_print_scoresheet(self):
        try:
            from thecubeivazio.cube_scoresheet import CubeScoresheet
            team = self.get_selected_team()
            if not team:
                raise Exception("Aucune équipe sélectionnée.")
            if not team.is_valid():
                raise Exception("Équipe invalide.")
            if self.fd.teams.has_team(team):
                raise Exception("Pas possible d'imprimer une feuille de score pour une équipe en cours de jeu.")
            scoresheet = CubeScoresheet(team)
            self.set_teams_info_label_text("⏳ Génération de la feuille de score en cours...")
            pdf_path = scoresheet.save_as_pdf_file_with_pyppeteer()
            # pdf_path = "/mnt/shared/thecube-ivazio/thecubeivazio/scoresheets/Dakar_1718297441_scoresheet.pdf"
            assert pdf_path, "Erreur lors de la génération du fichier PDF."
            assert os.path.exists(pdf_path), f"PDF file not found: {pdf_path}"

            printer = QPrinter(QPrinter.HighResolution)

            # Show the print preview dialog
            preview_dialog = QPrintPreviewDialog(printer, self)
            preview_dialog.paintRequested.connect(lambda: self.print_pdf(preview_dialog.printer(), pdf_path))
            preview_dialog.showMaximized()
            preview_dialog.exec()
        except Exception as e:
            self.log.error(f"Error in click_print_scoresheet: {e}")
            self.set_teams_info_label_text(f"❌ {str(e)}")
        finally:
            self.update_tab_teams()

    def print_pdf(self, printer, pdf_path):
        try:
            # Open the PDF document using PyMuPDF
            pdf_doc = fitz.open(pdf_path)

            # Create a QPainter object
            painter = QPainter(printer)

            # Iterate through the pages and render each one
            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                pix = page.get_pixmap(alpha=False)  # Disable alpha to avoid blank images

                # Convert the pixmap to a QImage
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

                # Check if the image dimensions are valid
                if img.width() == 0 or img.height() == 0:
                    continue

                # Calculate the scale factor
                scale = min(printer.pageRect().width() / img.width(), printer.pageRect().height() / img.height())
                painter.save()
                painter.translate(printer.pageRect().x(), printer.pageRect().y())
                painter.scale(scale, scale)

                # Draw the image
                painter.drawImage(0, 0, img)
                painter.restore()

                if page_num < len(pdf_doc) - 1:
                    printer.newPage()

            painter.end()
        except Exception as e:
            self.log.error(f"Error in print_pdf: {e}")
            self.set_teams_info_label_text(f"❌ {str(e)}")



    def click_add_trophy(self: 'CubeGuiForm'):
        try:
            # get the selected team
            team = self.get_selected_team()
            # check existence, validity
            assert team, "Aucune équipe sélectionnée."
            assert team.is_valid(), "Équipe invalide."
            # check that it's a database team and not currently playing
            assert not self.fd.teams.has_team(team), "Pas possible d'ajouter un trophée à une équipe en cours de jeu."
            # get the selected trophy
            trophy_french_name = self.ui.comboTeamsAddTrophy.currentText()
            trophy = cube_game.CubeTrophy.make_from_french_name(trophy_french_name)
            assert trophy, f"Impossible de trouver le trophée {trophy_french_name}."
            # check that the trophy is not already in the team
            assert trophy.name not in team.trophies_names, f"Le trophée {trophy_french_name} est déjà dans l'équipe."
            # add the trophy to the team
            team.add_trophy_by_name(trophy.name)
            # update the team in the database
            self.fd.database.update_team_in_database(team)
            # notify the CubeMaster
            assert self.fd.send_database_teams_to_cubemaster([team]), "Modification locale effectuée, mais erreur lors de l'envoi des équipes au CubeMaster."
            self.set_teams_info_label_text(f"✅ Trophée {trophy_french_name} ajouté à l'équipe {team.name}.")

        except Exception as e:
            self.log.error(f"Error in click_add_trophy: {e}")
            self.set_teams_info_label_text(f"❌ {str(e)}")
        finally:
            # refresh the tables
            self.on_teams_results_cell_clicked()
            # save the currently selected team (row)
            row = self.ui.tableTeamsResults.currentRow()
            self.click_search_teams()
            # restore the selected team (row)
            self.ui.tableTeamsResults.selectRow(row)
            self.update_all_tabs()

    def click_remove_trophy(self: 'CubeGuiForm'):
        try:
            # get the selected trophy name
            trophy_french_name = self.get_selected_trophy_french_name()
            # check existence, validity
            assert trophy_french_name, "Aucun trophée sélectionné."
            trophy = cube_game.CubeTrophy.make_from_french_name(trophy_french_name)
            assert trophy, f"Impossible de trouver le trophée {trophy_french_name}."
            # get the selected team
            team = self.get_selected_team()
            # check existence, validity
            assert team, "Aucune équipe sélectionnée."
            assert team.is_valid(), "Équipe invalide."
            # check that it's a database team and not currently playing
            assert not self.fd.teams.has_team(team), "Pas possible de retirer un trophée d'une équipe en cours de jeu."
            # check that the trophy is in the team
            assert trophy.name in team.trophies_names, f"Le trophée {trophy_name} n'est pas dans l'équipe."
            # remove the trophy from the team
            team.remove_trophy_by_name(trophy.name)
            # update the team in the database
            self.fd.database.update_team_in_database(team)
            # notify the CubeMaster
            self.fd.send_database_teams_to_cubemaster([team])
        except Exception as e:
            self.log.error(f"Error in click_remove_trophy: {e}")
            self.set_teams_info_label_text(f"❌ {str(e)}")
        finally:
            # refresh the tables
            self.on_teams_results_cell_clicked()
            # save the currently selected team (row)
            row = self.ui.tableTeamsResults.currentRow()
            self.click_search_teams()
            # restore the selected team (row)
            self.ui.tableTeamsResults.selectRow(row)
            self.update_all_tabs()




    @cubetry
    def click_delete_team(self: 'CubeGuiForm'):
        team = self.get_selected_team()
        assert team.is_valid()
        if not self.fd.teams.has_team(team):
            self.set_team_delete_info_status_label("error", "Il n'est pas permis de supprimer une équipe de la base de données.")
            return
        # display a confirmation dialog Yes/No
        reply = QMessageBox.question(self,
                                     "Suppression d'équipe",
                                     "Êtes-vous sûr de vouloir supprimer l'équipe ?\nCette action est irréversible.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        self.set_team_delete_info_status_label("hourglass", "En attente de réponse du CubeMaster...")
        if not self.fd.order_cubemaster_to_delete_team(team):
            self.set_team_delete_info_status_label("error", "Erreur lors de la suppression de l'équipe.")
            return
        self.set_team_delete_info_status_label("ok", "Suppression de l'équipe effectuée.")
        self.fd.request_cubemaster_status()
        self.click_search_teams()

    def set_team_delete_info_status_label(self, icon: str, info: str):
        self.ui.lblTeamsTeamDeleteStatus.setText(info)
        self.ui.btnIconTeamsTeamDeleteStatus.setIcon(QtGui.QIcon.fromTheme(icon))
        QApplication.processEvents()

    @cubetry
    def click_search_teams(self: 'CubeGuiForm'):
        self.ui: Ui_Form
        # assert False
        team_name = self.ui.comboTeamsTeamName.currentText()
        custom_name: str = self.ui.lineTeamsCustomName.text()
        rfid_uid = self.ui.lineTeamsRfid.text()

        if self.ui.radioTeamsCurrentlyPlaying.isChecked():
            # TODO: query current teams from the cubemaster
            # TODO: apply filters?
            matching_teams = self.fd.teams
            self.log.debug(f"playing teams: {self.fd.teams}")

        else:
            nb_days = self.ui.spinTeamsAmountOfDays.value()
            min_timestamp = time.time() - nb_days * 24 * 3600
            self.log.debug(f"min_timestamp: {min_timestamp}, i.e. {cube_utils.timestamp_to_date(min_timestamp)}")
            matching_teams = self.fd.database.find_teams_matching(name=team_name, custom_name=custom_name, rfid_uid=rfid_uid,
                                               min_creation_timestamp=min_timestamp, max_creation_timestamp=time.time())
        self.display_teams(matching_teams)

    @cubetry
    def display_teams(self, teams: cube_game.CubeTeamsStatusList):
        self.ui: Ui_Form

        if not teams:
            self.log.info("No matching teams found.")
            teams = cube_game.CubeTeamsStatusList()
        if not teams.is_valid():
            self.log.error("Invalid teams list.")
            return

        self.ui.tableTeamsResults.clearContents()
        self.ui.tableTeamsResults.setColumnCount(11)
        self.ui.tableTeamsResults.setHorizontalHeaderLabels(
            ["CrTmstmp", "Date", "Nom", "Nom personnalisé", "Score", "Cubes faits", "Trophées", "Création", "Début", "Fin", "RFID"])
        self.ui.tableTeamsResults.setRowCount(len(teams))

        for i, team in enumerate(teams):
            if not team.is_valid():
                self.log.error(f"Invalid team: {team}")
                continue
            #french_date = cube_utils.timestamp_to_french_date(team.start_timestamp)
            short_date = cube_utils.timestamp_to_date(team.start_timestamp)
            creation_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.creation_timestamp, separators=":", secs=False)
            start_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.start_timestamp, separators=":", secs=False)
            end_tod = cube_utils.timestamp_to_hhmmss_time_of_day_string(
                team.end_timestamp, separators=":", secs=False)
            self.log.debug(f"team: {team}, trophies_names: {team.trophies_names}")
            # trophies_str = ", ".join((trophy_name for trophy_name in team.trophies_names))
            # display one 🏆 for each trophy
            trophies_str = "🏆 " * len(team.trophies_names)

            # print(f"team: {team}")
            self.ui.tableTeamsResults.setItem(i, 0, QTableWidgetItem(str(team.creation_timestamp)))
            self.log.debug(f"team.creation_timestamp: {team.name} : {team.creation_timestamp} : {self.ui.tableTeamsResults.item(i, 0).text()}")
            self.ui.tableTeamsResults.setItem(i, 1, QTableWidgetItem(short_date))
            self.ui.tableTeamsResults.setItem(i, 2, QTableWidgetItem(team.name))
            self.ui.tableTeamsResults.setItem(i, 3, QTableWidgetItem(team.custom_name))
            self.ui.tableTeamsResults.setItem(i, 4, QTableWidgetItem(str(team.calculate_team_score())))
            self.ui.tableTeamsResults.setItem(i, 5, QTableWidgetItem(str(team.completed_cubebox_ids)))
            self.ui.tableTeamsResults.setItem(i, 6, QTableWidgetItem(trophies_str))
            self.ui.tableTeamsResults.setItem(i, 7, QTableWidgetItem(creation_tod))
            self.ui.tableTeamsResults.setItem(i, 8, QTableWidgetItem(start_tod))
            self.ui.tableTeamsResults.setItem(i, 9, QTableWidgetItem(end_tod))
            self.ui.tableTeamsResults.setItem(i, 10, QTableWidgetItem(team.rfid_uid))

        self.ui.tableTeamsResults.hideColumn(0)
        # Resize columns to fit contents and headers
        self.ui.tableTeamsResults.resizeColumnsToContents()


if __name__ == "__main__":
    from cubegui import CubeGuiForm
    import atexit
    app = QApplication(sys.argv)
    window = CubeGuiForm()
    atexit.register(window.close)
    window.show()

    window.ui.tabWidget.setCurrentIndex(1)
    window.ui.spinTeamsAmountOfDays.setValue(100)
    window.click_search_teams()

    sys.exit(app.exec_())

