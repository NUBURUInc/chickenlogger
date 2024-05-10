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

import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration, ThermocoupleType, TemperatureUnits

class SignalCommunicate(QtCore.QObject):
    # https://stackoverflow.com/a/45620056
    request_graph_update = QtCore.pyqtSignal()

uiclass, baseclass = pg.Qt.loadUiType("MainWindow.ui")

class MainWindow(uiclass, baseclass):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        

        # Filling out functionality
        self.startMonitorButton.clicked.connect(self.startMonitor)
        self.stopMonitorButton.clicked.connect(self.stopMonitor)
        self.startRecordButton.clicked.connect(self.startRecord)
        self.stopRecordButton.clicked.connect(self.stopRecord)

        

        # -------------------------------- ADDED CODE --------------------------------------------- #
        
        # Parameters
        sampleinterval=0.01
        timewindow=10.
        size=(600, 350)
        self.interval = int(sampleinterval * 1000)
        self.bufsize = int(timewindow / sampleinterval)
        self.x = np.linspace(-timewindow, 0.0, self.bufsize)
        
        # Data object
        self.b0 = collections.deque([0.0] * self.bufsize, self.bufsize)
        self.b1 = collections.deque([0.0] * self.bufsize, self.bufsize)
        self.b2 = collections.deque([0.0] * self.bufsize, self.bufsize)
        self.b3 = collections.deque([0.0] * self.bufsize, self.bufsize)

        # Create signal
        # self.request_graph_update = QtCore.pyqtSignal(np.ndarray)
        # self.request_graph_update.connect(self.updatePlots, args)
        self.sig = SignalCommunicate()
        self.sig.request_graph_update.connect(self.updateGraphs)

        self.iThread = InstrumentThread(func=self.updateData)

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

    def startPlots(self):
        self.iThread = InstrumentThread(func=self.updateData)
        self.iThread.start()
        # for plot in self.plots:
        #     plot.start()
        pass

    def stopPlots(self):
        self.iThread.terminate()
        # for plot in self.plots:
        #     plot.stop()
        return None

    def startMonitor(self):
        self.startMonitorButton.setDisabled(True)
        self.stopMonitorButton.setDisabled(False)
        self.startPlots()
        return None

    def stopMonitor(self):
        self.startMonitorButton.setDisabled(False)
        self.stopMonitorButton.setDisabled(True)
        self.stopPlots()
        return None

    def startRecord(self):
        self.startRecordButton.setDisabled(True)
        self.stopRecordButton.setDisabled(False)
        return None

    def stopRecord(self):
        self.startRecordButton.setDisabled(False)
        self.stopRecordButton.setDisabled(True)
        return None

    def updateGraphs(self):
        self.pdCurve.setData(self.x, self.b0)
        self.tpCurve.setData(self.x, self.b2)
        self.tempCurvePd.setData(self.x, self.b1)
        self.tempCurveTp.setData(self.x, self.b3)
        return None

    def updateData(self, data):
        self.b0.extend(data[0])
        self.b1.extend(data[1])
        self.b2.extend(data[2])
        self.b3.extend(data[3])
        # print(ret[2])
        # print('Callback')
        # Update curve objects
        # self.pdCurve.setData(self.x, self.b0)
        # self.tpCurve.setData(self.x, self.b2)
        self.sig.request_graph_update.emit()
        
        pass


class InstrumentThread(threading.Thread):
# class InstrumentThread(QtCore.QThread):
    def __init__(self, func):
        
        self.func = func

        # Thread object
        self._running_flag = False
        self.stop = threading.Event()
        super().__init__(target=self.record)

        # super().__init__()
        # self.started.connect(self.record)

        self.daemon = True

        # Set channels
        self.setChans()

        # QTimer
        self.timer = QtCore.QTimer()

        return

    def terminate(self):
        self.stop.set()

    def setChans(self, chan='Dev4', pdChan='ai1', thermoChan='ai3', pdTempChan='ai0', thermoTempChan='ai4'):
        # Save daq channel settings
        self.chan = chan
        self.pdChan = pdChan
        self.thermoChan = thermoChan
        self.pdTempChan = pdTempChan
        self.thermoTempChan = thermoTempChan
        return None

    def record(self):
        """ Method to start data collection """
        self.stop.clear()

        self.sper = 10 # sample period
        self.sampleFreq = 2000

        # Collect data
        with nidaqmx.Task() as task:

            task.ai_channels.add_ai_voltage_chan('/'.join([self.chan, self.pdChan]), terminal_config=TerminalConfiguration.DIFF)
            # task.ai_channels.add_ai_voltage_chan('/'.join([self.chan, self.pdTempChan]), terminal_config=TerminalConfiguration.DIFF)
            task.ai_channels.add_ai_thrmcpl_chan('/'.join([self.chan, self.pdTempChan]), units=TemperatureUnits.DEG_C, thermocouple_type=ThermocoupleType.J)

            task.ai_channels.add_ai_voltage_chan('/'.join([self.chan, self.thermoChan]), terminal_config=TerminalConfiguration.DIFF)
            # task.ai_channels.add_ai_voltage_chan('/'.join([self.chan, self.thermoTempChan]), terminal_config=TerminalConfiguration.DIFF)
            task.ai_channels.add_ai_thrmcpl_chan('/'.join([self.chan, self.thermoTempChan]), units=TemperatureUnits.DEG_C, thermocouple_type=ThermocoupleType.J)

            task.timing.cfg_samp_clk_timing(self.sampleFreq, sample_mode=AcquisitionType.CONTINUOUS)

            def callback(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
                """Callback function for reading singals."""
                ret = task.read(number_of_samples_per_channel=self.sper)
                
                self.func(ret)
                # Do the thing

                return 0

            task.register_every_n_samples_acquired_into_buffer_event(self.sper, callback)
            task.start()
            
            while self.stop.is_set() == False:
                self.stop.wait(100)
            # print('Stopped')

        return None

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()