import sys
import time
import json
import socket
import threading

import numpy as np
import requests
import serial
import serial.tools.list_ports

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import deque

data_lock = threading.Lock()
APP_NAME = "IMU Calibrator"
BANNER_TITLE = "SOBAN Technologies"
VERSION = "1.0"

STM32_VALUES = {
    "AX": 0, "AY": 0, "AZ": 0,
    "GX": 0, "GY": 0, "GZ": 0
}

PHONE_VALUES = {
    "AX": 0, "AY": 0, "AZ": 0,
    "GX": 0, "GY": 0, "GZ": 0
}

CONNECTED_STM32 = False
CONNECTED_PHONE = False


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.buildWindow()

    def buildWindow(self):
        self.setWindowTitle(APP_NAME)
        self.resize(1450, 950)
        self.setMinimumSize(1200, 800)
        self.setWindowIcon(QIcon())

    def setDashboard(self, dashboard):
        self.dashboard = dashboard
        self.setCentralWidget(dashboard)


class STM32Manager(QObject):

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.serial = None
        self.running = False
        self.dashboard.btnSTM32.clicked.connect(self.connectSTM32)

    def findSTM32(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            desc = port.description.lower()
            if "stm32" in desc or "virtual com" in desc or "cdc" in desc:
                return port.device
        return None

    def connectSTM32(self):
        if self.serial and self.serial.is_open:
            self.running = False
            try:
                self.serial.close()
            except Exception:
                pass

        port = self.findSTM32()
        if port is None:
            self.dashboard.stmStatus.setText("🔴 Not Found")
            return

        try:
            self.serial = serial.Serial(
                port,
                115200,
                timeout=0.01,
                write_timeout=0.01
            )
            self.serial.reset_input_buffer()
            self.dashboard.stmStatus.setText("🟢 Connected")
            self.dashboard.stmPort.setText(port)
            self.running = True
            threading.Thread(target=self.readLoop, daemon=True).start()
        except Exception:
            self.dashboard.stmStatus.setText("🔴 Access Denied")

    def readLoop(self):
        global STM32_VALUES

        while self.running:
            try:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode(errors="ignore").strip()

                    if not line:
                        continue

                    parts = line.split(",")
                    if len(parts) != 6:
                        continue

                    ax, ay, az, gx, gy, gz = map(float, parts)

                    with data_lock:
                        STM32_VALUES["AX"] = ax
                        STM32_VALUES["AY"] = ay
                        STM32_VALUES["AZ"] = az
                        STM32_VALUES["GX"] = gx
                        STM32_VALUES["GY"] = gy
                        STM32_VALUES["GZ"] = gz

                    sampleRate.stm += 1

            except Exception:
                pass


class GUIUpdater(QObject):

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateGUI)
        self.timer.start(100)

    # When the phone reading is close to zero, dividing by it makes tiny
    # absolute differences look like absurd percentages (e.g. 1000%+).
    # Below this reference magnitude we instead express the difference as
    # a percentage of the sensor's expected full-scale range, which stays
    # meaningful even when both readings are near zero (e.g. flat on a
    # table). Adjust these two constants to match your actual IMU's
    # configured range for the most accurate readout.
    PCT_REF_FLOOR = 0.05
    ACCEL_FULL_SCALE = 19.62   # m/s^2, assumes a +/-2g accelerometer range
    GYRO_FULL_SCALE = 4.36     # rad/s, assumes a +/-250 deg/s gyroscope range

    def updateGUI(self):
        if getattr(self.dashboard, "is_paused", False):
            return

        for axis in STM32_VALUES.keys():
            fc = STM32_VALUES[axis]
            ph = PHONE_VALUES[axis]
            diff = abs(fc - ph)

            ref = abs(ph)
            if ref > self.PCT_REF_FLOOR:
                pct = diff / ref * 100.0
            else:
                full_scale = self.ACCEL_FULL_SCALE if axis.startswith("A") else self.GYRO_FULL_SCALE
                pct = diff / full_scale * 100.0

            self.dashboard.labels[axis][0].setText(f"{fc:.3f}")
            self.dashboard.labels[axis][1].setText(f"{ph:.3f}")
            self.dashboard.labels[axis][2].setText(f"{diff:.3f}")
            self.dashboard.labels[axis][3].setText(f"{pct:.1f}%")


class PhyphoxManager(QObject):

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.running = False
        self.session = requests.Session()
        self.dashboard.btnPhone.clicked.connect(self.scanNetwork)

    def scanNetwork(self):
        self.dashboard.phoneStatus.setText("🟡 Scanning...")
        threading.Thread(target=self.scanThread, daemon=True).start()

    def scanThread(self):
        ip = self.getLocalSubnet()
        if ip is None:
            self.dashboard.phoneStatus.setText("🔴 No Network")
            return

        for i in range(1, 255):
            addr = f"{ip}.{i}"
            try:
                r = self.session.get(f"http://{addr}:8080/config", timeout=0.15)
                if r.status_code == 200:
                    self.dashboard.phoneIP.setText(addr)
                    self.dashboard.phoneStatus.setText("🟢 Connected")
                    self.url = f"http://{addr}:8080/get?accX&accY&accZ&gyrX&gyrY&gyrZ"
                    self.running = True
                    threading.Thread(target=self.readLoop, daemon=True).start()
                    return
            except Exception:
                pass
        self.dashboard.phoneStatus.setText("🔴 Not Found")

    def getLocalSubnet(self):
        try:
            ip = socket.gethostbyname(socket.gethostname())
            parts = ip.split(".")
            return ".".join(parts[:3])
        except Exception:
            return None

    def readLoop(self):
        global PHONE_VALUES
        while self.running:
            start_time = time.time()
            try:
                r = self.session.get(self.url, timeout=0.5)
                b = r.json()["buffer"]

                with data_lock:
                    PHONE_VALUES["AX"] = b["accX"]["buffer"][0]
                    PHONE_VALUES["AY"] = b["accY"]["buffer"][0]
                    PHONE_VALUES["AZ"] = b["accZ"]["buffer"][0]
                    PHONE_VALUES["GX"] = b["gyrX"]["buffer"][0]
                    PHONE_VALUES["GY"] = b["gyrY"]["buffer"][0]
                    PHONE_VALUES["GZ"] = b["gyrZ"]["buffer"][0]

                sampleRate.phone += 1
            except Exception:
                pass

            elapsed = time.time() - start_time
            sleep_time = max(0.02 - elapsed, 0)
            time.sleep(sleep_time)


class DifferenceManager(QObject):

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateStatistics)
        self.timer.start(100)

    def updateStatistics(self):
        accel = 0.0
        gyro = 0.0

        accel += abs(STM32_VALUES["AX"] - PHONE_VALUES["AX"])
        accel += abs(STM32_VALUES["AY"] - PHONE_VALUES["AY"])
        accel += abs(STM32_VALUES["AZ"] - PHONE_VALUES["AZ"])

        gyro += abs(STM32_VALUES["GX"] - PHONE_VALUES["GX"])
        gyro += abs(STM32_VALUES["GY"] - PHONE_VALUES["GY"])
        gyro += abs(STM32_VALUES["GZ"] - PHONE_VALUES["GZ"])

        accel /= 3.0
        gyro /= 3.0

        self.dashboard.accelError.setText(f"Accel Error : {accel:.3f} m/s\u00b2")
        self.dashboard.gyroError.setText(f"Gyro Error : {gyro:.4f} rad/s")

        if accel < 0.10:
            self.dashboard.calStatus.setText("🟢 Excellent Calibration")
        elif accel < 0.30:
            self.dashboard.calStatus.setText("🟡 Good Calibration")
        else:
            self.dashboard.calStatus.setText("🔴 Needs Calibration")


class SampleRate(QObject):

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.stm = 0
        self.phone = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frequencies)
        self.timer.start(1000)  # Evaluate rates every 1 second

    def update_frequencies(self):
        # Update the live UI label text
        self.dashboard.sampleRate.setText(f"STM:{self.stm}Hz   Phone:{self.phone}Hz")
        
        # Determine the maximum of the two at this instant (minimum frequency = slower rate)
        current_slower_rate = min(self.stm, self.phone) if (self.stm > 0 and self.phone > 0) else 20
        
        # Clamp between 5Hz and 60Hz to keep PyQt timers healthy and responsive
        target_hz = max(5, min(current_slower_rate, 60))
        target_interval_ms = int(1000 / target_hz)

        # Dynamically adjust processing loops to match the slower device rate
        # This prevents calculation overlap and stale comparisons
        if hasattr(self.dashboard, 'window'):
            main_win = self.dashboard.window()
            if main_win:
                # Find managers connected to QTimers and update them
                for child in main_win.children():
                    if isinstance(child, (GUIUpdater, GraphManager)):
                        child.timer.setInterval(target_interval_ms)

        # Reset counters for the next 1-second monitoring window
        self.stm = 0
        self.phone = 0


class GraphManager(QObject):

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.maxPoints = 150
        self.plotting_enabled = True

        self.stm_acc_x = deque([0] * self.maxPoints, maxlen=self.maxPoints)
        self.stm_acc_y = deque([0] * self.maxPoints, maxlen=self.maxPoints)
        self.stm_acc_z = deque([0] * self.maxPoints, maxlen=self.maxPoints)

        self.stm_gyr_x = deque([0] * self.maxPoints, maxlen=self.maxPoints)
        self.stm_gyr_y = deque([0] * self.maxPoints, maxlen=self.maxPoints)
        self.stm_gyr_z = deque([0] * self.maxPoints, maxlen=self.maxPoints)

        self.ph_acc_x = deque([0] * self.maxPoints, maxlen=self.maxPoints)
        self.ph_acc_y = deque([0] * self.maxPoints, maxlen=self.maxPoints)
        self.ph_acc_z = deque([0] * self.maxPoints, maxlen=self.maxPoints)

        self.ph_gyr_x = deque([0] * self.maxPoints, maxlen=self.maxPoints)
        self.ph_gyr_y = deque([0] * self.maxPoints, maxlen=self.maxPoints)
        self.ph_gyr_z = deque([0] * self.maxPoints, maxlen=self.maxPoints)

        # Unified single figure layout using a 2x2 grid system
        self.fig = Figure(figsize=(12, 6), constrained_layout=True)
        self.canvas = FigureCanvas(self.fig)
        
        # 2x2 grid assignments
        self.ax_stm_acc = self.fig.add_subplot(2, 2, 1)
        self.ax_ph_acc = self.fig.add_subplot(2, 2, 2)
        self.ax_stm_gyr = self.fig.add_subplot(2, 2, 3)
        self.ax_ph_gyr = self.fig.add_subplot(2, 2, 4)

        self.dashboard.graphCard.layout().removeWidget(self.dashboard.graphPlaceholder)
        self.dashboard.graphPlaceholder.deleteLater()
        self.dashboard.graphCard.layout().addWidget(self.canvas)

        self.timer = QTimer()
        self.timer.timeout.connect(self.updateGraph)
        self.timer.start(50)

        # Wire up the live-plotting toggle button. When switched off, the
        # QTimer is stopped entirely so no data is appended and no
        # matplotlib redraw work happens at all - a full bypass.
        self.dashboard.btnGraphToggle.clicked.connect(self.togglePlotting)

    def togglePlotting(self):
        self.plotting_enabled = not self.plotting_enabled

        if self.plotting_enabled:
            self.timer.start(50)
            self.dashboard.btnGraphToggle.setText("🟠  Live Plotting: ON")
            self.dashboard.btnGraphToggle.setStyleSheet(
                "QPushButton{"
                "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FFB74D, stop:1 #E65100);"
                "color:white; font-weight:600; border-radius:12px; padding:8px;"
                "}"
                "QPushButton:hover{ background:#FB8C00; }"
            )
        else:
            self.timer.stop()
            self.dashboard.btnGraphToggle.setText("⏹  Live Plotting: OFF")
            self.dashboard.btnGraphToggle.setStyleSheet(
                "QPushButton{"
                "background:#D7CCC8; color:#4E342E; font-weight:600;"
                "border-radius:12px; padding:8px;"
                "}"
                "QPushButton:hover{ background:#BCAAA4; }"
            )

    def updateGraph(self):
        # Bypass entirely when paused or when the person has switched
        # live plotting off - skip collection AND rendering.
        if getattr(self.dashboard, "is_paused", False):
            return
        if not self.plotting_enabled:
            return

        self.stm_acc_x.append(STM32_VALUES["AX"])
        self.stm_acc_y.append(STM32_VALUES["AY"])
        self.stm_acc_z.append(STM32_VALUES["AZ"])
        self.stm_gyr_x.append(STM32_VALUES["GX"])
        self.stm_gyr_y.append(STM32_VALUES["GY"])
        self.stm_gyr_z.append(STM32_VALUES["GZ"])

        self.ph_acc_x.append(PHONE_VALUES["AX"])
        self.ph_acc_y.append(PHONE_VALUES["AY"])
        self.ph_acc_z.append(PHONE_VALUES["AZ"])
        self.ph_gyr_x.append(PHONE_VALUES["GX"])
        self.ph_gyr_y.append(PHONE_VALUES["GY"])
        self.ph_gyr_z.append(PHONE_VALUES["GZ"])

        self._plotOne(self.ax_stm_acc, (self.stm_acc_x, self.stm_acc_y, self.stm_acc_z),
                      "STM32 Accelerometer (m/s\u00b2)")
        self._plotOne(self.ax_ph_acc, (self.ph_acc_x, self.ph_acc_y, self.ph_acc_z),
                      "Phone Accelerometer (m/s\u00b2)")
        self._plotOne(self.ax_stm_gyr, (self.stm_gyr_x, self.stm_gyr_y, self.stm_gyr_z),
                      "STM32 Gyroscope (rad/s)")
        self._plotOne(self.ax_ph_gyr, (self.ph_gyr_x, self.ph_gyr_y, self.ph_gyr_z),
                      "Phone Gyroscope (rad/s)")

        # Without this, Qt's FigureCanvasQTAgg never actually repaints -
        # the axes data updates internally but nothing reaches the screen
        # until a redraw is explicitly requested.
        self.canvas.draw_idle()

    def _plotOne(self, ax, series, title):
        ax.clear()
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.tick_params(axis="both", labelsize=8)

        colors = ("#E65100", "#43A047", "#1E88E5")
        labels = ("X-Axis", "Y-Axis", "Z-Axis")
        for data, color, label in zip(series, colors, labels):
            ax.plot(data, color=color, label=label, linewidth=1.2)

        ax.set_title(title, fontsize=9, fontweight="bold", color="#5D4037")
        ax.legend(loc="upper right", fontsize=7, framealpha=0.85, ncol=1)


class CalibrationWizard(QObject):

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.step = 0
        self.is_calibrating = False

        self.steps = [
            "STEP 1: Wave & rotate the setup randomly in the air!",
            "STEP 2: Place the setup completely flat and STILL on the table",
            "Finished"
        ]

        self.recorder = SampleRecorder()
        self.dashboard.btnCalibration.clicked.connect(self.handleButtonClick)

        self.collectTimer = QTimer()
        self.collectTimer.timeout.connect(self.performCollection)
        self.collectCount = 0

        self.dynamicSTM = []
        self.dynamicPhone = []
        self.staticSTM = []
        self.staticPhone = []

    def handleButtonClick(self):
        if not self.is_calibrating:
            self.is_calibrating = True
            self.step = 0
            self.recorder.clear()
            self.dynamicSTM.clear()
            self.dynamicPhone.clear()
            self.staticSTM.clear()
            self.staticPhone.clear()
            self.dashboard.btnCalibration.setText("Next Step")
            self.showStep()
        else:
            self.dashboard.btnCalibration.setEnabled(False)
            if self.step == 0:
                self.dashboard.calInstruction.setText("⚡ Recording motion... KEEP WAVING IT!")
            else:
                self.dashboard.calInstruction.setText("⚡ Recording baseline... DO NOT TOUCH IT!")

            QCoreApplication.processEvents()
            self.startCollecting()

    def showStep(self):
        self.dashboard.calInstruction.setText(self.steps[self.step])
        percent = int(self.step / (len(self.steps) - 1) * 100)
        self.dashboard.progress.setValue(percent)

    def startCollecting(self):
        self.collectCount = 0
        self.recorder.clear()
        self.collectTimer.start(20)

    def performCollection(self):
        if self.collectCount < 250:
            self.recorder.add()
            self.collectCount += 1
        else:
            self.collectTimer.stop()

            if self.step == 0:
                self.dynamicSTM = self.recorder.samplesSTM.copy()
                self.dynamicPhone = self.recorder.samplesPhone.copy()
            elif self.step == 1:
                self.staticSTM = self.recorder.samplesSTM.copy()
                self.staticPhone = self.recorder.samplesPhone.copy()

            self.step += 1
            self.dashboard.btnCalibration.setEnabled(True)

            if self.step >= len(self.steps) - 1:
                self.finishCalibration()
            else:
                self.showStep()

    def finishCalibration(self):
        self.is_calibrating = False
        self.dashboard.progress.setValue(100)
        self.dashboard.calInstruction.setText("🎉 Processing Data...")
        QCoreApplication.processEvents()
        self.analyse()

    def analyse(self):
        mapper = CorrelationMapper()
        mapping, sign = mapper.findBest(self.dynamicSTM, self.dynamicPhone)

        calc = BiasCalculator()
        bias, scale = calc.calculate(
            self.dynamicSTM, self.dynamicPhone,
            self.staticSTM, self.staticPhone,
            mapping, sign
        )

        self.dashboard.calStatus.setText("Finished")
        self.dashboard.calInstruction.setText("🎉 Calibration Complete!")
        self.dashboard.btnCalibration.setText("Start Calibration")

        data = {
            "mapping": mapping,
            "sign": sign,
            "bias": bias,
            "scale": scale
        }

        dialog = CalibrationResultsDialog(data, self.dashboard)
        dialog.show()
        self._resultsDialog = dialog  # keep a reference so it isn't garbage collected


class SampleRecorder(QObject):

    def __init__(self):
        super().__init__()
        self.samplesSTM = []
        self.samplesPhone = []

    def add(self):
        with data_lock:
            self.samplesSTM.append(STM32_VALUES.copy())
            self.samplesPhone.append(PHONE_VALUES.copy())

    def clear(self):
        with data_lock:
            self.samplesSTM.clear()
            self.samplesPhone.clear()


class CorrelationMapper(QObject):

    def __init__(self):
        super().__init__()

    def getSeries(self, data, key):
        return np.array([x[key] for x in data], dtype=float)

    def correlation(self, a, b):
        if len(a) < 20:
            return 0
        if np.std(a) == 0 or np.std(b) == 0:
            return 0
        corr = np.corrcoef(a, b)[0, 1]
        return 0 if np.isnan(corr) else corr

    def findBest(self, stm, phone):
        accel = ["AX", "AY", "AZ"]
        gyro = ["GX", "GY", "GZ"]
        mapping = {}
        sign = {}

        for s in accel:
            bestAxis = accel[0]
            bestCorr = -1.0
            bestSign = 1

            sData = self.getSeries(stm, s)
            for p in accel:
                pData = self.getSeries(phone, p)
                c = self.correlation(sData, pData)

                if abs(c) >= bestCorr:
                    bestCorr = abs(c)
                    bestAxis = p
                    bestSign = 1 if c >= 0 else -1

            mapping[s] = bestAxis
            sign[s] = bestSign

        for s in gyro:
            bestAxis = gyro[0]
            bestCorr = -1.0
            bestSign = 1

            sData = self.getSeries(stm, s)
            for p in gyro:
                pData = self.getSeries(phone, p)
                c = self.correlation(sData, pData)

                if abs(c) >= bestCorr:
                    bestCorr = abs(c)
                    bestAxis = p
                    bestSign = 1 if c >= 0 else -1

            mapping[s] = bestAxis
            sign[s] = bestSign

        return mapping, sign


class BiasCalculator(QObject):

    def __init__(self):
        super().__init__()

    def get_rms_amplitude(self, data, key):
        values = np.array([x[key] for x in data], dtype=float)
        return np.std(values)

    def get_average(self, data, key):
        values = [x[key] for x in data]
        return sum(values) / len(values)

    def calculate(self, dynamic_stm, dynamic_phone, static_stm, static_phone, mapping, sign):
        bias = {}
        scale = {}

        for axis in mapping.keys():
            phoneAxis = mapping[axis]

            stm_amp = self.get_rms_amplitude(dynamic_stm, axis)
            phone_amp = self.get_rms_amplitude(dynamic_phone, phoneAxis)

            if stm_amp < 0.001:
                scale[axis] = 1.0
            else:
                scale[axis] = phone_amp / stm_amp

        for axis in mapping.keys():
            phoneAxis = mapping[axis]

            s_avg = self.get_average(static_stm, axis)
            p_avg = self.get_average(static_phone, phoneAxis)

            bias[axis] = (p_avg * sign[axis]) - (s_avg * scale[axis])

        return bias, scale


class CalibrationResultsDialog(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration Results")
        self.resize(520, 480)

        layout = QVBoxLayout()
        self.setLayout(layout)

        info = QLabel("Calibration complete. Copy the values below into your STM32 firmware or notes:")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.textBox = QTextEdit()
        self.textBox.setReadOnly(True)
        self.textBox.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.textBox.setFont(QFont("Consolas", 10))
        self.textBox.setPlainText(json.dumps(data, indent=4))
        layout.addWidget(self.textBox)

        btnRow = QHBoxLayout()
        copyBtn = QPushButton("Copy to Clipboard")
        copyBtn.clicked.connect(self.copyToClipboard)
        closeBtn = QPushButton("Close")
        closeBtn.clicked.connect(self.accept)
        btnRow.addWidget(copyBtn)
        btnRow.addStretch()
        btnRow.addWidget(closeBtn)
        layout.addLayout(btnRow)

    def copyToClipboard(self):
        QApplication.clipboard().setText(self.textBox.toPlainText())


class RoundedCard(QFrame):

    def __init__(self, title):
        super().__init__()
        self.setObjectName("RoundedCard")
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.title = QLabel(title)
        self.title.setObjectName("CardTitle")
        layout.addWidget(self.title)
        layout.addStretch()


class Dashboard(QWidget):

    def __init__(self):
        super().__init__()
        self.is_paused = False
        self.build()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btnPause.setText("▶  Resume Live Feed")
            self.btnPause.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FFB74D, stop:1 #EF6C00);"
                "color: white; font-weight: bold; border-radius:12px; padding:10px;"
            )
        else:
            self.btnPause.setText("⏸  Hold Live Readings")
            self.btnPause.setStyleSheet(
                "background: #FBE9E7; color: #BF360C; font-weight: bold;"
                "border: 1px solid #FFCCBC; border-radius:12px; padding:10px;"
            )

    def build(self):
        root = QVBoxLayout()
        self.setLayout(root)

        # Top connection setup segment
        top_container = QFrame()
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)
        top_container.setLayout(top)
        top_container.setFixedHeight(168)
        root.addWidget(top_container)

        self.stmCard = RoundedCard("STM32")
        self.phoneCard = RoundedCard("Phyphox")
        self.calCard = RoundedCard("Calibration")
        self.graphControlCard = RoundedCard("Live View")
        top.addWidget(self.stmCard)
        top.addWidget(self.phoneCard)
        top.addWidget(self.calCard)
        top.addWidget(self.graphControlCard)

        stmLayout = self.stmCard.layout()
        stmLayout.setContentsMargins(12, 8, 12, 8)
        self.stmStatus = QLabel("🔴 Disconnected")
        self.stmPort = QLabel("COM : ---")
        stmLayout.addWidget(self.stmStatus)
        stmLayout.addWidget(self.stmPort)
        stmLayout.addStretch()
        self.btnSTM32 = QPushButton("Auto Detect")
        self.btnSTM32.setFixedHeight(32)
        stmLayout.addWidget(self.btnSTM32)

        phoneLayout = self.phoneCard.layout()
        phoneLayout.setContentsMargins(12, 8, 12, 8)
        self.phoneStatus = QLabel("🔴 Disconnected")
        self.phoneIP = QLabel("IP : ---")
        phoneLayout.addWidget(self.phoneStatus)
        phoneLayout.addWidget(self.phoneIP)
        phoneLayout.addStretch()
        self.btnPhone = QPushButton("Scan Network")
        self.btnPhone.setFixedHeight(32)
        phoneLayout.addWidget(self.btnPhone)

        calLayout = self.calCard.layout()
        calLayout.setContentsMargins(12, 8, 12, 8)
        self.calStatus = QLabel("Status: Idle")
        self.calInstruction = QLabel("Press 'Start' to Begin")
        self.calInstruction.setStyleSheet("font-weight: bold; color: #E65100;")
        calLayout.addWidget(self.calStatus)
        calLayout.addWidget(self.calInstruction)

        cal_action = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(14)
        self.btnCalibration = QPushButton("Start")
        self.btnCalibration.setFixedHeight(32)
        cal_action.addWidget(self.progress, stretch=65)
        cal_action.addWidget(self.btnCalibration, stretch=35)
        calLayout.addLayout(cal_action)

        # Right-most card in the top row: controls whether the live
        # matplotlib graphs are drawn at all, so the person can bypass
        # graph rendering entirely to save CPU/time.
        graphControlLayout = self.graphControlCard.layout()
        graphControlLayout.setContentsMargins(12, 8, 12, 8)
        self.graphControlHint = QLabel("Toggle live chart rendering")
        self.graphControlHint.setStyleSheet("color:#8D6E63; font-size:12px;")
        self.graphControlHint.setWordWrap(True)
        graphControlLayout.addWidget(self.graphControlHint)
        graphControlLayout.addStretch()
        self.btnGraphToggle = QPushButton("🟠  Live Plotting: ON")
        self.btnGraphToggle.setFixedHeight(32)
        self.btnGraphToggle.setStyleSheet(
            "QPushButton{"
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FFB74D, stop:1 #E65100);"
            "color:white; font-weight:600; border-radius:12px; padding:8px;"
            "}"
            "QPushButton:hover{ background:#FB8C00; }"
        )
        graphControlLayout.addWidget(self.btnGraphToggle)

        # Layer 2: Main Grid Canvas Container Frame
        self.graphCard = QFrame()
        self.graphCard.setObjectName("RoundedCard")
        graph_box_layout = QVBoxLayout()
        graph_box_layout.setContentsMargins(8, 8, 8, 8)
        self.graphCard.setLayout(graph_box_layout)

        self.graphPlaceholder = QLabel("Initialising system mapping matrix plots...")
        self.graphPlaceholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.graphCard.layout().addWidget(self.graphPlaceholder)
        root.addWidget(self.graphCard, stretch=10)

        # Layer 3: Main Data Table Base Layer
        bottomContainer = QWidget()
        bottomContainer.setMaximumHeight(230)
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottomContainer.setLayout(bottom_layout)
        root.addWidget(bottomContainer, stretch=0)

        tableFrame = QFrame()
        tableFrame.setObjectName("ExcelBoxedContainer")
        tableFrame.setFrameShape(QFrame.Shape.StyledPanel)
        tableFrame.setFrameShadow(QFrame.Shadow.Plain)

        table = QGridLayout()
        table.setSpacing(1)
        table.setContentsMargins(1, 1, 1, 1)
        tableFrame.setLayout(table)

        bottom_layout.addWidget(tableFrame, stretch=75)

        headers = ["Axis", "STM32", "Phyphox", "Difference", "% Difference"]
        for c, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setObjectName("ExcelHeader")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            table.addWidget(lbl, 0, c)

        self.labels = {}
        axes = ["AX", "AY", "AZ", "GX", "GY", "GZ"]

        for r, a in enumerate(axes, 1):
            row_title = QLabel(f"{a}")
            row_title.setObjectName("ExcelRowTitle")
            row_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            table.addWidget(row_title, r, 0)

            fc = QLabel("0.000")
            phone = QLabel("0.000")
            diff = QLabel("0.000")
            pct = QLabel("0.0%")

            fc.setObjectName("ExcelCell")
            phone.setObjectName("ExcelCell")
            diff.setObjectName("ExcelCellDelta")
            pct.setObjectName("ExcelCellPercentage")

            for cell in [fc, phone, diff, pct]:
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)

            table.addWidget(fc, r, 1)
            table.addWidget(phone, r, 2)
            table.addWidget(diff, r, 3)
            table.addWidget(pct, r, 4)

            self.labels[a] = (fc, phone, diff, pct)

        metrics_sidebar = QFrame()
        metrics_sidebar.setObjectName("RoundedCard")
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        metrics_sidebar.setLayout(sidebar_layout)

        bottom_layout.addWidget(metrics_sidebar, stretch=25)

        sidebar_layout.addStretch()

        self.accelError = QLabel("Accel Error : 0.000 m/s\u00b2")
        self.accelError.setStyleSheet("font-weight: bold; font-size: 13px; color:#BF360C;")
        sidebar_layout.addWidget(self.accelError)
        sidebar_layout.addSpacing(8)

        self.gyroError = QLabel("Gyro Error : 0.0000 rad/s")
        self.gyroError.setStyleSheet("font-weight: bold; font-size: 13px; color:#BF360C;")
        sidebar_layout.addWidget(self.gyroError)
        sidebar_layout.addSpacing(8)

        self.sampleRate = QLabel("Sample Rate : --- Hz")
        self.sampleRate.setStyleSheet("color: #8D6E63; font-size: 12px;")
        sidebar_layout.addWidget(self.sampleRate)

        sidebar_layout.addStretch()

        self.btnPause = QPushButton("⏸  Hold Live Readings")
        self.btnPause.setStyleSheet(
            "background: #FBE9E7; color: #BF360C; font-weight: bold;"
            "border: 1px solid #FFCCBC; border-radius:12px; padding:10px;"
        )
        self.btnPause.clicked.connect(self.toggle_pause)
        sidebar_layout.addWidget(self.btnPause)


class Style:

    @staticmethod
    def apply(app):
        app.setStyleSheet("""
        QMainWindow{ background:#FDF6EC; }
        QWidget{ background:#FDF6EC; font-size:14px; color:#5D4037; }

        #RoundedCard{
            background: #FFFFFF;
            border: 2px solid #FFD9A0;
            border-radius: 20px;
            padding: 8px;
        }

        #MainTitle{
            font-size:30px;
            font-weight:bold;
            color:#E65100;
            padding:12px;
        }

        #CardTitle{
            font-size:17px;
            font-weight:700;
            color:#E65100;
            padding-bottom:4px;
            border-bottom: 2px solid #FFE0B2;
        }

        QPushButton{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFA84D, stop:1 #F57C00);
            border:none;
            border-radius:12px;
            padding:10px;
            font-size:14px;
            font-weight:600;
            color:white;
        }
        QPushButton:hover{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFB74D, stop:1 #FB8C00);
        }
        QPushButton:pressed{
            background:#E65100;
        }
        QPushButton:disabled{
            background:#EFC9A0;
            color:#FFF3E0;
        }

        QLabel{ color:#5D4037; }

        QProgressBar{
            border: 1px solid #FFCC80;
            border-radius: 7px;
            background: #FFF3E0;
            text-align: center;
            color:#5D4037;
        }
        QProgressBar::chunk{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFB74D, stop:1 #E65100);
            border-radius: 6px;
        }

        #ExcelBoxedContainer{
            background: white;
            border: 2px solid #FFD9A0;
            border-radius: 14px;
        }
        #ExcelHeader{
            background: #FB8C00;
            color: white;
            font-weight: 700;
            padding: 6px;
            border-radius: 4px;
        }
        #ExcelRowTitle{
            background: #FFE0B2;
            font-weight: 700;
            color: #E65100;
            padding: 4px;
        }
        #ExcelCell{
            background: #FFFDF9;
            padding: 4px;
            border-radius: 3px;
        }
        #ExcelCellDelta{
            background: #FFF3E0;
            color: #BF360C;
            font-weight: 600;
            padding: 4px;
            border-radius: 3px;
        }
        #ExcelCellPercentage{
            background: #FFECB3;
            color: #E65100;
            font-weight: 700;
            padding: 4px;
            border-radius: 3px;
        }
        """)


def startProgram():
    global sampleRate

    app = QApplication(sys.argv)
    Style.apply(app)

    window = MainWindow()
    dashboard = Dashboard()
    dashboard.setParent(window)  # Ensures the sample rate loop can find it
    window.setDashboard(dashboard)

    stm32 = STM32Manager(dashboard)
    phyphox = PhyphoxManager(dashboard)
    updater = GUIUpdater(dashboard)
    difference = DifferenceManager(dashboard)
    graphs = GraphManager(dashboard)
    calibration = CalibrationWizard(dashboard)
    sampleRate = SampleRate(dashboard)

    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    startProgram()