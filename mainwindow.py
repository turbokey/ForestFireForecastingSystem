# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import QtWebEngineWidgets
from dateutil.relativedelta import relativedelta
import datetime

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setFixedSize(1200, 790)
        self.centralWidget = QtWidgets.QWidget(MainWindow)
        self.centralWidget.setObjectName("centralWidget")
        font = QtGui.QFont()
        font.setPointSize(12)
        self.regioName = QtWidgets.QLabel(self.centralWidget)
        self.regioName.setGeometry(QtCore.QRect(10, 10, 370, 50))
        self.regioName.setFont(font)
        self.regioName.setObjectName("label_region")
        self.regioName.setText("Данные не загружены!")
        self.regioName.setAlignment(QtCore.Qt.AlignCenter)
        self.progressBar = QtWidgets.QProgressBar(self.centralWidget)
        self.progressBar.setGeometry(QtCore.QRect(150, 740, 1040, 20))
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setMaximum(100000)
        self.progressBar.setTextVisible(False)
        self.progressLabel = QtWidgets.QLabel(self.centralWidget)
        self.progressLabel.setGeometry(QtCore.QRect(0, 740, 150, 20))
        self.progressLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.mapView = QtWebEngineWidgets.QWebEngineView(self.centralWidget)
        self.mapView.setGeometry(QtCore.QRect(390, 10, 800, 720))
        self.mapView.setUrl(QtCore.QUrl("about:blank"))
        self.mapView.setObjectName("mapView")
        self.groupBox = QtWidgets.QGroupBox(self.centralWidget)
        self.groupBox.setGeometry(QtCore.QRect(10, 60, 370, 131))
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setEnabled(False)
        self.groupBox.setToolTip('Для прогнозирования необходимо обучить систему!')
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setGeometry(QtCore.QRect(10, 20, 50, 20))
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.comboBox = QtWidgets.QComboBox(self.groupBox)
        self.comboBox.setGeometry(QtCore.QRect(70, 20, 191, 20))
        self.comboBox.setFont(font)
        self.comboBox.setObjectName("comboBox")
        self.checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.checkBox.setGeometry(QtCore.QRect(10, 50, 600, 20))
        self.checkBox.setFont(font)
        self.checkBox.setObjectName("checkBox")
        self.forecastButton = QtWidgets.QPushButton(self.groupBox)
        self.forecastButton.setGeometry(QtCore.QRect(110, 100, 150, 23))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.forecastButton.setFont(font)
        self.forecastButton.setObjectName("forecastButton")
        MainWindow.setCentralWidget(self.centralWidget)
        self.menuBar = QtWidgets.QMenuBar(MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 1200, 21))
        self.menuBar.setObjectName("menuBar")
        file_menu = self.menuBar.addMenu('Данные')
        self.train_menu = self.menuBar.addMenu('Обучение системы')
        self.train_menu.setToolTipsVisible(True)
        self.actiona = file_menu.addAction('Загрузить данные')
        self.train_action = self.train_menu.addAction('Запуск')
        self.train_action.setToolTip('Для обучения системы необходимо загрузить данные')
        self.train_action.setEnabled(False)
        MainWindow.setMenuBar(self.menuBar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Прогнозирование возникновения пожаров"))
        self.groupBox.setTitle(_translate("MainWindow", "Сделать прогноз"))
        self.label_2.setText(_translate("MainWindow", "Дата:"))
        self.checkBox.setText(_translate("MainWindow", "Отобразить результат на карте"))
        self.forecastButton.setText(_translate("MainWindow", "Сделать прогноз"))
        dates_to_combobox = [(datetime.datetime.today() + relativedelta(days=1)).strftime('%d.%m.%Y'),
                             (datetime.datetime.today() + relativedelta(days=2)).strftime('%d.%m.%Y'),
                             (datetime.datetime.today() + relativedelta(days=3)).strftime('%d.%m.%Y'),
                             (datetime.datetime.today() + relativedelta(days=4)).strftime('%d.%m.%Y'),
                             (datetime.datetime.today() + relativedelta(days=5)).strftime('%d.%m.%Y')]
        self.comboBox.addItems(dates_to_combobox)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
