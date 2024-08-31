from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from dependencies.Ui import Ui_MainWindow
from PyQt5.QtGui import QImage, QPixmap
import time
import threading
import numpy as np
from PyQt5.QtCore import Qt

class QueueParser(QThread):
    task_signal = pyqtSignal(object)

    def __init__(self, connector):
        super().__init__()
        self.connector = connector
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            if not self.connector.ui_queue.empty():
                task = self.connector.ui_queue.get()
                self.task_signal.emit(task)
            time.sleep(0.01)

    def stop(self):
        self.running = False

class UiController(QMainWindow, Ui_MainWindow):
    def __init__(self, connector):
        super(UiController, self).__init__()
        self.setupUi(self)
        self.connector = connector
        self.connect_signals()
        self.initial_configure()

    def run(self):
        self.thread = QueueParser(self.connector)
        self.thread.task_signal.connect(self.parse_task)
        self.thread.start()
        self.show()

    def closeEvent(self, event):
        self.thread.stop()
        self.thread.wait()
        event.accept()

    def connect_signals(self):
        self.MapModeButton.clicked.connect(self.swithch_to_map_mode)
        self.DeviceModeButton.clicked.connect(self.switch_to_device_mode)
        self.ConsoleModeButton.clicked.connect(self.switch_to_console_mode)
        self.SettingsModeButton.clicked.connect(self.switch_to_settings_mode)
        self.ConnectDeviceButton.clicked.connect(self.connect_device)
        self.CancelConnection.clicked.connect(self.cancel_connection)
        self.IPConnect.clicked.connect(self.switch_to_enter_ip)
        self.Connect.clicked.connect(self.switch_to_ip_connecting_phase)
        self.AutoConnect.clicked.connect(self.switch_to_auto_connecting_phase)
        self.ModuleButton.clicked.connect(self.use_module)
        self.ConsoleInput.returnPressed.connect(self.console_enter)
        self.ForwardButton.pressed.connect(lambda: self.button_operation("pressed", "forward"))
        self.BackwardButton.pressed.connect(lambda: self.button_operation("pressed", "backward"))
        self.LeftButton.pressed.connect(lambda: self.button_operation("pressed", "left"))
        self.RightButton.pressed.connect(lambda: self.button_operation("pressed", "right"))


        self.ForwardButton.released.connect(lambda: self.button_operation("released", "forward"))
        self.BackwardButton.released.connect(lambda: self.button_operation("released", "backward"))
        self.LeftButton.released.connect(lambda: self.button_operation("released", "left"))
        self.RightButton.released.connect(lambda: self.button_operation("released", "right"))
        self.checkBox.stateChanged.connect(self.headlights_state_changed)

    def initial_configure(self):
        self.MainStack.setCurrentIndex(1)
        self.stackedWidget_2.setCurrentIndex(0)
        array = np.zeros((512, 512, 3), dtype=np.uint8)
        pixmap = self.numpy_array_to_pixmap(array)
        self.map.setPixmap(pixmap)
        self.DeviceVideo.setPixmap(pixmap)

    def numpy_array_to_pixmap(self, array):
        height, width, channel = array.shape
        bytesPerLine = 3 * width
        qImg = QImage(array.data, width, height, bytesPerLine, QImage.Format_RGB888)   
        pixmap =  QPixmap(qImg)
        return pixmap
        
    def swithch_to_map_mode(self):
        self.stackedWidget_2.setCurrentIndex(0)

    def switch_to_device_mode(self):
        if self.connector.variables.device_is_connected:
            self.stackedWidget_2.setCurrentIndex(2)
        else:
            self.stackedWidget_2.setCurrentIndex(1)

    def switch_to_console_mode(self):
        self.stackedWidget_2.setCurrentIndex(3)

    def switch_to_settings_mode(self):
        self.stackedWidget_2.setCurrentIndex(4) 

    def connect_device(self):
        self.stackedWidget.setCurrentIndex(0)
        self.MainStack.setCurrentIndex(0)

    def cancel_connection(self):
        self.MainStack.setCurrentIndex(1)
        self.connector.network_queue.put({"name" : "cancel connection"})

    def switch_to_enter_ip(self):
        self.stackedWidget.setCurrentIndex(1)

    def switch_to_auto_connecting_phase(self):
        self.stackedWidget.setCurrentIndex(2)
        self.connector.network_queue.put({"name" : "start auto connection"})
        self.connector.kernel_queue.put({"name" : "get last mdns device"})
        self.progressBar.setProperty("value", 10)

    def switch_to_ip_connecting_phase(self):
        self.stackedWidget.setCurrentIndex(2)
        self.connector.network_queue.put({"name" : "start ip connection", "ip" : self.IPfield.text()})
        self.connectingState.setText("triggering network kernel")
        self.progressBar.setProperty("value", 10)

    def console_enter(self):
        command = self.ConsoleInput.text()
        self.connector.kernel_queue.put({"name" : "command from console", "command" : command})
        self.ConsoleInput.clear()
        self.console_log(command)

    def use_module(self):
        self.connector.socket_queue.put({"name" : "send", "data" : "use_module"})

    def headlights_state_changed(self, state):
        if state == 2:
            self.connector.socket_queue.put({"name" : "send", "data" : "enable_headlights"})
        else:
            self.connector.socket_queue.put({"name" : "send", "data" : "disable_headlights"})

    def console_log(self, text):
        self.ConsoleOutput.append(text)
        verScrollBar = self.ConsoleOutput.verticalScrollBar()
        verScrollBar.setValue(verScrollBar.maximum())

    def button_operation(self, operation, button):
        self.connector.kernel_queue.put({"name" : "button operation", "operation" : operation, "button" : button})

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_W:
            self.button_operation("pressed", "forward")
        if event.key() == Qt.Key_S:
            self.button_operation("pressed", "backward")
        if event.key() == Qt.Key_A:
            self.button_operation("pressed", "left")
        if event.key() == Qt.Key_D:
            self.button_operation("pressed", "right")

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_W:
            self.button_operation("released", "forward")
        if event.key() == Qt.Key_S:
            self.button_operation("released", "backward")
        if event.key() == Qt.Key_A:
            self.button_operation("released", "left")
        if event.key() == Qt.Key_D:
            self.button_operation("released", "right")
        
    @pyqtSlot(object)
    def parse_task(self, task):
        if task["name"] == "set status":
            self.connectingState.setText(task["status"])
            self.progressBar.setProperty("value", task["percentage"])
        elif task["name"] == "failed to connect":
            self.stackedWidget.setCurrentIndex(3)
        elif task["name"] == "connected successfully":
            self.stackedWidget_2.setCurrentIndex(2)
            self.MainStack.setCurrentIndex(1)
        elif task["name"] == "command responce":
            self.console_log(task["data"])
        elif task["name"] == "update image":
            pixmap = self.numpy_array_to_pixmap(self.connector.variables.displayed_image)
            self.DeviceVideo.setPixmap(pixmap)