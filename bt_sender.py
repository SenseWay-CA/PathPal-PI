import bluetooth
import threading
import json
import time
import queue

class BluetoothSender:
    def __init__(self):
        self.server_sock = None
        self.client_sock = None
        self.connected = False
        self.running = False
        self.accept_thread = None
        self.send_thread = None
        
        # A mailbox to hold messages so the main loop doesn't have to wait
        # Max size 2 ensures we don't pile up old data if the connection is slow
        self.out_queue = queue.Queue(maxsize=2)

    def start(self):
        """Starts the Bluetooth server and sender in background threads."""
        self.running = True
        
        # Thread 1: Accepts new connections
        self.accept_thread = threading.Thread(target=self._accept_connections)
        self.accept_thread.daemon = True
        self.accept_thread.start()
        
        # Thread 2: Handles the slow sending process
        self.send_thread = threading.Thread(target=self._process_queue)
        self.send_thread.daemon = True
        self.send_thread.start()

    def _accept_connections(self):
        try:
            self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.server_sock.bind(("", bluetooth.PORT_ANY))
            self.server_sock.listen(1)

            port = self.server_sock.getsockname()[1]
            print(f"[BT] Waiting for connection on RFCOMM channel {port}...")

            bluetooth.advertise_service(self.server_sock, "PathPalPi",
                                        service_id="00001101-0000-1000-8000-00805F9B34FB",
                                        service_classes=[bluetooth.SERIAL_PORT_CLASS],
                                        profiles=[bluetooth.SERIAL_PORT_PROFILE])
        except Exception as e:
            print(f"[BT] Init failed: {e}")
            return

        while self.running:
            try:
                # This blocks until a phone connects
                client, client_info = self.server_sock.accept()
                print(f"[BT] Accepted connection from {client_info}")
                self.client_sock = client
                self.connected = True
                
                # Monitor connection
                while self.connected and self.running:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[BT] Connection reset/error: {e}")
            finally:
                self.connected = False
                if self.client_sock:
                    try: self.client_sock.close()
                    except: pass
                self.client_sock = None
                # Clear queue so old data doesn't get sent on reconnect
                with self.out_queue.mutex:
                    self.out_queue.queue.clear()

    def _process_queue(self):
        """Constantly checks the mailbox and sends data if connected."""
        while self.running:
            try:
                # Get message from queue (waits 1 sec then loops to check self.running)
                msg = self.out_queue.get(timeout=1)
                
                if self.connected and self.client_sock:
                    try:
                        self.client_sock.send(msg)
                    except Exception as e:
                        print(f"[BT] Send Error: {e}")
                        self.connected = False
                        try: self.client_sock.close()
                        except: pass
                        self.client_sock = None
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[BT] Queue Error: {e}")

    def send_data(self, data_dict):
        """NON-BLOCKING: Puts data in queue and returns immediately."""
        if not self.connected:
            return

        try:
            message = json.dumps(data_dict) + "\n"
            
            # If queue is full (Bluetooth is too slow), remove oldest item
            # This ensures we always send the NEWEST data
            if self.out_queue.full():
                try: self.out_queue.get_nowait()
                except queue.Empty: pass
            
            self.out_queue.put_nowait(message)
            
        except Exception as e:
            # If this fails, it just means queue issues, doesn't crash main loop
            pass

    def stop(self):
        self.running = False
        if self.server_sock:
            try: self.server_sock.close()
            except: pass