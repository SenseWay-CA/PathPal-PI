


import time
import board
import busio
from heartrate_monitor import HeartRateMonitor
import time
from TfLunaI2C import TfLunaI2C
import adafruit_mpu6050

# ---------------------------------------------------------------
# MAX30102
# -------------------------------------------------------------

def init_max30102():
    try:
        hr = HeartRateMonitor
        HeartRateMonitor.start_sensor(hr)
        print("[OK] MAX30102 initialized")
        return hr
    except Exception as e:
        print("[ERR] MAX30102 init:", e)


# ---------------------------------------------------------------
# MPU6050 – Adafruit CircuitPython library
# ---------------------------------------------------------------
def init_mpu6050():
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        mpu = adafruit_mpu6050.MPU6050(i2c)
        print("[OK] MPU6050 initialized (CircuitPython)")
        return mpu
    except Exception as e:
        print("[ERR] MPU init error:", e)
        return None

# ---------------------------------------------------------------
# TF-Luna LiDAR – your library
# ---------------------------------------------------------------
def init_lidar():
    try:
        lidar = TfLunaI2C()
        lidar.us = False
        print(lidar)
        return lidar
    except Exception as e:
        print("[ERR] TF-Luna init:", e)
        return None

# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("Initializing sensors...")
    init_max30102()
    mpu = init_mpu6050()
    lidar = init_lidar()
    hr = init_max30102()

    print("\n All sensors active. Reading...\n")

    while True:
        # MAX30102
        bpm = hr.bpm

        # TF-Luna
        try:    
            data = lidar.read_data()
            distance = lidar.dist

         
            
        except:
            distance = None

        # MPU6050 (CircuitPython)
        if mpu:
            accel = mpu.acceleration  # (x, y, z)
            gyro  = mpu.gyro          # (x, y, z)
        else:
            accel = gyro = None

        print("-------------------------------------------------------")
        print("MAX30102 → BPM:", bpm)
        print("TF-Luna  → Distance:", distance, "cm")

        if accel and gyro:
            print(f"MPU6050 → Accel(g): {accel}")
            print(f"MPU6050 → Gyro(dps): {gyro}")
        else:
            print("MPU6050 → Error")

        time.sleep(0.2)
