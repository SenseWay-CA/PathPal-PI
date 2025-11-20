import time
import board
import busio
from smbus2 import SMBus
from TfLunaI2C import TfLunaI2C
import adafruit_mpu6050

# ---------------------------------------------------------------
# MAX30102 – Raw I²C (no CircuitPython driver available)
# ---------------------------------------------------------------
MAX30102_ADDR = 0x57
bus = SMBus(1)

def init_max30102():
    try:
        bus.write_byte_data(MAX30102_ADDR, 0x09, 0x03)  # Mode Config: RED + IR
        bus.write_byte_data(MAX30102_ADDR, 0x0A, 0x27)  # SpO2 Config
        bus.write_byte_data(MAX30102_ADDR, 0x0C, 0x24)  # LED pulse amplitude
        print("[OK] MAX30102 initialized")
    except Exception as e:
        print("[ERR] MAX30102 init:", e)

def read_max30102():
    try:
        data = bus.read_i2c_block_data(MAX30102_ADDR, 0x07, 6)
        red = (data[0]<<16) | (data[1]<<8) | data[2]
        ir  = (data[3]<<16) | (data[4]<<8) | data[5]
        return red & 0x03FFFF, ir & 0x03FFFF
    except:
        return None, None

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

    print("\n All sensors active. Reading...\n")

    while True:
        # MAX30102
        red, ir = read_max30102()

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
        print("MAX30102 → RED:", red, " IR:", ir)
        print("TF-Luna  → Distance:", distance, "cm")

        if accel and gyro:
            print(f"MPU6050 → Accel(g): {accel}")
            print(f"MPU6050 → Gyro(dps): {gyro}")
        else:
            print("MPU6050 → Error")

        time.sleep(0.2)
