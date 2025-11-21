# bt_sender.py
import bluetooth
import threading
import json

class BluetoothSender:
    def __init__(self):
        self.server_sock = None
        self.client_sock = None
        self.connected = False
        self.running = False
        self.thread = None

    def start(self):
        """Starts the Bluetooth server in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._accept_connections)
        self.thread.daemon = True
        self.thread.start()

    def _accept_connections(self):
        # Setup RFCOMM server
        self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.server_sock.bind(("", bluetooth.PORT_ANY))
        self.server_sock.listen(1)

        port = self.server_sock.getsockname()[1]
        print(f"[BT] Waiting for connection on RFCOMM channel {port}...")

        # Advertise the Serial Port service
        bluetooth.advertise_service(self.server_sock, "PathPalPi",
                                    service_id="00001101-0000-1000-8000-00805F9B34FB",
                                    service_classes=[bluetooth.SERIAL_PORT_CLASS],
                                    profiles=[bluetooth.SERIAL_PORT_PROFILE])

        while self.running:
            try:
                # Accept connection (Blocking call)
                client, client_info = self.server_sock.accept()
                print(f"[BT] Accepted connection from {client_info}")
                self.client_sock = client
                self.connected = True
                
                # Keep connection alive until broken
                while self.connected and self.running:
                    pass  # The sending is handled by the send_data method
                    
            except Exception as e:
                print(f"[BT] Connection lost/error: {e}")
                self.connected = False
                if self.client_sock:
                    self.client_sock.close()

    def send_data(self, data_dict):
        """Sends a dictionary as a JSON string followed by a newline."""
        if not self.connected or not self.client_sock:
            return

        try:
            # Convert dict to JSON string + newline for easy parsing on Android
            message = json.dumps(data_dict) + "\n"
            self.client_sock.send(message)
        except Exception as e:
            print(f"[BT] Send failed: {e}")
            self.connected = False
            self.client_sock.close()

    def stop(self):
        self.running = False
        if self.server_sock:
            self.server_sock.close()
        if self.client_sock:
            self.client_sock.close()