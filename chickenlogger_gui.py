import sys
# from PySide6.QtWidgets import QApplication
from PyQt5.QtWidgets import QApplication
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import collections
import numpy as np
import math
import random
import time
import threading
import yamlParser as yp

import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration, ThermocoupleType, TemperatureUnits

class SignalCommunicate(QtCore.QObject):
    # https://stackoverflow.com/a/45620056
    request_graph_update = QtCore.pyqtSignal()

uiclass, baseclass = pg.Qt.loadUiType("MainWindow.ui")

class Cfg():
    def __init__(self):
        pass

class MainWindow(uiclass, baseclass):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Create config file object
        self.conf = yp.Cfg()

        # Filling out functionality
        self.startMonitorButton.clicked.connect(self.startMonitor)
        self.stopMonitorButton.clicked.connect(self.stopMonitor)
        self.startRecordButton.clicked.connect(self.startRecord)
        self.stopRecordButton.clicked.connect(self.stopRecord)
        
        # Load and save buttons
        self.saveButton.clicked.connect(self.saveSettings)
        self.loadButton.clicked.connect(self.loadSettings)

        # Line edits
        local_system = nidaqmx.system.System.local()
        for device in local_system.devices:
            self.devCombo.addItem(device.name)

        # self.devBox.setValidator(QtGui.QIntValidator())
        # self.tpChan.setValidator(QtGui.QIntValidator())
        # self.tpTChan.setValidator(QtGui.QIntValidator())
        # self.pdChan.setValidator(QtGui.QIntValidator())
        # self.pdTChan.setValidator(QtGui.QIntValidator())
        # self.binEntry.setValidator(QtGui.QIntValidator())
        # self.freqEntry.setValidator(QtGui.QIntValidator())
        # self.wSizeEntry.setValidator(QtGui.QIntValidator())
        # self.savePerEntry.setValidator(QtGui.QIntValidator())
        # self.avgDD.currentText()
        # self.saveLocEntry.setValidator(QtGui.QIntValidator())

        # Parameters
        sampleinterval=1/2000 # 0.01
        timewindow=1.
        self.interval = int(sampleinterval * 1000)
        self.bufsize = int(timewindow / sampleinterval)
        self.x = np.linspace(-timewindow, 0.0, self.bufsize)
        
        # Data object
        self.b0 = collections.deque([0.0] * self.bufsize, self.bufsize)
        self.b1 = collections.deque([0.0] * self.bufsize, self.bufsize)
        self.b2 = collections.deque([0.0] * self.bufsize, self.bufsize)
        self.b3 = collections.deque([0.0] * self.bufsize, self.bufsize)

        # Create signal
        self.sig = SignalCommunicate()
        self.sig.request_graph_update.connect(self.updateGraphs)

        # Create thread
        self.getSettings()
        self.iThread = InstrumentThread(func=self.updateData, settings=self.settings1)

        self.__formatPlots()

        self.avgDD.addItem('True')
        self.avgDD.addItem('False')

        self.saving = False
        self.monit = False
        self.stime = time.time()

        return

    def __formatPlots(self):
        """ Format plots for __init__() """
        size=(600, 350)
        
        # PyQtGraph photodiode plot
        self.photodiodeGraph.setTitle("Photodiode Data")
        self.photodiodeGraph.resize(*size)
        self.photodiodeGraph.showGrid(x=True, y=True)
        self.photodiodeGraph.setLabel('left', 'Sensor', 'V')
        self.photodiodeGraph.setLabel('bottom', 'Time', 's')
        self.pdCurve = self.photodiodeGraph.plot(self.x, self.b0, pen=(255, 0, 0))

        # PyQtGraph thermopile plot
        self.thermopileGraph.setTitle("Thermopile Data")
        self.thermopileGraph.resize(*size)
        self.thermopileGraph.showGrid(x=True, y=True)
        self.thermopileGraph.setLabel('left', 'Sensor', 'V')
        self.thermopileGraph.setLabel('bottom', 'Time', 's')
        self.tpCurve = self.thermopileGraph.plot(self.x, self.b2, pen=(255, 0, 0))

        # Temperature plots
        self.tempGraph.setTitle("Thermocouple Data")
        self.tempGraph.resize(*size)
        self.tempGraph.showGrid(x=True, y=True)
        self.tempGraph.setLabel('left', 'Thermocouple', 'V')
        self.tempGraph.setLabel('bottom', 'Time', 's')
        self.tempCurvePd = self.tempGraph.plot(self.x, self.b1, pen=(255, 0, 0))
        self.tempCurveTp = self.tempGraph.plot(self.x, self.b3, pen=(255, 0, 0))
        return None

    def startPlots(self):
        """ Start the measurement and live plotting """
        self.getSettings()
        self.iThread = InstrumentThread(func=self.updateData, settings = self.settings1)
        self.iThread.start()
        return None

    def stopPlots(self):
        """ Stop the measurement and live plotting """
        self.iThread.terminate()
        return None

    def startMonitor(self):
        """ Start monitor button action """
        self.startMonitorButton.setDisabled(True)
        self.stopMonitorButton.setDisabled(False)
        self.monit = True
        self.startPlots()
        return None

    def stopMonitor(self):
        """ Stop monitor button action """
        self.startMonitorButton.setDisabled(False)
        self.stopMonitorButton.setDisabled(True)
        if self.saving == True:
            self.stopRecord()
        self.monit = False
        self.stopPlots()
        return None

    def startRecord(self):
        """ Start record button action """
        self.startRecordButton.setDisabled(True)
        self.stopRecordButton.setDisabled(False)
        if self.monit == False:
            self.startMonitor()

        # Get settings
        self.savePer = int(self.savePerEntry.text())
        self.saveName = '/'.join([self.saveLocEntry.text(),'save_data.csv'])

        self.saving = True
        return None

    def stopRecord(self):
        """ Stop record button action """
        self.startRecordButton.setDisabled(False)
        self.stopRecordButton.setDisabled(True)
        self.saving = False
        return None

    def updateGraphs(self):
        """ Update the plots in the live gui """
        self.pdCurve.setData(self.x, self.b0)
        self.tpCurve.setData(self.x, self.b2)
        self.tempCurvePd.setData(self.x, self.b1)
        self.tempCurveTp.setData(self.x, self.b3)
        return None

    def updateData(self, data):
        """ Update the data from the lastest measurement """
        self.b0.extend(data[0])
        self.b1.extend(data[1])
        self.b2.extend(data[2])
        self.b3.extend(data[3])
        
        if self.saving:
            ctime = time.time()
            if self.savePer < (ctime - self.stime):
                self.stime = ctime
                with open(self.saveName, 'a') as file1:
                    linea = [str(ctime), str(self.b0[-1]), str(self.b1[-1]), str(self.b2[-1]), str(self.b3[-1])]
                    line = ','.join(linea) + '\n'
                    file1.write(line)
                
        # Emit a signal
        self.sig.request_graph_update.emit()
        return None
    
    def loadSettings(self):
        """ Load settings from config file """
        self.conf.loadCfg()

        # Load address
        index = self.devCombo.findText(self.conf.dAddr)
        if index != -1:
            self.devCombo.setCurrentIndex(index)

        self.tpChan.clear()
        self.tpChan.insert(self.conf.tpChan)

        self.tpTChan.clear()
        self.tpTChan.insert(self.conf.tpTChan)

        self.pdChan.clear()
        self.pdChan.insert(self.conf.pdChan)

        self.pdTChan.clear()
        self.pdTChan.insert(self.conf.pdTChan)

        self.binEntry.clear()
        self.binEntry.insert(self.conf.binSize)

        self.freqEntry.clear()
        self.freqEntry.insert(self.conf.sampFreq)

        self.wSizeEntry.clear()
        self.wSizeEntry.insert(self.conf.pWindow)

        self.savePerEntry.clear()
        self.savePerEntry.insert(self.conf.sPeroid)
        
        # w2 = self.avgDD.currentText()
        index = self.avgDD.findText(self.conf.sAvg)
        if index != -1:
            self.avgDD.setCurrentIndex(index)
        
        self.saveLocEntry.clear()
        self.saveLocEntry.insert(self.conf.sLoc)

        pass

    def saveSettings(self):
        """ Save settings in text boxes """
        self.conf.saveCfg()
        pass

    def getSettings(self):
        """ Get settings from text boxes """
        s1 = self.devCombo.currentText()
        s2 = self.tpChan.text()
        s3 = self.tpTChan.text()
        s4 = self.pdChan.text()
        s5 = self.pdTChan.text()

        v1 = int(self.binEntry.text())
        v2 = int(self.freqEntry.text())
        v3 = self.wSizeEntry.text()

        w1 = self.savePerEntry.text()
        w2 = self.avgDD.currentText()
        w3 = self.saveLocEntry.text()

        self.settings = [s1, s2, s3, s4, s5, v1, v2, v3, w1, w2, w3]
        self.settings1 = [s1, s2, s3, s4, s5, v1, v2]

        # print(settings)

        return None


class InstrumentThread(threading.Thread):
    def __init__(self, func, settings):
        # Function that needs to be called from the class above.
        self.func = func

        # Thread object
        self._running_flag = False
        self.stop = threading.Event()
        
        # Create a thread object
        super().__init__(target=self.record)
        self.daemon = True

        self.chan = settings[0]
        self.pdChan = settings[3]
        self.thermoChan = settings[1]
        self.pdTempChan = settings[4]
        self.thermoTempChan = settings[2]
        self.sper = settings[5]
        self.sampleFreq = settings[6]

        # Set channels
        # self.setChans()

        return

    def terminate(self):
        ''' Set stop event '''
        self.stop.set()
        return None

    def setChans(self, chan='Dev4', pdChan='ai1', thermoChan='ai3', pdTempChan='ai0', thermoTempChan='ai4', sper=10, sampleFreq=2000):
        '''
        Inputs
            - chan
            - pdChan
            - thermoChan
            - pdTempChan
            - thermoTempChan
            - sper
            - sampleFreq
        '''
        # Save daq channel settings
        self.chan = chan
        self.pdChan = pdChan
        self.thermoChan = thermoChan
        self.pdTempChan = pdTempChan
        self.thermoTempChan = thermoTempChan
        self.sper = sper
        self.sampleFreq = sampleFreq
        return None

    def record(self):
        """ Method to start data collection """
        self.stop.clear()
        self.sper = 10 # sample period
        self.sampleFreq = 2000

        # Collect data
        with nidaqmx.Task() as task:
            # Create tasks
            task.ai_channels.add_ai_voltage_chan('/'.join([self.chan, self.pdChan]), terminal_config=TerminalConfiguration.DIFF)
            # task.ai_channels.add_ai_voltage_chan('/'.join([self.chan, self.pdTempChan]), terminal_config=TerminalConfiguration.DIFF)
            task.ai_channels.add_ai_thrmcpl_chan('/'.join([self.chan, self.pdTempChan]), units=TemperatureUnits.DEG_C, thermocouple_type=ThermocoupleType.J)
            task.ai_channels.add_ai_voltage_chan('/'.join([self.chan, self.thermoChan]), terminal_config=TerminalConfiguration.DIFF)
            # task.ai_channels.add_ai_voltage_chan('/'.join([self.chan, self.thermoTempChan]), terminal_config=TerminalConfiguration.DIFF)
            task.ai_channels.add_ai_thrmcpl_chan('/'.join([self.chan, self.thermoTempChan]), units=TemperatureUnits.DEG_C, thermocouple_type=ThermocoupleType.J)

            # Set task timing
            task.timing.cfg_samp_clk_timing(self.sampleFreq, sample_mode=AcquisitionType.CONTINUOUS)

            def callback(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
                """Callback function for reading singals."""
                ret = task.read(number_of_samples_per_channel=self.sper)    
                self.func(ret)
                return 0

            task.register_every_n_samples_acquired_into_buffer_event(self.sper, callback)
            task.start()
            
            while self.stop.is_set() == False:
                self.stop.wait(100)

        return None

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()