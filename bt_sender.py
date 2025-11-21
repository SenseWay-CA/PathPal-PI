import bluetooth
import threading
import json
import time

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
                # FIX: Use time.sleep(1) instead of 'pass' to save CPU
                while self.connected and self.running:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[BT] Connection lost/error: {e}")
            finally:
                # Clean up connection on error or disconnect
                self.connected = False
                if self.client_sock:
                    try:
                        self.client_sock.close()
                    except:
                        pass
                self.client_sock = None

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
            try:
                self.client_sock.close()
            except:
                pass
            self.client_sock = None

    def stop(self):
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass
        if self.client_sock:
            try:
                self.client_sock.close()
            except:
                pass