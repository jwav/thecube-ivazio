# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'cubegui.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1001, 981)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("../../../../../home/vee/.designer/resources/icon_thecube_32x32.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Form.setWindowIcon(icon)
        Form.setIconSize(QtCore.QSize(32, 32))
        self.centralwidget = QtWidgets.QWidget(Form)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout_17 = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout_17.setObjectName("horizontalLayout_17")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_17.addItem(spacerItem)
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setLocale(QtCore.QLocale(QtCore.QLocale.French, QtCore.QLocale.France))
        self.tabWidget.setObjectName("tabWidget")
        self.tabMain = QtWidgets.QWidget()
        self.tabMain.setObjectName("tabMain")
        self.tabVerticalLayout = QtWidgets.QVBoxLayout(self.tabMain)
        self.tabVerticalLayout.setObjectName("tabVerticalLayout")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.lblTopBanner = QtWidgets.QLabel(self.tabMain)
        self.lblTopBanner.setPixmap(QtGui.QPixmap(":/images/images/logo_thecube-125x150.png"))
        self.lblTopBanner.setAlignment(QtCore.Qt.AlignCenter)
        self.lblTopBanner.setObjectName("lblTopBanner")
        self.verticalLayout_2.addWidget(self.lblTopBanner)
        self.tabVerticalLayout.addLayout(self.verticalLayout_2)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.tabVerticalLayout.addItem(spacerItem1)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.lblNewteamStatusText_2 = QtWidgets.QLabel(self.tabMain)
        font = QtGui.QFont()
        font.setFamily("Noto Serif")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.lblNewteamStatusText_2.setFont(font)
        self.lblNewteamStatusText_2.setAlignment(QtCore.Qt.AlignCenter)
        self.lblNewteamStatusText_2.setObjectName("lblNewteamStatusText_2")
        self.horizontalLayout_7.addWidget(self.lblNewteamStatusText_2)
        self.tabVerticalLayout.addLayout(self.horizontalLayout_7)
        spacerItem2 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.tabVerticalLayout.addItem(spacerItem2)
        self.gridLayout_6 = QtWidgets.QGridLayout()
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.lineNewteamRfid = QtWidgets.QLineEdit(self.tabMain)
        self.lineNewteamRfid.setMaximumSize(QtCore.QSize(100, 16777215))
        font = QtGui.QFont()
        font.setFamily("DejaVu Sans Mono")
        font.setBold(True)
        font.setWeight(75)
        self.lineNewteamRfid.setFont(font)
        self.lineNewteamRfid.setAlignment(QtCore.Qt.AlignCenter)
        self.lineNewteamRfid.setReadOnly(True)
        self.lineNewteamRfid.setObjectName("lineNewteamRfid")
        self.gridLayout_6.addWidget(self.lineNewteamRfid, 2, 3, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.tabMain)
        self.label_3.setObjectName("label_3")
        self.gridLayout_6.addWidget(self.label_3, 1, 2, 1, 1)
        self.lineNewteamTeamCustomName = QtWidgets.QLineEdit(self.tabMain)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineNewteamTeamCustomName.sizePolicy().hasHeightForWidth())
        self.lineNewteamTeamCustomName.setSizePolicy(sizePolicy)
        self.lineNewteamTeamCustomName.setMinimumSize(QtCore.QSize(400, 0))
        self.lineNewteamTeamCustomName.setObjectName("lineNewteamTeamCustomName")
        self.gridLayout_6.addWidget(self.lineNewteamTeamCustomName, 1, 3, 1, 3)
        self.lblNewteamTeamName = QtWidgets.QLabel(self.tabMain)
        self.lblNewteamTeamName.setObjectName("lblNewteamTeamName")
        self.gridLayout_6.addWidget(self.lblNewteamTeamName, 0, 2, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_6.addItem(spacerItem3, 2, 0, 1, 1)
        self.btnIconNewteamRfidStatus = QtWidgets.QPushButton(self.tabMain)
        self.btnIconNewteamRfidStatus.setEnabled(True)
        self.btnIconNewteamRfidStatus.setStyleSheet("QPushButton {\n"
"    background-color: none;\n"
"    border: none;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: none;\n"
"    border: none;\n"
"}\n"
"QPushButton:focus {\n"
"    outline: none;\n"
"}")
        self.btnIconNewteamRfidStatus.setText("")
        icon = QtGui.QIcon.fromTheme("error")
        self.btnIconNewteamRfidStatus.setIcon(icon)
        self.btnIconNewteamRfidStatus.setCheckable(False)
        self.btnIconNewteamRfidStatus.setFlat(True)
        self.btnIconNewteamRfidStatus.setObjectName("btnIconNewteamRfidStatus")
        self.gridLayout_6.addWidget(self.btnIconNewteamRfidStatus, 2, 1, 1, 1)
        self.btnNewteamRfidClear = QtWidgets.QPushButton(self.tabMain)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btnNewteamRfidClear.sizePolicy().hasHeightForWidth())
        self.btnNewteamRfidClear.setSizePolicy(sizePolicy)
        self.btnNewteamRfidClear.setText("")
        icon = QtGui.QIcon.fromTheme("edit-clear")
        self.btnNewteamRfidClear.setIcon(icon)
        self.btnNewteamRfidClear.setObjectName("btnNewteamRfidClear")
        self.gridLayout_6.addWidget(self.btnNewteamRfidClear, 2, 4, 1, 1)
        self.lblNewteamRfid = QtWidgets.QLabel(self.tabMain)
        self.lblNewteamRfid.setObjectName("lblNewteamRfid")
        self.gridLayout_6.addWidget(self.lblNewteamRfid, 2, 2, 1, 1)
        self.lblNewteamAllocatedTime = QtWidgets.QLabel(self.tabMain)
        self.lblNewteamAllocatedTime.setObjectName("lblNewteamAllocatedTime")
        self.gridLayout_6.addWidget(self.lblNewteamAllocatedTime, 3, 2, 1, 1)
        self.comboNewteamDuration = QtWidgets.QComboBox(self.tabMain)
        self.comboNewteamDuration.setMaxVisibleItems(20)
        self.comboNewteamDuration.setObjectName("comboNewteamDuration")
        self.comboNewteamDuration.addItem("")
        self.comboNewteamDuration.addItem("")
        self.gridLayout_6.addWidget(self.comboNewteamDuration, 3, 3, 1, 1)
        self.comboNewteamTeamName = QtWidgets.QComboBox(self.tabMain)
        self.comboNewteamTeamName.setMaxVisibleItems(20)
        self.comboNewteamTeamName.setObjectName("comboNewteamTeamName")
        self.comboNewteamTeamName.addItem("")
        self.comboNewteamTeamName.addItem("")
        self.gridLayout_6.addWidget(self.comboNewteamTeamName, 0, 3, 1, 1)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_6.addItem(spacerItem4, 2, 6, 1, 1)
        self.tabVerticalLayout.addLayout(self.gridLayout_6)
        spacerItem5 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.tabVerticalLayout.addItem(spacerItem5)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem6)
        self.btnNewteamNewTeam = QtWidgets.QPushButton(self.tabMain)
        self.btnNewteamNewTeam.setObjectName("btnNewteamNewTeam")
        self.horizontalLayout_4.addWidget(self.btnNewteamNewTeam)
        spacerItem7 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem7)
        self.tabVerticalLayout.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        spacerItem8 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem8)
        self.btnIconNewteamNewTeamStatus = QtWidgets.QPushButton(self.tabMain)
        self.btnIconNewteamNewTeamStatus.setEnabled(True)
        self.btnIconNewteamNewTeamStatus.setStyleSheet("QPushButton {\n"
"    background-color: none;\n"
"    border: none;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: none;\n"
"    border: none;\n"
"}\n"
"QPushButton:focus {\n"
"    outline: none;\n"
"}")
        self.btnIconNewteamNewTeamStatus.setText("")
        self.btnIconNewteamNewTeamStatus.setCheckable(False)
        self.btnIconNewteamNewTeamStatus.setFlat(True)
        self.btnIconNewteamNewTeamStatus.setObjectName("btnIconNewteamNewTeamStatus")
        self.horizontalLayout_5.addWidget(self.btnIconNewteamNewTeamStatus)
        self.lblNewteamNewTeamStatusText = QtWidgets.QLabel(self.tabMain)
        self.lblNewteamNewTeamStatusText.setObjectName("lblNewteamNewTeamStatusText")
        self.horizontalLayout_5.addWidget(self.lblNewteamNewTeamStatusText)
        spacerItem9 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem9)
        self.tabVerticalLayout.addLayout(self.horizontalLayout_5)
        spacerItem10 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.tabVerticalLayout.addItem(spacerItem10)
        self.tabWidget.addTab(self.tabMain, "")
        self.tabFinishedGames = QtWidgets.QWidget()
        self.tabFinishedGames.setObjectName("tabFinishedGames")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.tabFinishedGames)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.label_5 = QtWidgets.QLabel(self.tabFinishedGames)
        self.label_5.setText("")
        self.label_5.setPixmap(QtGui.QPixmap(":/images/images/logo_thecube-125x150.png"))
        self.label_5.setAlignment(QtCore.Qt.AlignCenter)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_11.addWidget(self.label_5)
        self.verticalLayout_3.addLayout(self.horizontalLayout_11)
        spacerItem11 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout_3.addItem(spacerItem11)
        self.horizontalLayout_12 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        self.lblNewteamStatusText_6 = QtWidgets.QLabel(self.tabFinishedGames)
        font = QtGui.QFont()
        font.setFamily("Noto Serif")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.lblNewteamStatusText_6.setFont(font)
        self.lblNewteamStatusText_6.setAlignment(QtCore.Qt.AlignCenter)
        self.lblNewteamStatusText_6.setObjectName("lblNewteamStatusText_6")
        self.horizontalLayout_12.addWidget(self.lblNewteamStatusText_6)
        self.verticalLayout_3.addLayout(self.horizontalLayout_12)
        spacerItem12 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout_3.addItem(spacerItem12)
        self.gridLayout_3 = QtWidgets.QGridLayout()
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.btnTeamsSearch = QtWidgets.QPushButton(self.tabFinishedGames)
        self.btnTeamsSearch.setObjectName("btnTeamsSearch")
        self.gridLayout_3.addWidget(self.btnTeamsSearch, 4, 1, 1, 2)
        self.label_8 = QtWidgets.QLabel(self.tabFinishedGames)
        self.label_8.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_8.setObjectName("label_8")
        self.gridLayout_3.addWidget(self.label_8, 3, 0, 1, 1)
        self.lineTeamsRfid = QtWidgets.QLineEdit(self.tabFinishedGames)
        self.lineTeamsRfid.setMaximumSize(QtCore.QSize(100, 16777215))
        font = QtGui.QFont()
        font.setFamily("DejaVu Sans Mono")
        font.setBold(True)
        font.setWeight(75)
        self.lineTeamsRfid.setFont(font)
        self.lineTeamsRfid.setAlignment(QtCore.Qt.AlignCenter)
        self.lineTeamsRfid.setReadOnly(False)
        self.lineTeamsRfid.setPlaceholderText("")
        self.lineTeamsRfid.setObjectName("lineTeamsRfid")
        self.gridLayout_3.addWidget(self.lineTeamsRfid, 2, 1, 1, 1)
        self.lblNewteamTeamName_4 = QtWidgets.QLabel(self.tabFinishedGames)
        self.lblNewteamTeamName_4.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lblNewteamTeamName_4.setObjectName("lblNewteamTeamName_4")
        self.gridLayout_3.addWidget(self.lblNewteamTeamName_4, 1, 0, 1, 1)
        self.lineTeamsCustomName = QtWidgets.QLineEdit(self.tabFinishedGames)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineTeamsCustomName.sizePolicy().hasHeightForWidth())
        self.lineTeamsCustomName.setSizePolicy(sizePolicy)
        self.lineTeamsCustomName.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setFamily("DejaVu Sans Mono")
        font.setBold(True)
        font.setWeight(75)
        self.lineTeamsCustomName.setFont(font)
        self.lineTeamsCustomName.setAlignment(QtCore.Qt.AlignCenter)
        self.lineTeamsCustomName.setReadOnly(False)
        self.lineTeamsCustomName.setPlaceholderText("")
        self.lineTeamsCustomName.setObjectName("lineTeamsCustomName")
        self.gridLayout_3.addWidget(self.lineTeamsCustomName, 1, 1, 1, 3)
        self.lblNewteamRfid_3 = QtWidgets.QLabel(self.tabFinishedGames)
        self.lblNewteamRfid_3.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lblNewteamRfid_3.setObjectName("lblNewteamRfid_3")
        self.gridLayout_3.addWidget(self.lblNewteamRfid_3, 2, 0, 1, 1)
        self.radioTeamsToday = QtWidgets.QRadioButton(self.tabFinishedGames)
        self.radioTeamsToday.setObjectName("radioTeamsToday")
        self.gridLayout_3.addWidget(self.radioTeamsToday, 3, 2, 1, 1)
        spacerItem13 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem13, 3, 6, 1, 1)
        self.comboTeamsTeamName = QtWidgets.QComboBox(self.tabFinishedGames)
        self.comboTeamsTeamName.setMaxVisibleItems(20)
        self.comboTeamsTeamName.setObjectName("comboTeamsTeamName")
        self.gridLayout_3.addWidget(self.comboTeamsTeamName, 0, 1, 1, 1)
        self.lblNewteamTeamName_3 = QtWidgets.QLabel(self.tabFinishedGames)
        self.lblNewteamTeamName_3.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lblNewteamTeamName_3.setObjectName("lblNewteamTeamName_3")
        self.gridLayout_3.addWidget(self.lblNewteamTeamName_3, 0, 0, 1, 1)
        self.radioTeamsNoDate = QtWidgets.QRadioButton(self.tabFinishedGames)
        self.radioTeamsNoDate.setObjectName("radioTeamsNoDate")
        self.gridLayout_3.addWidget(self.radioTeamsNoDate, 3, 5, 1, 1)
        self.radioTeamsCurrentlyPlaying = QtWidgets.QRadioButton(self.tabFinishedGames)
        self.radioTeamsCurrentlyPlaying.setChecked(True)
        self.radioTeamsCurrentlyPlaying.setObjectName("radioTeamsCurrentlyPlaying")
        self.gridLayout_3.addWidget(self.radioTeamsCurrentlyPlaying, 3, 1, 1, 1)
        self.radioTeamsThisWeek = QtWidgets.QRadioButton(self.tabFinishedGames)
        self.radioTeamsThisWeek.setObjectName("radioTeamsThisWeek")
        self.gridLayout_3.addWidget(self.radioTeamsThisWeek, 3, 3, 1, 1)
        self.radioTeamsThisMonth = QtWidgets.QRadioButton(self.tabFinishedGames)
        self.radioTeamsThisMonth.setObjectName("radioTeamsThisMonth")
        self.gridLayout_3.addWidget(self.radioTeamsThisMonth, 3, 4, 1, 1)
        self.verticalLayout_3.addLayout(self.gridLayout_3)
        self.tableTeamsResults = QtWidgets.QTableWidget(self.tabFinishedGames)
        self.tableTeamsResults.setMinimumSize(QtCore.QSize(800, 0))
        self.tableTeamsResults.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableTeamsResults.setObjectName("tableTeamsResults")
        self.tableTeamsResults.setColumnCount(8)
        self.tableTeamsResults.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsResults.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsResults.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsResults.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsResults.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsResults.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsResults.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsResults.setHorizontalHeaderItem(6, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsResults.setHorizontalHeaderItem(7, item)
        self.tableTeamsResults.horizontalHeader().setStretchLastSection(True)
        self.tableTeamsResults.verticalHeader().setVisible(False)
        self.verticalLayout_3.addWidget(self.tableTeamsResults)
        self.gridLayout_4 = QtWidgets.QGridLayout()
        self.gridLayout_4.setObjectName("gridLayout_4")
        spacerItem14 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_4.addItem(spacerItem14, 0, 3, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.tabFinishedGames)
        self.label_2.setObjectName("label_2")
        self.gridLayout_4.addWidget(self.label_2, 0, 0, 1, 1)
        self.comboTeamsAddTrophy = QtWidgets.QComboBox(self.tabFinishedGames)
        self.comboTeamsAddTrophy.setObjectName("comboTeamsAddTrophy")
        self.gridLayout_4.addWidget(self.comboTeamsAddTrophy, 0, 1, 1, 1)
        self.btnTeamsAddTrophy = QtWidgets.QPushButton(self.tabFinishedGames)
        self.btnTeamsAddTrophy.setObjectName("btnTeamsAddTrophy")
        self.gridLayout_4.addWidget(self.btnTeamsAddTrophy, 0, 2, 1, 1)
        self.btnTeamsRemoveSelectedTrophy = QtWidgets.QPushButton(self.tabFinishedGames)
        self.btnTeamsRemoveSelectedTrophy.setObjectName("btnTeamsRemoveSelectedTrophy")
        self.gridLayout_4.addWidget(self.btnTeamsRemoveSelectedTrophy, 0, 4, 1, 1)
        self.verticalLayout_3.addLayout(self.gridLayout_4)
        self.tableTeamsTrophyList = QtWidgets.QTableWidget(self.tabFinishedGames)
        self.tableTeamsTrophyList.setObjectName("tableTeamsTrophyList")
        self.tableTeamsTrophyList.setColumnCount(4)
        self.tableTeamsTrophyList.setRowCount(1)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsTrophyList.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsTrophyList.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsTrophyList.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsTrophyList.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableTeamsTrophyList.setHorizontalHeaderItem(3, item)
        self.tableTeamsTrophyList.horizontalHeader().setStretchLastSection(True)
        self.tableTeamsTrophyList.verticalHeader().setVisible(False)
        self.verticalLayout_3.addWidget(self.tableTeamsTrophyList)
        self.horizontalLayout_14 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_14.setObjectName("horizontalLayout_14")
        spacerItem15 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_14.addItem(spacerItem15)
        self.btnTeamsPrintScoresheet = QtWidgets.QPushButton(self.tabFinishedGames)
        icon = QtGui.QIcon.fromTheme("print")
        self.btnTeamsPrintScoresheet.setIcon(icon)
        self.btnTeamsPrintScoresheet.setObjectName("btnTeamsPrintScoresheet")
        self.horizontalLayout_14.addWidget(self.btnTeamsPrintScoresheet)
        spacerItem16 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_14.addItem(spacerItem16)
        self.verticalLayout_3.addLayout(self.horizontalLayout_14)
        spacerItem17 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem17)
        self.tabWidget.addTab(self.tabFinishedGames, "")
        self.tabAdmin = QtWidgets.QWidget()
        self.tabAdmin.setObjectName("tabAdmin")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.tabAdmin)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.tabAdmin)
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap(":/images/images/logo_thecube-125x150.png"))
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.verticalLayout.addLayout(self.horizontalLayout)
        spacerItem18 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem18)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.lblNewteamStatusText_5 = QtWidgets.QLabel(self.tabAdmin)
        font = QtGui.QFont()
        font.setFamily("Noto Serif")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.lblNewteamStatusText_5.setFont(font)
        self.lblNewteamStatusText_5.setAlignment(QtCore.Qt.AlignCenter)
        self.lblNewteamStatusText_5.setObjectName("lblNewteamStatusText_5")
        self.horizontalLayout_3.addWidget(self.lblNewteamStatusText_5)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        spacerItem19 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem19)
        self.gridLayout_8 = QtWidgets.QGridLayout()
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.tableAdminNodesStatusLeft = QtWidgets.QTableWidget(self.tabAdmin)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableAdminNodesStatusLeft.sizePolicy().hasHeightForWidth())
        self.tableAdminNodesStatusLeft.setSizePolicy(sizePolicy)
        self.tableAdminNodesStatusLeft.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.tableAdminNodesStatusLeft.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableAdminNodesStatusLeft.setAlternatingRowColors(True)
        self.tableAdminNodesStatusLeft.setRowCount(15)
        self.tableAdminNodesStatusLeft.setObjectName("tableAdminNodesStatusLeft")
        self.tableAdminNodesStatusLeft.setColumnCount(3)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(6, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(7, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(8, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(9, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(10, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(11, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(12, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setVerticalHeaderItem(13, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableAdminNodesStatusLeft.setHorizontalHeaderItem(2, item)
        self.tableAdminNodesStatusLeft.horizontalHeader().setStretchLastSection(True)
        self.gridLayout_8.addWidget(self.tableAdminNodesStatusLeft, 0, 0, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout_8)
        self.gridLayout_7 = QtWidgets.QGridLayout()
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.pushButton = QtWidgets.QPushButton(self.tabAdmin)
        self.pushButton.setObjectName("pushButton")
        self.gridLayout_7.addWidget(self.pushButton, 0, 1, 1, 1)
        spacerItem20 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_7.addItem(spacerItem20, 0, 0, 1, 1)
        spacerItem21 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_7.addItem(spacerItem21, 0, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout_7)
        spacerItem22 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem22)
        self.horizontalLayout_18 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_18.setObjectName("horizontalLayout_18")
        self.label_20 = QtWidgets.QLabel(self.tabAdmin)
        self.label_20.setObjectName("label_20")
        self.horizontalLayout_18.addWidget(self.label_20)
        self.lineEdit_4 = QtWidgets.QLineEdit(self.tabAdmin)
        self.lineEdit_4.setObjectName("lineEdit_4")
        self.horizontalLayout_18.addWidget(self.lineEdit_4)
        self.pushButton_4 = QtWidgets.QPushButton(self.tabAdmin)
        self.pushButton_4.setObjectName("pushButton_4")
        self.horizontalLayout_18.addWidget(self.pushButton_4)
        self.verticalLayout.addLayout(self.horizontalLayout_18)
        self.listWidget = QtWidgets.QListWidget(self.tabAdmin)
        self.listWidget.setObjectName("listWidget")
        self.verticalLayout.addWidget(self.listWidget)
        self.tabWidget.addTab(self.tabAdmin, "")
        self.horizontalLayout_17.addWidget(self.tabWidget)
        spacerItem23 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_17.addItem(spacerItem23)
        Form.setCentralWidget(self.centralwidget)

        self.retranslateUi(Form)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Interface TheCube"))
        self.lblNewteamStatusText_2.setText(_translate("Form", "CRÉER UNE NOUVELLE ÉQUIPE"))
        self.lineNewteamRfid.setText(_translate("Form", "1234567890"))
        self.lineNewteamRfid.setPlaceholderText(_translate("Form", "----------"))
        self.label_3.setText(_translate("Form", "Nom personnalisé : "))
        self.lblNewteamTeamName.setText(_translate("Form", "Nom de code :"))
        self.lblNewteamRfid.setText(_translate("Form", "Badge RFID : "))
        self.lblNewteamAllocatedTime.setText(_translate("Form", "Temps alloué : "))
        self.comboNewteamDuration.setItemText(0, _translate("Form", "0h10"))
        self.comboNewteamDuration.setItemText(1, _translate("Form", "0h20"))
        self.comboNewteamTeamName.setItemText(0, _translate("Form", "NomDeVille1"))
        self.comboNewteamTeamName.setItemText(1, _translate("Form", "NomDeVille2"))
        self.btnNewteamNewTeam.setText(_translate("Form", "Créer une nouvelle équipe"))
        self.lblNewteamNewTeamStatusText.setText(_translate("Form", "-- statut de la création d\'équipe --"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabMain), _translate("Form", "Créer une nouvelle équipe"))
        self.lblNewteamStatusText_6.setText(_translate("Form", "GÉRER LES ÉQUIPES"))
        self.btnTeamsSearch.setText(_translate("Form", "Rechercher équipes"))
        self.label_8.setText(_translate("Form", "Date de jeu : "))
        self.lblNewteamTeamName_4.setText(_translate("Form", "Nom personnalisé :"))
        self.lblNewteamRfid_3.setText(_translate("Form", "Badge RFID : "))
        self.radioTeamsToday.setText(_translate("Form", "aujourd\'hui"))
        self.lblNewteamTeamName_3.setText(_translate("Form", "Nom de l\'équipe : "))
        self.radioTeamsNoDate.setText(_translate("Form", "sans date"))
        self.radioTeamsCurrentlyPlaying.setText(_translate("Form", "en cours de jeu"))
        self.radioTeamsThisWeek.setText(_translate("Form", "cette semaine"))
        self.radioTeamsThisMonth.setText(_translate("Form", "ce mois"))
        item = self.tableTeamsResults.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Date"))
        item = self.tableTeamsResults.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Nom"))
        item = self.tableTeamsResults.horizontalHeaderItem(2)
        item.setText(_translate("Form", "Nom personnalisé"))
        item = self.tableTeamsResults.horizontalHeaderItem(3)
        item.setText(_translate("Form", "Score"))
        item = self.tableTeamsResults.horizontalHeaderItem(4)
        item.setText(_translate("Form", "Cubes faits"))
        item = self.tableTeamsResults.horizontalHeaderItem(5)
        item.setText(_translate("Form", "Début"))
        item = self.tableTeamsResults.horizontalHeaderItem(6)
        item.setText(_translate("Form", "Fin"))
        item = self.tableTeamsResults.horizontalHeaderItem(7)
        item.setText(_translate("Form", "RFID UID"))
        self.label_2.setText(_translate("Form", "Ajouter un trophée pour cette équipe : "))
        self.btnTeamsAddTrophy.setText(_translate("Form", "Ajouter tophée"))
        self.btnTeamsRemoveSelectedTrophy.setText(_translate("Form", "Supprimer le trophée sélectrionné"))
        item = self.tableTeamsTrophyList.verticalHeaderItem(0)
        item.setText(_translate("Form", "New Row"))
        item = self.tableTeamsTrophyList.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Trophée"))
        item = self.tableTeamsTrophyList.horizontalHeaderItem(1)
        item.setText(_translate("Form", "Image"))
        item = self.tableTeamsTrophyList.horizontalHeaderItem(2)
        item.setText(_translate("Form", "Points"))
        item = self.tableTeamsTrophyList.horizontalHeaderItem(3)
        item.setText(_translate("Form", "Description"))
        self.btnTeamsPrintScoresheet.setText(_translate("Form", "Imprimer la feuille de score"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabFinishedGames), _translate("Form", "Gérer les équipes"))
        self.lblNewteamStatusText_5.setText(_translate("Form", "ADMINISTRATION ET CONTRÔLE"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(0)
        item.setText(_translate("Form", "CubeFrontdesk"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(1)
        item.setText(_translate("Form", "CubeMaster"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(2)
        item.setText(_translate("Form", "CubeBox1"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(3)
        item.setText(_translate("Form", "CubeBox2"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(4)
        item.setText(_translate("Form", "CubeBox3"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(5)
        item.setText(_translate("Form", "CubeBox4"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(6)
        item.setText(_translate("Form", "New Row"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(7)
        item.setText(_translate("Form", "New Row"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(8)
        item.setText(_translate("Form", "New Row"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(9)
        item.setText(_translate("Form", "New Row"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(10)
        item.setText(_translate("Form", "New Row"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(11)
        item.setText(_translate("Form", "New Row"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(12)
        item.setText(_translate("Form", "New Row"))
        item = self.tableAdminNodesStatusLeft.verticalHeaderItem(13)
        item.setText(_translate("Form", "New Row"))
        item = self.tableAdminNodesStatusLeft.horizontalHeaderItem(0)
        item.setText(_translate("Form", "Dernier msg"))
        item = self.tableAdminNodesStatusLeft.horizontalHeaderItem(1)
        item.setText(_translate("Form", "IP"))
        item = self.tableAdminNodesStatusLeft.horizontalHeaderItem(2)
        item.setText(_translate("Form", "Statut"))
        self.pushButton.setText(_translate("Form", "Mise à jour infos serveurs"))
        self.label_20.setText(_translate("Form", "Commande > "))
        self.pushButton_4.setText(_translate("Form", "Envoyer"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabAdmin), _translate("Form", "Administration et contrôle"))
import resources_rc
