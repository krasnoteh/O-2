import threading
import time
import queue
import http.server
import socketserver
import socket
import asyncio
import websockets
from websockets.exceptions import ConnectionClosedOK
from zeroconf import ServiceInfo, Zeroconf
import socket
import subprocess
import smbus2
from picamera2 import Picamera2


class Variables():
    def __init__(self):
        self.device_is_connected = False
        self.server_ip = None
   
class Connector():
    def __init__(self):
        self.kernel_queue = queue.Queue()
        self.socket_queue = queue.Queue()
        self.devices_queue = queue.Queue()

        self.variables = Variables()
        
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        client_ip, client_port = self.client_address
        print(f"Received GET request from {client_ip}:{client_port} for {self.path}")
        print(f"Headers: {self.headers}")
        global connector
        connector.variables.server_ip = client_ip
        self.send_response(200)
        connector.kernel_queue.put({"name" : "start socket"})
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

class HttpServerController:
    def __init__(self, connector):
        self.connector = connector
        self.PORT = 8000
        self.httpd = None
        self.server_thread = None

    def run(self):
        self.server_thread = threading.Thread(target=self.thread_function)
        self.server_thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.server_thread.join()

    def thread_function(self):
        with socketserver.TCPServer(("", self.PORT), RequestHandler) as self.httpd:
            print(f"Serving on port {self.PORT}")
            self.httpd.serve_forever()

class SocketController():
    def __init__(self, connector):
        self.connector = connector
        self.running = False

    def run(self):
        if self.running:
            return
        self.running = True
        thread = threading.Thread(target=self.thread_function)
        thread.start()

    def stop(self):
        self.running = False

    def thread_function(self):
        asyncio.run(self.listen())

    async def listen(self):
        uri = "ws://" + self.connector.variables.server_ip + ":8765"
        print(uri)
        try:
            async with websockets.connect(uri) as websocket:
                while self.running:

                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                        connector.kernel_queue.put({"name" : "recieved", "data" : message})
                    except asyncio.TimeoutError:
                        pass
                    
                    if not self.connector.socket_queue.empty():
                        message = self.connector.socket_queue.get()
                        if message["name"] == "send":
                            await websocket.send(message["data"])
                            if len(message["data"]) < 1000:
                                print("Sent message to server: ", message["data"])
        except Exception:
            self.running = False


connector = Connector()

def get_image(picam2):
    arr = picam2.capture_array()
    arr = arr[:, :, : 3].astype('uint8')
    return arr


def get_ip():
    bashCommand = "ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'"
    output = subprocess.check_output(['bash','-c', bashCommand])
    output = output.decode('utf-8').strip()
    return output


class DoubleSyncController:
    def __init__(self, address, bus):
        self.address = address
        self.control_data = [0]*64
        self.return_data = [0]*64
        self.control_is_modified = [False]*64
        self.bus = bus
        self.online = True

    def send_command(self, command):
        try:
            self.bus.write_i2c_block_data(self.address, 0, list(command))
        except OSError:
            self.online = False

    def recieve_command(self):
        try:
            byte_data = self.bus.read_i2c_block_data(self.address, 0, 8) 
            return b''.join([b.to_bytes(1, signed=False) for b in byte_data])
        except OSError:
            self.online = False
            return b"\0\0\0\0\0\0\0\0"

    def update_control(self):
        self.send_command(b"\x05")
        code = b"\x01"
        for i in range(0, 64):
            if self.control_is_modified[i]:
                self.control_is_modified[i] = False
                index = i.to_bytes(1)
                value = self.control_data[i].to_bytes(4, byteorder='little', signed=True)
                command = code + index + value
                self.send_command(command)
        self.send_command(b"\x06")
                
    def update_return(self):
        self.send_command(b"\x03")
        while self.online:
            command = self.recieve_command()
            code = command[0]
            if code == 2:
                position = command[1]
                value_bytes = command[2:6]
                value = int.from_bytes(value_bytes, byteorder='little', signed=True)
                self.return_data[position] = value
            if code == 4:
                break

    def set_control_value(self, index, value):
        self.control_data[index] = value
        self.control_is_modified[index] = True

    def get_return_value(self, index):
        return self.return_data[index]
    
    def ping(self):
        self.control_is_modified[0] = True
        self.update_control()
    
    def update(self):
        pass
                

class ChassisDevice(DoubleSyncController):
    def __init__(self, bus, connector):
        DoubleSyncController.__init__(self, 0x08, bus)
        self.name = "chassis"
        self.connector = connector
        self.wifi_mode = 0

    def parce_command(self, command):
        if command["name"] == "set data":
            self.set_control_value(1, command["speed"])
            self.set_control_value(2, command["angle"])
            self.update_control()

        if command["name"] == "get":
            self.update_return()
            print(self.get_return_value(command["index"]))

        if command["name"] == "set network mode":
            self.set_control_value(3, command["mode"])
            self.update_control()

        if command["name"] == "headlights":
            self.set_control_value(4, command["mode"])
            self.update_control()

    def update(self):
        self.update_return()
        if self.return_data[1] != self.wifi_mode:
            self.wifi_mode = self.return_data[1]
            self.connector.kernel_queue.put({"name" : "switch wifi mode", "mode" : self.wifi_mode})

class PullModuleDevice(DoubleSyncController):
    def __init__(self, bus, connector):
        DoubleSyncController.__init__(self, 0x09, bus)
        self.name = "pull module"
        self.connector = connector
        self.counter = 0

    def parce_command(self, command):
        if command["name"] == "use":
            self.counter += 1
            self.set_control_value(1, self.counter)
            self.update_control()

        
class DeviceManager:
    def __init__(self, connector): 
        self.connector = connector
        self.bus = smbus2.SMBus(1)
        self.address_to_name = {0x08 : "chassis", 0x09 : "pull module"}
        self.devices = []
        self.update_device_data()
        self.running = False
        self.last_update_all = 0
        self.last_rescan_bus = 0

    def run(self):
        self.running = True
        thread = threading.Thread(target=self.thread_function)
        thread.start()

    def stop(self):
        self.running = False
        self.bus.close()

    def thread_function(self):
        while self.running:
            if not self.connector.devices_queue.empty():
                command = self.connector.devices_queue.get()
                self.parce_command(command)
            self.update_all_handler()
            self.rescan_bus_handler()
            time.sleep(0.01)

    def update_all_handler(self):
        if time.time() - self.last_update_all > 0.1:
            self.last_update_all = time.time()
            for device in self.devices:
                device.update()

    def rescan_bus_handler(self):
        if time.time() - self.last_rescan_bus > 1:
            self.last_rescan_bus = time.time()
            self.clear_offline()
            self.update_device_data()

    def ping_all(self):
        for device in self.devices:
            device.ping()

    def scan_i2c_bus(self):
        devices = []
        for address in range(0x03, 0x78):
            try:
                self.bus.read_byte(address)
                devices.append(address)
            except OSError:
                pass
        return devices
    
    def find_by_name(self, name):
        for device in self.devices:
            if name == device.name:
                return device
        return None
    
    def add_device(self, name):
        if name == "chassis":
            self.devices.append(ChassisDevice(self.bus, self.connector))
        if name == "pull module":
            self.devices.append(PullModuleDevice(self.bus, self.connector))

    def update_device_data(self):
        found_devices = self.scan_i2c_bus()
        for device_address in found_devices:
            device_name = self.address_to_name[device_address]
            if not self.find_by_name(device_name):
                self.add_device(device_name)

    def clear_offline(self):
        self.devices = [device for device in self.devices if device.online]

    def generate_device_list(self):
        self.ping_all()
        self.clear_offline()
        self.update_device_data()
        answer = "found " + str(len(self.devices)) + " connected modules:\n"
        for device in self.devices:
            answer += device.name + "\n"
        return answer
         

    def parce_command(self, command):
        if command["name"] == "send command":
            device_name = command["device name"]
            device = self.find_by_name(device_name)
            if device:
                device.parce_command(command["command"])
        if command["name"] == "get devices":
            self.connector.kernel_queue.put({"name" : "send to server", "data" : "C" + self.generate_device_list()})


def execute_bash(command):
    output = subprocess.check_output(['bash','-c', command])
    output = output.decode('utf-8').strip()
    return output

def generate_service_info():
    service_type = "_myrobot._tcp.local."
    service_name = "MyRobot._myrobot._tcp.local."
    port = 8000
    info = ServiceInfo(type_=service_type,
                   name=service_name,
                   port=port,
                   addresses=[socket.inet_aton(get_ip())])
    return info

def main():
    global connector
    http_server_controller = HttpServerController(connector)
    http_server_controller.run()
    socket_controller = SocketController(connector)

    device_manager = DeviceManager(connector)
    device_manager.run()

    zeroconf = Zeroconf()
    current_service = generate_service_info()
    zeroconf.register_service(current_service)

    picam2 = Picamera2()
    picam2.preview_configuration.size = (256, 256)
    picam2.start()

    previous_image = None
    
    try:
        while(True):
            if not connector.kernel_queue.empty():
                task = connector.kernel_queue.get()
                if task["name"] == "start socket":
                    connector.socket_queue.put({"name" : "send", "data" : "handshake"})
                    socket_controller.run()
                if task["name"] == "recieved":
                    if task["data"] == "get image":
                        if previous_image:
                            connector.socket_queue.put({"name" : "send", "data" : previous_image})
                            image = get_image(picam2)
                            previous_image = image.tobytes()
                        else:
                            image = get_image(picam2)
                            previous_image = image.tobytes()
                            connector.socket_queue.put({"name" : "send", "data" : previous_image})
                    else:
                        print(task["data"])
                        parced_task = task["data"].split()
                        if parced_task[0] == "speed":
                            command_to_device = {"name" : "set data", "speed" : int(parced_task[1]), "angle" : int(parced_task[3])}
                            command = {"name" : "send command", "device name" : "chassis", "command" : command_to_device}
                            connector.devices_queue.put(command)
                        if parced_task[0] == "modules":
                            connector.devices_queue.put({"name" : "get devices"})
                        if parced_task[0] == "add_network":
                            execute_bash('sudo nmcli connection add type wifi ifname wlan0 con-name "' + parced_task[1] + '" ssid "' + parced_task[1] + '"')
                            execute_bash('sudo nmcli connection modify "' + parced_task[1] + '" wifi-sec.key-mgmt wpa-psk')
                            execute_bash('sudo nmcli connection modify "' + parced_task[1] + '" wifi-sec.psk ' + parced_task[2])
                            execute_bash('sudo nmcli connection modify "' + parced_task[1] + '" connection.autoconnect-priority 2')
                            connector.socket_queue.put({"name" : "send", "data" : "Cnext external router connection\
                             will use this network if it is available."})
                            
                        if parced_task[0] == "use_module":
                            command = {"name" : "send command", "device name" : "pull module", "command" : {"name" : "use"}}
                            connector.devices_queue.put(command)

                        if parced_task[0] == "enable_headlights":
                            command = {"name" : "send command", "device name" : "chassis", "command" : {"name" : "headlights", "mode" : 1}}
                            connector.devices_queue.put(command)

                        if parced_task[0] == "disable_headlights":
                            command = {"name" : "send command", "device name" : "chassis", "command" : {"name" : "headlights", "mode" : 0}}
                            connector.devices_queue.put(command)


                if task["name"] == "switch wifi mode":
                    print(task["mode"])
                    if task["mode"] == 1:
                        execute_bash('sudo nmcli connection up o2')
                        zeroconf.unregister_service(current_service)
                        current_service = generate_service_info()
                        zeroconf.register_service(current_service)
                        command_to_device = {"name" : "set network mode", "mode" : 1}
                        command = {"name" : "send command", "device name" : "chassis", "command" : command_to_device}
                        connector.devices_queue.put(command)
                    if task["mode"] == 0:
                        execute_bash('sudo nmcli radio wifi off')
                        execute_bash('sudo nmcli radio wifi on')
                        counter = 0
                        while (counter < 20):
                            try:
                                get_ip()
                                break
                            except Exception:
                                time.sleep(1)
                                counter += 1
                        zeroconf.unregister_service(current_service)
                        current_service = generate_service_info()
                        zeroconf.register_service(current_service)
                        command_to_device = {"name" : "set network mode", "mode" : 0}
                        command = {"name" : "send command", "device name" : "chassis", "command" : command_to_device}
                        connector.devices_queue.put(command)

                if task["name"] == "send to server":
                    connector.socket_queue.put({"name" : "send", "data" : task["data"]})
 
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Exiting")
        socket_controller.stop()
        http_server_controller.stop()
        zeroconf.close()
        device_manager.stop()

main()
