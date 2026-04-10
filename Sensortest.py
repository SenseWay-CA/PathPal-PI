import time
import board
import busio
import io
import base64
import sys

# ---------------------------------------------------------------
# IMPORT YOUR SENSORS
# ---------------------------------------------------------------
try:
    from hr2 import HeartRateMonitor
    from TfLunaI2C import TfLunaI2C
    import adafruit_mpu6050
    from bt_sender import BluetoothSender 
    from gpiozero import RGBLED  # <--- ADD THIS LINE
except ImportError as e:
    print(f"[CRITICAL] Library missing: {e}")

# Camera Imports


# ---------------------------------------------------------------
# 1. ROBUST INIT FUNCTIONS
# ---------------------------------------------------------------

def init_max30102():
    try:
        hr = HeartRateMonitor()
        hr.start_sensor()
        print("[OK] MAX30102 initialized")
        return hr
    except Exception as e:
        print(f"[ERR] MAX30102 init failed: {e}")
        return None

def init_mpu6050():
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        mpu = adafruit_mpu6050.MPU6050(i2c)
        print("[OK] MPU6050 initialized")
        return mpu
    except Exception as e:
        print(f"[ERR] MPU init failed: {e}")
        return None

def init_lidar():
    try:
        lidar = TfLunaI2C()
        # Verify it works immediately
        lidar.read_data()
        print("[OK] TF-Luna initialized")
        return lidar
    except Exception as e:
        # Do not print stack trace, just simple error
        print(f"[ERR] TF-Luna missing/disconnected")
        return None

def init_status_led():
    try:
        # gpiozero uses BCM GPIO numbers (12, 13, 18)
        # pwm=True allows color mixing and brightness control
        led = RGBLED(red=12, green=13, blue=18, pwm=True)
        
        # Flash white briefly to prove it works
        led.color = (1, 1, 1) 
        time.sleep(0.5)
        led.color = (0, 0, 0) # Turn off
        
        print("[OK] RGB Status LED initialized")
        return led
    except Exception as e:
        print(f"[ERR] LED init failed: {e}")
        return None




# ---------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("---------------------------------------")
    print("STARTING ROBUST SENSOR LOOP")
    print("---------------------------------------")

    mpu = init_mpu6050()
    lidar = init_lidar()
    hr = init_max30102()
    status_led = init_status_led() # <--- ADD THIS LINE
    

    try:
        bt = BluetoothSender() 
        bt.start()
        print("[OK] Bluetooth Sender started")
    except Exception as e:
        print(f"[FATAL] Bluetooth start failed: {e}")
        bt = None 

    loop_count = 0 
     
    LIDAR_RETRY_RATE = 50 # Retry LiDAR only every 50 loops (~5 seconds)

    if status_led:
        status_led.color = (0, 0, 1)


    while True:
        loop_count += 1
        
        # --- SAFE VARIABLES ---
        bpm = 0
        distance = 0
        accel = [0, 0, 0]
        gyro = [0, 0, 0]
  

        # 1. Heart Rate
        if hr is None: hr = init_max30102()
        if hr is not None:
            try: bpm = hr.bpm
            except: hr = None

        # 2. LiDAR (THROTTLED RECONNECT)
        # If LiDAR is disconnected, don't hammer the I2C bus every loop.
        # Wait for the retry counter.
        if lidar is None:
            if loop_count % LIDAR_RETRY_RATE == 0:
                lidar = init_lidar()
        
        if lidar is not None:
            try:
                lidar.read_data()
                distance = lidar.dist
            except Exception as e:
                print(f"[LIDAR LOST] Sensor disconnected.")
                lidar = None # Mark as dead so we stop trying for 5 seconds
                distance = 0

        # 3. MPU6050
        if mpu is None: mpu = init_mpu6050()
        if mpu is not None:
            try:
                accel = mpu.acceleration
                gyro  = mpu.gyro
            except: mpu = None

        # 4. Camera
        

        # 5. Send Data
        packet = {
            "bpm": bpm,
            "dist_cm": distance if distance is not None else 0,
            "accel": accel,
            "gyro": gyro,
            
        }    

        if bt:
            bt.send_data(packet)

        # 6. Console Status
        status = f"Loop {loop_count} | Dist: {distance}cm | BPM: {bpm}"
        
        if lidar is None: status += " | [LIDAR OFF]"
        print(status)

        if status_led:
            if lidar is None:
                # System Error -> RED
                status_led.color = (1, 0, 0) 
            elif bt and bt.connected:
                # Everything working & Phone connected -> GREEN
                status_led.color = (0, 1, 0) 
            else:
                # Working but no phone connected -> BLUE
                status_led.color = (0, 0, 1) 

        time.sleep(0.1)

   
