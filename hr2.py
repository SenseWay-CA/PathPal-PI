from max30102 import MAX30102
import hrcalc
import threading
import time
import numpy as np


class HeartRateMonitor(object):
    """
    A class that encapsulates the MAX30102 device into a background thread.
    """

    LOOP_TIME = 0.01  # 100 Hz sampling approx

    def __init__(self, print_raw=False, print_result=False):
        self.bpm = 0
        self.print_raw = print_raw
        self.print_result = print_result
        self._thread = None

        if print_raw:
            print("IR, RED")

    # ---------------------------------------------------------
    # MAIN SENSOR LOOP
    # ---------------------------------------------------------
    def run_sensor(self):
        sensor = MAX30102()

        ir_data = []
        red_data = []

        # run until told to stop
        while not getattr(self._thread, "stopped", False):

            num_bytes = sensor.get_data_present()

            if num_bytes > 0:
                # Read all available samples
                while num_bytes > 0:
                    red, ir = sensor.read_fifo()
                    num_bytes -= 1

                    ir_data.append(ir)
                    red_data.append(red)

                    if self.print_raw:
                        print(f"{ir}, {red}")

                # Keep ONLY the last 100 samples (rolling buffer)
                if len(ir_data) > 100:
                    ir_data = ir_data[-100:]
                    red_data = red_data[-100:]

                # Once we have enough samples, estimate HR
                if len(ir_data) == 100:

                    bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(
                        ir_data, red_data
                    )

                    # If a valid BPM reading was found
                    if valid_bpm:
                        self.bpm = bpm

                    else:
                        # Unstable reading → set BPM to 0 instead of freezing
                        self.bpm = 0

                    # Detect if finger is removed
                    if np.mean(ir_data) < 50000 and np.mean(red_data) < 50000:
                        self.bpm = 0
                        if self.print_result:
                            print("Finger not detected")

                    if self.print_result:
                        print(f"BPM: {self.bpm:.1f}, SpO2: {spo2}")

            time.sleep(self.LOOP_TIME)

        sensor.shutdown()

    # ---------------------------------------------------------
    # START THREAD
    # ---------------------------------------------------------
    def start_sensor(self):
        if self._thread and self._thread.is_alive():
            return  # already running

        self._thread = threading.Thread(target=self.run_sensor)
        self._thread.stopped = False
        self._thread.start()

    # ---------------------------------------------------------
    # STOP THREAD
    # ---------------------------------------------------------
    def stop_sensor(self, timeout=2.0):
        if not self._thread:
            return

        self._thread.stopped = True
        self._thread.join(timeout)
        self.bpm = 0
