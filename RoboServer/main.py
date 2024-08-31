import threading
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
import sys
import cv2

from dependencies.Connector import Connector
from dependencies.UiController import UiController
from dependencies.NetworkController import NetworkController
from dependencies.NetworkController import SocketServerController
from dependencies.NetworkController import MDNSController


class MoveControlManager:
    def __init__(self, connector):
        self.connector = connector
        self.forward = False
        self.backward = False
        self.left = False
        self.right = False
        self.current_speed = 0
        self.current_angle = 0
        self.new_speed = 0
        self.new_angle = 0

    def set_speed(self, speed):
        self.new_speed = speed

    def set_angle(self, angle):
        self.new_angle = angle

    def update(self):
        if self.new_speed != self.current_speed or self.new_angle != self.current_angle:
            self.connector.socket_queue.put({"name" : "send", "data" : "speed " + str(self.new_speed) + " angle " + str(self.new_angle)})
        self.current_angle = self.new_angle
        self.current_speed = self.new_speed

    def parce_button_task(self, task):
        button_is_pressed = task["operation"] == "pressed"
        if task["button"] == "forward":
            self.forward = button_is_pressed
        if task["button"] == "backward":
            self.backward = button_is_pressed
        if task["button"] == "left":
            self.left = button_is_pressed
        if task["button"] == "right":
            self.right = button_is_pressed

        if self.forward:
            self.set_speed(100)
        elif self.backward:
            self.set_speed(-100)
        else:
            self.set_speed(0)

        if self.left:
            self.set_angle(-50)
        elif self.right:
            self.set_angle(50)
        else:
            self.set_angle(0)

        if self.new_angle != 0 and self.new_speed == 0:
            self.new_speed = 100
            self.new_angle *= 2
        
        
class Kernel:
    def __init__(self, connector):
        self.connector = connector
        self.mdns_found_ip = None
        self.waiting_mdsn_device = False
        self.move_control_manager = MoveControlManager(connector)
        
    def run(self):
        self.running = True
        thread = threading.Thread(target=self.thread_function)
        thread.start()

    def stop(self):
        self.running = False

    def thread_function(self):
        while self.running:
            if not self.connector.kernel_queue.empty():
                task = self.connector.kernel_queue.get()
                self.parce_task(task)

            if self.waiting_mdsn_device and self.mdns_found_ip:
                self.connector.network_queue.put({"name" : "start ip connection", "ip" : self.mdns_found_ip})
                self.waiting_mdsn_device = False

            self.move_control_manager.update()
            time.sleep(0.01)

    def parce_task(self, task):
        if task["name"] == "mdns new device":
            self.mdns_found_ip = task["ip"]

        if task["name"] == "get last mdns device":
            self.waiting_mdsn_device = True

        if task["name"] == "command from console":
            self.parce_console_command(task["command"])

        if task["name"] == "recieved image":
            self.connector.socket_queue.put({"name" : "send", "data" : "get image"})
            image = self.connector.variables.incoming_image
            rescaled_image = cv2.resize(image, (512, 512))
            flipped_image = cv2.flip(rescaled_image, 0)
            flipped_image = cv2.flip(flipped_image, 1)
            self.connector.variables.displayed_image = flipped_image
            self.connector.ui_queue.put({"name" : "update image"})

        if task["name"] == "device is connected":
            self.connector.socket_queue.put({"name" : "send", "data" : "get image"})

        if task["name"] == "button operation":
            self.move_control_manager.parce_button_task(task)

    def parce_console_command(self, command):
        if command == "/modules":
            if not self.connector.variables.device_is_connected:
                self.connector.ui_queue.put({"name": "command responce", "data" : "device is not connected"})
                return
            self.connector.socket_queue.put({"name" : "send", "data" : "modules"})
            self.connector.ui_queue.put({"name": "command responce", "data" : "collecting data..."})

        elif command.startswith("/add network") and len(command.split()) == 4:
            if not self.connector.variables.device_is_connected:
                self.connector.ui_queue.put({"name": "command responce", "data" : "device is not connected"})
                return
            network_name = command.split()[2]
            network_pass = command.split()[3]
            self.connector.socket_queue.put({"name" : "send", "data" : "add_network " + network_name + " " + network_pass})
            self.connector.ui_queue.put({"name": "command responce", "data" : "network configuration request sent"})
            
        elif command.startswith("/"):
             self.connector.ui_queue.put({"name": "command responce", "data" : "no such command"})
            

def main():
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(218, 130, 42))
    palette.setColor(QPalette.Highlight, QColor(218, 130, 42))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    connector = Connector()
    kernel = Kernel(connector)
    kernel.run()

    network_controller = NetworkController(connector)
    network_controller.run()

    socket_server_controller = SocketServerController(connector)
    socket_server_controller.run()

    ui_controller = UiController(connector)
    ui_controller.run()

    mdns_controller = MDNSController(connector)
    mdns_controller.run()

    try:
        sys.exit(app.exec_())
    except:
        print("Exiting")
        kernel.stop()
        network_controller.stop()
        mdns_controller.stop()
        socket_server_controller.stop()

main()