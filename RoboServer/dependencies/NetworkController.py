import threading
import time
from enum import Enum, auto
import requests
import asyncio
from websockets.server import serve
import websockets
from websockets.exceptions import ConnectionClosedOK
import socket
from zeroconf import ServiceBrowser, Zeroconf
import numpy as np

class modes(Enum):
    idle = auto()
    ip_connecting = auto()
    auto_connecting = auto()

class NetworkController:
    def __init__(self, connector):
        self.connector = connector
        self.connecting_mode = modes.idle
        
    def run(self):
        self.running = True
        thread = threading.Thread(target=self.thread_function)
        thread.start()

    def stop(self):
        self.running = False

    def thread_function(self):
        while self.running:
            if not self.connector.network_queue.empty():
                task = self.connector.network_queue.get()
                self.parse_task(task)
            
            if self.connecting_mode == modes.ip_connecting:
                self.ip_connecting_step()

            if self.connecting_mode == modes.auto_connecting:
                self.auto_connecting_step()

            time.sleep(1)

    def parse_task(self, task):
        if task["name"] == "start ip connection":
            self.connecting_ip = task["ip"]
            self.connecting_mode = modes.ip_connecting

        elif task["name"] == "start auto connection":
            self.connecting_mode = modes.auto_connecting

        elif task["name"] == "cancel connection":
            self.connecting_mode = modes.idle

    def ip_connecting_step(self):
        server_url = "http://" + self.connecting_ip + ":8000"
        self.connector.ui_queue.put({"name" : "set status", "status" : "awaiting responce from " + server_url, "percentage" : 30})
        try:
            response = requests.get(server_url)
            if response.text == "OK":
                self.connector.ui_queue.put({"name" : "set status", "status" : "opening websocket", "percentage" : 60})
                self.connecting_mode = modes.idle

        except:
            self.connector.ui_queue.put({"name" : "failed to connect"})
            self.connecting_mode = modes.idle

    def auto_connecting_step(self):
        pass


class SocketServerController():
    def __init__(self, connector):
        self.connector = connector

    def run(self):
        self.running = True
        thread = threading.Thread(target=self.thread_function)
        thread.start()

    def stop(self):
        self.running = False

    def thread_function(self):
        asyncio.run(self.websocket_server())

    async def websocket_server(self):
        async def handle_client(websocket, path):
            print("Client connected")
            self.connector.ui_queue.put({"name" : "set status", "status" : "awaiting initial package", "percentage" : 90})
            try:
                while self.running:
                    
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                        self.parse_incoming_data(message)
                    except asyncio.TimeoutError:
                        pass

                    if not self.connector.socket_queue.empty():
                        task = self.connector.socket_queue.get()
                        if task["name"] == "send":
                            await websocket.send(task["data"])

                        elif task["name"] == "cancel connection":
                            break

                    await asyncio.sleep(0.01)
            except Exception:
                print("Client disconnected")

        self.server = await websockets.serve(handle_client, "0.0.0.0", 8765)
        while self.running:
            await asyncio.sleep(0.01)

        self.server.close()
        await self.server.wait_closed()

    def data_is_image(self, data):
        return len(data) > 1000

    def parse_incoming_data(self, data):
        if self.data_is_image(data):
            try:
                image = np.frombuffer(data, dtype=np.uint8).reshape((256, 256, 3))
                self.connector.variables.incoming_image = image
                self.connector.kernel_queue.put({"name" : "recieved image"})
            except Exception:
                print("error when getting image")
        elif data[0] == "C":
            self.connector.ui_queue.put({"name": "command responce", "data" : data[1:]})
                
            
        elif data == "handshake":
            self.connector.ui_queue.put({"name" : "set status", "status" : "done", "percentage" : 100})
            self.connector.ui_queue.put({"name" : "connected successfully"})
            self.connector.variables.device_is_connected = True
            self.connector.kernel_queue.put({"name" : "device is connected"})
    
class MDNSListener:
    def __init__(self, connector):
        self.connector = connector

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        self.connector.kernel_queue.put({"name" : "mdns new device", "ip" : socket.inet_ntoa(info.addresses[0])})

    def update_service(self, zeroconf, type, name):
        pass
        
    def remove_service(self, zeroconf, type, name):
        pass

class MDNSController():
    def __init__(self, connector):
        self.connector = connector
        self.stop_event = threading.Event()

    def run(self):
        thread = threading.Thread(target=self.thread_function)
        thread.start()

    def stop(self):
        self.stop_event.set()

    def thread_function(self):
        zeroconf = Zeroconf()
        listener = MDNSListener(self.connector)
        browser = ServiceBrowser(zeroconf, "_myrobot._tcp.local.", listener)

        try:
            self.stop_event.wait()
        finally:
            zeroconf.close()