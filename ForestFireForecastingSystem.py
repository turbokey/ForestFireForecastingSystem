from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
from shutil import copy
import pickle
import sys
import folium
import warnings
import os
import errno
import keras
import json
import sqlite3
import numpy as np
import matplotlib as mpl
from scipy.interpolate import griddata
from dateutil.relativedelta import relativedelta
import mainwindow
import requests
import datetime
from requests.exceptions import HTTPError
import re
from bs4 import BeautifulSoup

warnings.simplefilter(action='ignore', category=Warning)
from pyproj import Proj, datadir, _datadir

inProj = Proj(init='epsg:3857')
outProj = Proj(init='epsg:4326')

def month_switch(argument):
    switcher = {
        "января": "01",
        "февраля": "02",
        "марта": "03",
        "апреля": "04",
        "мая": "05",
        "июня": "06",
        "июля": "07",
        "августа": "08",
        "сентября": "09",
        "октября": "10",
        "ноября": "11",
        "декабря": "12"
    }
    return switcher[argument]

def loadDataFromDatabase(path):
    data = {}
    data["map"] = {}
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("SELECT * FROM map")
    map = c.fetchall()
    for t in map:
        try:
            data["map"][t[0]][int(t[1]), int(t[2])] = {}
        except KeyError:
            data["map"][t[0]] = {}
            data["map"][t[0]][int(t[1]), int(t[2])] = {}
        data["map"][t[0]][int(t[1]), int(t[2])]['max_temp'] = float(t[3])
        data["map"][t[0]][int(t[1]), int(t[2])]['humidity'] = float(t[4])
        data["map"][t[0]][int(t[1]), int(t[2])]['days_without_rain'] = float(t[5])
        data["map"][t[0]][int(t[1]), int(t[2])]['population_density'] = float(t[6])
        data["map"][t[0]][int(t[1]), int(t[2])]['fires_count'] = int(t[7])
    c.execute("SELECT * FROM train_data")
    train_data = c.fetchall()
    data['train_data'] = {}
    train_x = []
    train_y = []
    for t in train_data:
        els = (t[1]).split(',')
        train_x.append(
            [float(els[0]), float(els[1]), float(els[2]), float(els[3]), float(els[4]), float(els[5]),
             int(els[6])])
        train_y.append(int(t[2]))
    data['train_data']['x_train'] = train_x[:10000]
    data['train_data']['y_train'] = train_y[:10000]
    data['train_data']['x_test'] = train_x[10000:]
    data['train_data']['y_test'] = train_y[10000:]
    c.execute("SELECT * FROM grid")
    grid = c.fetchall()
    data['grid'] = {}
    for t in grid:
        data['grid']['geojson'] = json.loads(t[0])
        data['contour'] = json.loads(t[1])
        data['grid']['VERTICAL_CELLS'] = int(t[2])
        data['grid']['HORIZONTAL_CELLS'] = int(t[3])
        data['grid']['LOWER_LEFT_CORNER'] = [float(t[4].split(' ')[0]), float(t[4].split(' ')[1])]
        data['grid']['UPPER_RIGHT_CORNER'] = [float(t[5].split(' ')[0]), float(t[5].split(' ')[1])]
    c.execute("SELECT * FROM additional_info")
    additional_info = c.fetchall()
    for t in additional_info:
        crds = (t[0]).split(',')
        data['start'] = [float(crds[0]), float(crds[1])]
        data['name'] = [str(t[1])]
    c.execute("SELECT * FROM station_info")
    station_numbers = c.fetchall()
    station_numbers_list = {}
    for t in station_numbers:
        station_numbers_list[str(t[0])] = {"row": int(t[1]), "col": int(t[2]), "link": str(t[3]), "link_archive": str(t[4])}
    data['station_info'] = station_numbers_list
    c.execute("SELECT * FROM region_grids")
    region_grids = c.fetchall()
    data['region_grids'] = []
    for t in region_grids:
        data['region_grids'].append((int(t[0]), int(t[1])))
    return data

def get_fires_count(fire_date, fire_row, fire_column, dictionary):
    try:
        return len(dictionary[fire_date][fire_row, fire_column])
    except KeyError:
        return 0

class Applcation(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        super(Applcation, self).__init__(parent)
        self.data = {}
        self.setupUi(self)
        self.actiona.triggered.connect(self.loadData)
        self.train_action.triggered.connect(self.startTraining)
        self.forecastButton.clicked.connect(self.startForecasting)
        self.threadclass = MainThread()
        self.readfilethread = ReadFileThread()
        self.train_thread = TrainThread()
        self.visualize_map_thread = VisualizeMapThread({})
        self.threadclass.start()
        self.threadclass.update_mapsignal.connect(self.updateMap)
        self.threadclass.update_progressbar.connect(self.updateProgressBar)
        self.threadclass.update_progresslabel.connect(self.setProgressLabelText)
        self.threadclass.longtask_finished.connect(self.longTaskFinished)
        self.threadclass.pass_data.connect(self.passData)
        self.threadclass.change_predict_block_enable.connect(self.changePredictBlockEnable)
        self.readfilethread.update_progressbar.connect(self.updateProgressBar)
        self.readfilethread.update_progresslabel.connect(self.setProgressLabelText)
        self.readfilethread.pass_data.connect(self.passData)

    def updateProgressBar(self, value):
        self.progressBar.setValue(self.progressBar.value() + value)

    def updateMap(self, map):
        self.mapView.load(QtCore.QUrl.fromLocalFile(os.path.abspath(os.path.join(os.path.dirname(__file__), map))))
        self.mapView.show()

    def setProgressLabelText(self, text):
        self.progressLabel.setText(text)

    def onChanged(self):
        print('')

    def loadData(self):
        self.readfilethread.start()

    def longTaskFinished(self):
        self.progressBar.setValue(0)
        self.progressLabel.setText('Готово')

    def startTraining(self):
        self.train_thread = TrainThread()
        self.train_thread.update_progressbar.connect(self.updateProgressBar)
        self.train_thread.update_progresslabel.connect(self.setProgressLabelText)
        self.train_thread.longtask_finished.connect(self.longTaskFinished)
        self.train_thread.change_predict_block_enable.connect(self.changePredictBlockEnable)
        self.train_thread.start()

    def passData(self, data):
        self.train_action.setEnabled(True)
        self.regioName.setText(data['name'][0])

        self.visualize_map_thread = VisualizeMapThread(data)
        self.visualize_map_thread.update_progressbar.connect(self.updateProgressBar)
        self.visualize_map_thread.update_progresslabel.connect(self.setProgressLabelText)
        self.visualize_map_thread.longtask_finished.connect(self.longTaskFinished)
        self.visualize_map_thread.update_mapsignal.connect(self.updateMap)
        self.visualize_map_thread.start()

    def changePredictBlockEnable(self, b):
        self.groupBox.setEnabled(b)

    def startForecasting(self):
        self.forecasting_thread = ForecastingThread(self.comboBox.currentText())
        self.forecasting_thread.update_progressbar.connect(self.updateProgressBar)
        self.forecasting_thread.update_progresslabel.connect(self.setProgressLabelText)
        self.forecasting_thread.longtask_finished.connect(self.longTaskFinished)
        self.forecasting_thread.pass_data.connect(self.passData)
        self.forecasting_thread.start()


class MainThread(QtCore.QThread):
    update_mapsignal = pyqtSignal(str)
    update_progressbar = pyqtSignal(float)
    update_progresslabel = pyqtSignal(str)
    longtask_finished = pyqtSignal()
    pass_data = pyqtSignal(object)
    change_predict_block_enable = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(MainThread, self).__init__(parent)
    def run(self):

        if not os.path.exists('./data/'):
            try:
                os.makedirs(os.path.dirname('./data/'))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        if not os.path.exists('./maps/'):
            try:
                os.makedirs(os.path.dirname('./maps/'))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        datafiles = [f for f in os.listdir('./data/') if os.path.isfile(os.path.join('./data/', f))]

        if os.path.exists('.properties'):
            with open('.properties', 'r') as f:
                regionname = f.read()
            if regionname in datafiles:
                self.update_progresslabel.emit("Загрузка")
                self.update_progressbar.emit(32000)
                try:
                    data = loadDataFromDatabase('./data/' + regionname)
                except:
                    self.longtask_finished.emit()
                    return
                self.pass_data.emit(data)

            if 'model.h5' in datafiles:
                self.change_predict_block_enable.emit(True)

        map = folium.Map(location=[60, 90], max_bounds=True, zoom_start=3, max_zoom=3, zoom_control=False,
                         scrollWheelZoom=False, dragging=False)
        map.save('./maps/map.html')
        self.update_mapsignal.emit('./maps/map.html')


class ReadFileThread(QtCore.QThread):
    update_progressbar = pyqtSignal(float)
    update_progresslabel = pyqtSignal(str)
    pass_data = pyqtSignal(object)

    def __init__(self, parent=None):
        super(ReadFileThread, self).__init__(parent)

    def run(self):
        filter = "SQLite3 (*.sqlite)"
        filename = QFileDialog.getOpenFileName(QFileDialog(), 'Открытие файла', '.', filter)
        database_path = filename[0]
        self.update_progressbar.emit(2000)
        self.update_progresslabel.emit("Загрузка")

        try:
            data = loadDataFromDatabase(database_path)
        except:
            self.longtask_finished.emit()
            return

        self.update_progressbar.emit(15000)
        path = './data/' + data['name'][0]

        self.update_progresslabel.emit("Копирование")
        copy(database_path, path)

        with open('.properties', 'w') as f:
            f.write(data['name'][0])

        self.update_progressbar.emit(15000)
        self.pass_data.emit(data)


class TrainThread(QtCore.QThread):
    update_progressbar = pyqtSignal(float)
    update_progresslabel = pyqtSignal(str)
    longtask_finished = pyqtSignal()
    change_predict_block_enable = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(TrainThread, self).__init__(parent)

    def run(self):
        with open('.properties', 'r') as f:
            regionname = f.read()

        try:
            data = loadDataFromDatabase('./data/' + regionname)
        except:
            self.longtask_finished.emit()
            return

        x_train = np.array(data['train_data']['x_train']).reshape(-1, 7)
        y_train = np.array(data['train_data']['y_train']).reshape(-1, 1)
        x_test = np.array(data['train_data']['x_test']).reshape(-1, 7)
        y_test = np.array(data['train_data']['y_test']).reshape(-1, 1)

        import keras.backend.tensorflow_backend as tb
        tb._SYMBOLIC_SCOPE.value = True

        model = keras.Sequential()
        model.add(keras.layers.Dense(9, input_dim=7, activation='sigmoid'))
        model.add(keras.layers.Dense(1, activation='sigmoid'))
        model.summary()
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        epochs = 3
        total = epochs*x_train.shape[0]
        self.update_progresslabel.emit('Обучение...')
        for e in range(epochs):
            for i in range(x_train.shape[0]):
                model.fit(x_train[i:i+1], y_train[i], nb_epoch=1, batch_size=100, verbose=0)
                self.update_progressbar.emit(100000 / total)

        self.update_progresslabel.emit('Оценка...')

        model.save("./data/model.h5")

        self.change_predict_block_enable.emit(True)
        self.longtask_finished.emit()

class VisualizeMapThread(QtCore.QThread):
    update_progressbar = pyqtSignal(float)
    update_progresslabel = pyqtSignal(str)
    longtask_finished = pyqtSignal()
    update_mapsignal = pyqtSignal(str)

    def __init__(self, data, parent=None):
        super(VisualizeMapThread, self).__init__(parent)
        self.data = data

    def run(self):
        try:
            progressBarStep = 68 * 1000 / (self.data['grid']['VERTICAL_CELLS'] * self.data['grid']['HORIZONTAL_CELLS'])
            self.update_progresslabel.emit("Построение сети")
            grid = self.data['grid']['geojson']

            map = folium.Map(location=self.data['start'], max_bounds=True, zoom_start=6, max_zoom=6, zoom_control=False,
                         scrollWheelZoom=False)

            map.add_child(folium.GeoJson(data=self.data['contour'],
                                     style_function=lambda x: {'color': 'black', 'fillColor': 'transparent'}))

            self.update_progresslabel.emit("Картрирование")

            pokazetel = "prediction"

            # max_temp = -1000.0
            # for k in self.data['map'].keys():
            #     if (self.data['map'][k][pokazetel] > max_temp):
            #         max_temp = self.data['map'][k][pokazetel]

            for i, geo_json in enumerate(grid):
                self.update_progressbar.emit(progressBarStep)
                i_to_row = (self.data['grid']['VERTICAL_CELLS'] - 1) - i % self.data['grid']['VERTICAL_CELLS']
                i_to_column = i // self.data['grid']['VERTICAL_CELLS']

                v = self.data['map'][i_to_row, i_to_column][pokazetel]
                if v < 0.5:
                    color = mpl.colors.to_hex('#00ff00')
                elif v >=0.5 and v < 0.8:
                    color = mpl.colors.to_hex('yellow')
                elif v >=0.8 and v < 0.92:
                    color = mpl.colors.to_hex('orange')
                else:
                    color = mpl.colors.to_hex('red')
                #color = plt.cm.Reds(self.data['map'][i_to_row, i_to_column][pokazetel] / max_temp)


                border_color = 'black'
                if np.isnan(self.data['map'][i_to_row, i_to_column][pokazetel]):
                    continue

                gj = folium.GeoJson(geo_json,
                                style_function=lambda feature, color=color: {
                                    'fillColor': color,
                                    'color': border_color,
                                    'weight': 0.5,
                                    'fillOpacity': 0.75,
                                })
                popup = folium.Popup(str(i_to_row) + " " + str(i_to_column) + " " + str(
                    self.data['map'][i_to_row, i_to_column][pokazetel]))
                gj.add_child(popup)

                map.add_child(gj)

            map.save('./maps/map.html')
            self.update_mapsignal.emit('./maps/map.html')
        except: pass
        self.longtask_finished.emit()

class ForecastingThread(QtCore.QThread):
    update_progressbar = pyqtSignal(float)
    update_progresslabel = pyqtSignal(str)
    longtask_finished = pyqtSignal()
    pass_data = pyqtSignal(object)

    HEADERS = {'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Encoding': 'gzip, deflate, sdch, br',
                'Accept-Language': 'ru,en;q=0.9'
                }

    def __init__(self, date_to_forecast, parent=None):
        super(ForecastingThread, self).__init__(parent)
        self.date_to_forecast = date_to_forecast

    def run(self):
        import keras.backend.tensorflow_backend as tb
        tb._SYMBOLIC_SCOPE.value = True
        try:
            model = keras.models.load_model('./data/model.h5')
        except OSError:
            return

        model.summary()

        with open('.properties', 'r') as f:
            regionname = f.read()

        dataset = loadDataFromDatabase('./data/' + regionname)

        step = 100000 / (1174 +len(dataset['station_info'].keys()))

        forecasting_date = ''
        if os.path.exists('.temp'):
            with open('.temp', 'r') as f:
                forecasting_date = f.read()

        if forecasting_date == datetime.datetime.today().strftime('%d.%m.%Y'):
            with open('./data/data_for_forecasting.pkl', 'rb') as df:
                data_for_forecasting = pickle.load(df)
        else:
            meteo_d = {}
            fires_d = {}
            self.update_progresslabel.emit('Получение прогнозов')
            for code in dataset['station_info'].keys():
                url = 'https://rp5.ru/'+dataset['station_info'][code]['link']
                try:
                    r = requests.get(url=url,headers=self.HEADERS)
                    r.encoding = 'utf-8'
                    soup = BeautifulSoup(r.text, 'lxml')
                    forecast_table = soup.find("div", {"id": "ftab_6_content", "class": "ftab_content"})
                    table = forecast_table.find('table')
                    rows = table.find_all('tr')
                    dates = []
                    rw = dataset['station_info'][code]['row']
                    cl = dataset['station_info'][code]['col']
                    for row in rows:
                        cols = row.find_all('td')
                        colss = []
                        for ele in cols:
                            if ele.text.strip() == '' and ele.find("div",{"class": "pr_0"}):
                                try:
                                    t = re.findall("(\d+(?:\.\d+)?) мм", ele.find("div",{"class": "pr_0"})['onmouseover'])
                                    if len(t) == 0:
                                        colss.append('0.0')
                                    else:
                                        colss.append(t[0].replace(" мм",""))
                                except KeyError:
                                    colss.append('0.0')
                            else:
                                colss.append(ele.text.strip())
                        if len(colss) == 0:
                            continue
                        if colss[0] == 'День недели':
                            for i in range(1,7,1):
                                day_month = colss[i].split(',')[1].split(' ')
                                date = str("{0:0=2d}".format(int(day_month[0])))+"."+month_switch(day_month[1])+"."+str(datetime.datetime.now().year)
                                dates.append(date)
                                try:
                                    meteo_d[date][rw, cl] = {}
                                except KeyError:
                                    meteo_d[date] = {}
                                    meteo_d[date][rw, cl] = {}
                        elif colss[0] == 'Явления погоды  Явления погоды':
                            lis = [[float(colss[1]),float(colss[2]),float(colss[3]),float(colss[4])],
                               [float(colss[5]),float(colss[6]),float(colss[7]),float(colss[8]),float(colss[9]),float(colss[10]),float(colss[11]),float(colss[12])],
                               [float(colss[13]),float(colss[14]),float(colss[15]),float(colss[16]),float(colss[17]),float(colss[18]),float(colss[19]),float(colss[20])],
                               [float(colss[21]),float(colss[22]),float(colss[23]),float(colss[24]),float(colss[25]),float(colss[26]),float(colss[27]),float(colss[28])],
                               [float(colss[29]),float(colss[30]),float(colss[31]),float(colss[32]),float(colss[33]),float(colss[34]),float(colss[35]),float(colss[36])],
                               [float(colss[37]),float(colss[38]),float(colss[39]),float(colss[40]),float(colss[41]),float(colss[42]),float(colss[43]),float(colss[44])]]
                            meteo_d[dates[0]][rw, cl]["rain"] = sum(lis[0]) / 2
                            meteo_d[dates[1]][rw, cl]["rain"] = sum(lis[1]) / 2
                            meteo_d[dates[2]][rw, cl]["rain"] = sum(lis[2]) / 2
                            meteo_d[dates[3]][rw, cl]["rain"] = sum(lis[3]) / 2
                            meteo_d[dates[4]][rw, cl]["rain"] = sum(lis[4]) / 2
                            meteo_d[dates[5]][rw, cl]["rain"] = sum(lis[5]) / 2
                        elif colss[0] == 'Температура,  °C °F':
                            lis = [[float(colss[1].split(' ')[0].replace("+","")),float(colss[2].split(' ')[0].replace("+",""))],
                               [float(colss[3].split(' ')[0].replace("+","")),float(colss[4].split(' ')[0].replace("+","")),float(colss[5].split(' ')[0].replace("+","")),float(colss[6].split(' ')[0].replace("+",""))],
                               [float(colss[7].split(' ')[0].replace("+","")),float(colss[8].split(' ')[0].replace("+","")),float(colss[9].split(' ')[0].replace("+","")),float(colss[10].split(' ')[0].replace("+",""))],
                               [float(colss[11].split(' ')[0].replace("+","")),float(colss[12].split(' ')[0].replace("+","")),float(colss[13].split(' ')[0].replace("+","")),float(colss[14].split(' ')[0].replace("+",""))],
                               [float(colss[15].split(' ')[0].replace("+","")),float(colss[16].split(' ')[0].replace("+","")),float(colss[17].split(' ')[0].replace("+","")),float(colss[18].split(' ')[0].replace("+",""))],
                               [float(colss[19].split(' ')[0].replace("+","")),float(colss[20].split(' ')[0].replace("+","")),float(colss[21].split(' ')[0].replace("+","")),float(colss[22].split(' ')[0].replace("+",""))]]
                            meteo_d[dates[0]][rw, cl]["max_temp"] = max(lis[0])
                            meteo_d[dates[1]][rw, cl]["max_temp"] = max(lis[1])
                            meteo_d[dates[2]][rw, cl]["max_temp"] = max(lis[2])
                            meteo_d[dates[3]][rw, cl]["max_temp"] = max(lis[3])
                            meteo_d[dates[4]][rw, cl]["max_temp"] = max(lis[4])
                            meteo_d[dates[5]][rw, cl]["max_temp"] = max(lis[5])
                        elif colss[0] == 'Влажность, %':
                            lis = [[float(colss[1]),float(colss[2])],
                               [float(colss[3]),float(colss[4]),float(colss[5]),float(colss[6])],
                               [float(colss[7]), float(colss[8]), float(colss[9]), float(colss[10])],
                               [float(colss[11]), float(colss[12]), float(colss[13]), float(colss[14])],
                               [float(colss[15]), float(colss[16]), float(colss[17]), float(colss[18])],
                               [float(colss[19]), float(colss[20]), float(colss[21]), float(colss[22])]]
                            meteo_d[dates[0]][rw, cl]["hum"] = sum(lis[0]) / len(lis[0])
                            meteo_d[dates[1]][rw, cl]["hum"] = sum(lis[1]) / len(lis[1])
                            meteo_d[dates[2]][rw, cl]["hum"] = sum(lis[2]) / len(lis[2])
                            meteo_d[dates[3]][rw, cl]["hum"] = sum(lis[3]) / len(lis[3])
                            meteo_d[dates[4]][rw, cl]["hum"] = sum(lis[4]) / len(lis[4])
                            meteo_d[dates[5]][rw, cl]["hum"] = sum(lis[5]) / len(lis[5])
                    hh = {'Accept': 'text/html, application/xhtml+xml, */*',
                        'Referer': 'https://rp5.ru/',
                        'Accept-Language': 'ru-RU',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept-Encoding': 'gzip, deflate',
                        'Host': 'rp5.ru',
                        'DNT': '1',
                        'Connection': 'close',
                        'Cache-Control': 'no-cache'
                    }
                    p_r = requests.post('https://rp5.ru/' + dataset['station_info'][code]['link_archive'],headers=hh,data={'ArchDate':dates[0],'pe':30,'lang':'ru','time_zone_add':9})
                    p_r.encoding = 'utf-8'
                    soup = BeautifulSoup(p_r.text, 'lxml')
                    table = soup.find('table', attrs={'id': 'archiveTable'})
                    rows = table.find_all('tr')
                    temps = []
                    hums = []
                    rains = []
                    cur_date = ''
                    for row in rows:
                        cols = row.find_all('td')
                        cols = [ele.text.strip() for ele in cols]
                        if len(cols[0]) > 2 and cols[0] != 'Дата / Местное время':
                            if (cur_date != ''):
                                try:
                                    meteo_d[cur_date][rw, cl] = {"max_temp": max(temps), "hum":sum(hums)/len(hums), "rain":sum(rains)}
                                except KeyError:
                                    meteo_d[cur_date] = {}
                                    meteo_d[cur_date][rw, cl] = {"max_temp": max(temps), "hum": sum(hums) / len(hums),
                                                             "rain": sum(rains)}
                            raw = re.sub('[0-9]{4}г\.', '', cols[0].split(",")[0]).split('\xa0')
                            cur_date = str("{0:0=2d}".format(int(raw[0])))+"."+month_switch(raw[1])+"."+str(datetime.datetime.now().year)
                            temps = []
                            hums = []
                            rains = []
                            if (cols[2] != ''):
                                temps.append(float(cols[2].split(' ')[0]))
                            if (cols[6] != ''):
                                hums.append(float(cols[6]))
                            if cols[24].split(' ')[0] != 'Осадков' and cols[
                                24].split(' ')[0] != 'Следы' and cols[
                                24].split(' ')[0] != '':
                                rains.append(float(cols[24].split(' ')[0]))
                        elif cols[0] == 'Дата / Местное время':
                            continue
                        elif len(cols[0]) == 2:
                            if (cols[1] != ''):
                                temps.append(float(cols[1].split(' ')[0]))
                            if (cols[5] != ''):
                                hums.append(float(cols[5]))
                            if cols[23].split(' ')[0] != 'Осадков' and cols[23].split(' ')[0] != 'Следы' and cols[23].split(' ')[0] != '':
                                rains.append(float(cols[23].split(' ')[0]))
                except requests.ConnectionError as e:
                    print(" Failed to open url")
                self.update_progressbar.emit(step)

            today_str = datetime.datetime.today().strftime('%d.%m.%Y')
            today_date = datetime.datetime.strptime(today_str, '%d.%m.%Y')
            control_date = datetime.datetime.strptime('02.05.2020', '%d.%m.%Y')
            begin_span = 14732 + (today_date-control_date).days
            end_span = begin_span - 1095

            URL = "https://maps.kosmosnimki.ru/TileSender.ashx"
            HEADERS = {'Accept': '*/*',
                   'Referer': 'https://fires.ru/',
                   'Accept-Language': 'ru-RU',
                   'Origin': 'https://fires.ru',
                   'Accept-Encoding': 'gzip, deflate',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
                   'Connection': 'Keep-Alive',
                   'DNT': '1',
                   'Cache-Control': 'no-cache'}

            self.update_progresslabel.emit('Получение пожаров')
            for i in range(begin_span, end_span, -1):
                PARAMS = {'WrapStyle': 'None',
                      'key': '',
                      'ModeKey': 'tile',
                      'ftc': 'osm',
                      'r': 'j',
                      'LayerName': 'E58063D97D534BB4BBDFF07FE5CB17F2',
                      'z': '1',
                      'x': '1',
                      'y': '0',
                      'srs': '3857',
                      'Level': '1',
                      'Span': i,
                      'sw': '1'}

                print('span #' + str(i))

                try:
                    response = requests.get(url=URL, params=PARAMS, headers=HEADERS)
                    response.raise_for_status()
                    json_body = json.loads(response.text.replace('gmxAPI._vectorTileReceiver(', '').replace('})', '}'))
                    response.close()

                    values = json_body['values']

                    for value in values:
                        date = value[6]
                        x = value[10]['coordinates'][0]
                        y = value[10]['coordinates'][1]
                        name = value[9]
                        if dataset['grid']['UPPER_RIGHT_CORNER'][0] > x > dataset['grid']['LOWER_LEFT_CORNER'][0] and \
                            dataset['grid']['UPPER_RIGHT_CORNER'][1] > y > dataset['grid']['LOWER_LEFT_CORNER'][1]:
                            r = int((dataset['grid']['UPPER_RIGHT_CORNER'][1] - float(y)) // ((dataset['grid']['UPPER_RIGHT_CORNER'][1] - dataset['grid']['LOWER_LEFT_CORNER'][1]) / dataset['grid']['VERTICAL_CELLS']))
                            c = int((float(x) - dataset['grid']['LOWER_LEFT_CORNER'][0]) // ((dataset['grid']['UPPER_RIGHT_CORNER'][0] - dataset['grid']['LOWER_LEFT_CORNER'][0]) / dataset['grid']['HORIZONTAL_CELLS']))
                            d = str(datetime.datetime.utcfromtimestamp(date).strftime('%d.%m.%Y'))
                            try:
                                if (r, c) in fires_d[d].keys():
                                    fires_d[d][r, c].append(name)
                                else:
                                    fires_d[d][r, c] = [name]
                            except KeyError:
                                fires_d[d] = {}
                                fires_d[d][r, c] = [name]
                    print(str(datetime.datetime.utcfromtimestamp(date).strftime('%d.%m.%Y')))
                except HTTPError as http_err:
                    print(f'HTTP error occurred: {http_err}')
                except Exception as err:
                    print(f'Other error occurred: {err}')
                else:
                    print('Success!')

                print('span #' + str(i) + '(' + str((begin_span - i) * 100 / (begin_span - end_span)) + '%)')
                print()
                self.update_progressbar.emit(step)

            p_d = dataset['map'][list(dataset['map'].keys())[0]]
            raw_data = {}

            self.update_progresslabel.emit('Обработка')
            for date in meteo_d.keys():
                for i in range(dataset['grid']['VERTICAL_CELLS']):
                    for j in range(dataset['grid']['HORIZONTAL_CELLS']):
                        try:
                            meteo_list = meteo_d[date][i, j]
                        except KeyError:
                            meteo_list = {'max_temp': 'nan', 'hum': 'nan', 'rain': 'nan'}
                        mt = round(float(meteo_list['max_temp']),1)
                        hum = round(float(meteo_list['hum']),1)
                        d = round(float(meteo_list['rain']),1)
                        if (i, j) in dataset['region_grids']:
                            pop_density = float(p_d[i, j]['population_density'])
                        else:
                            pop_density = float('nan')
                        try:
                            raw_data[date][i, j] = {"max_temp": mt,
                                            "humidity": hum,
                                            "days_without_rain": d,
                                            "population_density": pop_density,
                                            "fires_count": int(get_fires_count(date, i, j, fires_d))}
                        except KeyError:
                            raw_data[date] = {}
                            raw_data[date][i, j] = {"max_temp": mt,
                                            "humidity": hum,
                                            "days_without_rain": d,
                                            "population_density": pop_density,
                                            "fires_count": int(get_fires_count(date, i, j, fires_d))}
                self.update_progressbar.emit(step)

            self.update_progresslabel.emit('Интерполяция')
            for date in meteo_d.keys():
                temp = []
                hum = []
                dney = []
                for i in range(dataset['grid']['VERTICAL_CELLS']):
                    temp.append([])
                    hum.append([])
                    dney.append([])
                    for j in range(dataset['grid']['HORIZONTAL_CELLS']):
                        temp[i].append(raw_data[date][i, j]["max_temp"])
                        hum[i].append(raw_data[date][i, j]["humidity"])
                        dney[i].append(raw_data[date][i, j]["days_without_rain"])
                temp = np.array(temp)
                hum = np.array(hum)
                dney = np.array(dney)
                x_temp, y_temp = np.indices(temp.shape)
                x_hum, y_hum = np.indices(hum.shape)
                x_dney, y_dney = np.indices(dney.shape)
                temp_interp = np.array(temp)
                temp_interp[np.isnan(temp_interp)] = griddata((x_temp[~np.isnan(temp)], y_temp[~np.isnan(temp)]), temp[~np.isnan(temp)], (x_temp[np.isnan(temp)], y_temp[np.isnan(temp)]))

                hum_interp = np.array(hum)
                hum_interp[np.isnan(hum_interp)] = griddata((x_hum[~np.isnan(hum)], y_hum[~np.isnan(hum)]),
                                                          hum[~np.isnan(hum)],
                                                          (x_hum[np.isnan(hum)], y_hum[np.isnan(hum)]))
                dney_interp = np.array(dney)
                dney_interp[np.isnan(dney_interp)] = griddata((x_dney[~np.isnan(dney)], y_dney[~np.isnan(dney)]),
                                                          dney[~np.isnan(dney)],
                                                          (x_dney[np.isnan(dney)], y_dney[np.isnan(dney)]))
                for i in range(dataset['grid']['VERTICAL_CELLS']):
                    for j in range(dataset['grid']['HORIZONTAL_CELLS']):
                        if ((i, j) in dataset['region_grids']):
                            raw_data[date][i, j]["max_temp"] = round(temp_interp[i][j], 1)
                            raw_data[date][i, j]["humidity"] = round(hum_interp[i][j], 1)
                            raw_data[date][i, j]["days_without_rain"] = round(dney_interp[i][j], 1)
                        else:
                            raw_data[date][i, j]["max_temp"] = float('nan')
                            raw_data[date][i, j]["humidity"] = float('nan')
                            raw_data[date][i, j]["days_without_rain"] = float('nan')

                self.update_progressbar.emit(step)

            data_for_forecasting = {}
            dates = []
            date_keys = meteo_d.keys()

            for d in date_keys:
                dates.append(datetime.datetime.strptime(d, '%d.%m.%Y'))

            self.update_progresslabel.emit('Обработка')
            dates.sort(reverse=True)
            for k in dates[:7]:
                new_date_year_minus_3 = k + relativedelta(years=-3)
                new_date_day_minus_1 = k + relativedelta(days=-1)
                new_date_day_minus_2 = k + relativedelta(days=-2)
                d_today = k.strftime("%d.%m.%Y")
                d_day_minus_1 = new_date_day_minus_1.strftime("%d.%m.%Y")
                d_day_minus_2 = new_date_day_minus_2.strftime("%d.%m.%Y")
                for i_j in raw_data[d_today]:
                    if not (np.isnan(raw_data[d_today][i_j]['max_temp'])):
                        try:
                            max_temp_today = raw_data[d_today][i_j]['max_temp']
                            max_temp_day_minus_1 = raw_data[d_day_minus_1][i_j]['max_temp']
                            max_temp_day_minus_2 = raw_data[d_day_minus_2][i_j]['max_temp']
                            hum = raw_data[d_today][i_j]['humidity']
                            pop_density = raw_data[d_today][i_j]['population_density']
                            day_without_rain_3mm = 0
                            temp_d = k
                            while temp_d >= dates[-1]:
                                temp_d_str = temp_d.strftime("%d.%m.%Y")
                                if raw_data[temp_d_str][i_j]['days_without_rain'] > 3:
                                    break
                                day_without_rain_3mm = day_without_rain_3mm + 1
                                temp_d = temp_d + relativedelta(days=-1)
                            temp_d = k
                            three_years_fires_sum = 0
                            while temp_d >= new_date_year_minus_3:
                                temp_d_str = temp_d.strftime("%d.%m.%Y")
                                try:
                                    three_years_fires_sum = three_years_fires_sum + len(fires_d[temp_d_str][i_j])
                                except: pass
                                temp_d = temp_d + relativedelta(days=-1)
                            try:
                                data_for_forecasting[d_today][i_j]=[max_temp_today,
                                    max_temp_day_minus_1,
                                    max_temp_day_minus_2,
                                    hum,
                                    pop_density,
                                    day_without_rain_3mm,
                                    three_years_fires_sum]
                            except KeyError:
                                data_for_forecasting[d_today] = {}
                                data_for_forecasting[d_today][i_j] = [max_temp_today,
                                                        max_temp_day_minus_1,
                                                        max_temp_day_minus_2,
                                                        hum,
                                                        pop_density,
                                                        day_without_rain_3mm,
                                                        three_years_fires_sum]
                        except KeyError:
                            break
                self.update_progressbar.emit(step)

            f = open('./data/data_for_forecasting.pkl', 'wb')
            pickle.dump(data_for_forecasting, f)
            f.close()

            with open('.temp', 'w') as f:
                f.write(datetime.datetime.today().strftime('%d.%m.%Y'))

            self.longtask_finished.emit()

        self.update_progresslabel.emit('Прогнозирование')
        step = 100000 / (len(data_for_forecasting[self.date_to_forecast].keys()) + dataset['grid']['VERTICAL_CELLS'])
        prediction = {}
        for i_j in data_for_forecasting[self.date_to_forecast].keys():
            prediction[i_j] = model.predict(np.array(data_for_forecasting[self.date_to_forecast][i_j]).reshape(-1, 7))
            self.update_progressbar.emit(step)

        output = {}
        output['grid'] = dataset['grid']
        output['start'] = dataset['start']
        output['contour'] = dataset['contour']
        output['name'] = dataset['name']
        output['map'] = {}
        for p in prediction.keys():
            output['map'][p] = {"prediction":prediction[p][0][0]}
        for i in range(dataset['grid']['VERTICAL_CELLS']):
            for j in range(dataset['grid']['HORIZONTAL_CELLS']):
                try:
                    output['map'][i,j]
                except KeyError:
                    output['map'][i, j] = {"prediction":float('nan')}
            self.update_progressbar.emit(step)

        self.longtask_finished.emit()
        self.pass_data.emit(output)

if __name__ == '__main__':
    a = QApplication(sys.argv)
    app = Applcation()
    app.show()
    a.exec_()
