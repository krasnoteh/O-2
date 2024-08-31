import queue

class Variables():
    def __init__(self):
        self.device_is_connected = False
        self.incoming_image = None
        self.displayed_image = None

class Connector():
    def __init__(self):
        self.kernel_queue = queue.Queue()
        self.ui_queue = queue.Queue()
        self.network_queue = queue.Queue()
        self.socket_queue = queue.Queue()

        self.variables = Variables()
