from max30102 import MAX30102
import hrcalc
import threading
import time
import numpy as np


class HeartRateMonitor(object):
    """
    A class that reads MAX30102 heart rate data in a background thread.
    Now includes:
      - I2C error handling
      - Auto-reset on Errno 5
      - Finger detection
      - Stable rolling buffer
    """

    LOOP_TIME = 0.01  # ~100Hz sampling

    def __init__(self, print_raw=False, print_result=False):
        self.bpm = 0
        self.print_raw = print_raw
        self.print_result = print_result
        self._thread = None

    # ---------------------------------------------------------
    # MAIN SENSOR LOOP WITH FULL ERROR RECOVERY
    # ---------------------------------------------------------
    def run_sensor(self):
        sensor = MAX30102()

        ir_data = []
        red_data = []

        consecutive_errors = 0

        while not getattr(self._thread, "stopped", False):

            try:
                num_bytes = sensor.get_data_present()

            except OSError as e:
                print("I2C read error (get_data_present):", e)
                consecutive_errors += 1
                if consecutive_errors > 3:
                    print("Resetting MAX30102...")
                    try:
                        sensor.reset()
                        time.sleep(0.1)
                        sensor.setup()
                        time.sleep(0.3)
                        consecutive_errors = 0
                    except:
                        pass
                time.sleep(0.1)
                continue

            if num_bytes > 0:

                while num_bytes > 0:
                    try:
                        red, ir = sensor.read_fifo()
                    except OSError as e:
                        print("I2C FIFO read error:", e)
                        consecutive_errors += 1
                        break

                    num_bytes -= 1

                    ir_data.append(ir)
                    red_data.append(red)

                    if self.print_raw:
                        print(f"{ir}, {red}")

                # trim rolling buffer
                if len(ir_data) > 100:
                    ir_data = ir_data[-100:]
                    red_data = red_data[-100:]

                # enough samples for HR calculation
                if len(ir_data) == 100:

                    # detect finger removed → very low IR & RED
                    if np.mean(ir_data) < 50000:
                        self.bpm = 0
                        if self.print_result:
                            print("No finger detected")
                        continue

                    # run heart rate algorithm
                    bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(
                        ir_data, red_data
                    )

                    if valid_bpm:
                        self.bpm = bpm
                    else:
                        self.bpm = 0

                    if self.print_result:
                        print(f"BPM: {self.bpm:.1f} | SpO2: {spo2}")

            time.sleep(self.LOOP_TIME)

        # shutdown on exit
        try:
            sensor.shutdown()
        except:
            pass

    # ---------------------------------------------------------
    def start_sensor(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run_sensor)
        self._thread.stopped = False
        self._thread.start()

    # ---------------------------------------------------------
    def stop_sensor(self, timeout=2.0):
        if not self._thread:
            return
        self._thread.stopped = True
        self._thread.join(timeout)
        self.bpm = 0
