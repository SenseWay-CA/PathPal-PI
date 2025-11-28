import time
import board
import busio
# Standard imports
import io
import base64
import sys # Added to help print errors without crashing

# ---------------------------------------------------------------
# IMPORT YOUR SENSORS
# ---------------------------------------------------------------
# We wrap imports in try/except just in case a file is missing
try:
    from hr2 import HeartRateMonitor
    from TfLunaI2C import TfLunaI2C
    import adafruit_mpu6050
    from bt_sender import BluetoothSender 
except ImportError as e:
    print(f"[CRITICAL] Library missing: {e}")
    # We continue, but sensors relying on this will fail gracefully below

# Camera Imports
try:
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
except ImportError:
    print("[WARN] picamera2 library not found. Camera disabled.")
    CAMERA_AVAILABLE = False


# ---------------------------------------------------------------
# 1. ROBUST INIT FUNCTIONS (These allow failures without crashing)
# ---------------------------------------------------------------

def init_max30102():
    try:
        hr = HeartRateMonitor()
        hr.start_sensor()
        print("[OK] MAX30102 initialized")
        return hr
    except Exception as e:
        # Just print error, return None so the main loop knows it failed
        print(f"[ERR] MAX30102 init failed: {e}")
        return None

def init_mpu6050():
    try:
        # Re-initialize I2C to ensure clean bus state
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
        # Depending on your specific library version, this might fail if disconnected
        lidar.us = False 
        print("[OK] TF-Luna initialized")
        return lidar
    except Exception as e:
        print(f"[ERR] TF-Luna init failed: {e}")
        return None

def init_camera():
    if not CAMERA_AVAILABLE:
        return None
    try:
        picam2 = Picamera2()
        config = picam2.create_still_configuration(main={"size": (320, 240)})
        picam2.configure(config)
        picam2.start()
        print("[OK] Pi Camera 3 initialized")
        return picam2
    except Exception as e:
        print(f"[ERR] Camera init failed: {e}")
        return None

def capture_frame_base64(cam):
    if cam is None:
        return ""
    try:
        stream = io.BytesIO()
        cam.capture_file(stream, format='jpeg')
        stream.seek(0)
        b64_bytes = base64.b64encode(stream.read())
        return b64_bytes.decode('utf-8')
    except Exception as e:
        print(f"[CAM ERR] Capture failed: {e}")
        # Return empty string, don't crash
        return ""


# ---------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("---------------------------------------")
    print("STARTING ROBUST SENSOR LOOP")
    print("Disconnecting sensors will NOT stop the script.")
    print("---------------------------------------")

    # 1. Initial Setup
    mpu = init_mpu6050()
    lidar = init_lidar()
    hr = init_max30102()
    cam = init_camera()

    # Bluetooth Setup
    try:
        bt = BluetoothSender() 
        bt.start()
        print("[OK] Bluetooth Sender started")
    except Exception as e:
        print(f"[FATAL] Bluetooth start failed: {e}")
        bt = None 
        # We continue even if BT fails, just to see sensor data in console

    loop_count = 0 

    while True:
        loop_count += 1
        
        # --- SAFE VARIABLES (Default to 0 if sensors fail) ---
        bpm = 0
        distance = 0
        accel = [0, 0, 0]
        gyro = [0, 0, 0]
        image_b64 = ""


        # ---------------------------------------------
        # 1. MAX30102 (Heart Rate)
        # ---------------------------------------------
        if hr is None:
            # Try to reconnect
            hr = init_max30102()
        
        # If we have a sensor object, try to read
        if hr is not None:
            try:
                bpm = hr.bpm
            except Exception as e:
                print(f"[READ ERR] Heart Sensor: {e}")
                hr = None # Set to None so we try to re-init next loop


        # ---------------------------------------------
        # 2. TF-Luna LiDAR (The one causing crashes)
        # ---------------------------------------------
        if lidar is None:
            lidar = init_lidar()

        if lidar is not None:
            try:
                # We wrap the READ in a try/except block
                lidar.read_data()
                distance = lidar.dist
            except Exception as e:
                print(f"[READ ERR] LiDAR: {e}")
                lidar = None # Force re-init next loop
                distance = 0 


        # ---------------------------------------------
        # 3. MPU6050 (Gyro/Accel)
        # ---------------------------------------------
        if mpu is None:
            mpu = init_mpu6050()

        if mpu is not None:
            try:
                accel = mpu.acceleration
                gyro  = mpu.gyro
            except Exception as e:
                print(f"[READ ERR] MPU6050: {e}")
                mpu = None # Force re-init next loop


        # ---------------------------------------------
        # 4. Camera
        # ---------------------------------------------
        # Only try to reconnect camera occasionally (every 20 loops) to save CPU
        if cam is None and CAMERA_AVAILABLE and (loop_count % 20 == 0):
            cam = init_camera()
        
        if cam is not None:
            try:
                image_b64 = capture_frame_base64(cam)
            except Exception:
                # If capture fails, assume camera died
                cam = None
                image_b64 = ""


        # ---------------------------------------------
        # 5. Send Data
        # ---------------------------------------------
        packet = {
            "bpm": bpm,
            "dist_cm": distance if distance is not None else 0,
            "accel": accel,
            "gyro": gyro,
            "image": image_b64
        }    

        if bt:
            try:
                bt.send_data(packet)
            except Exception as e:
                print(f"[BT ERR] Send failed: {e}")
                # We do not set bt=None because sockets can sometimes recover.
                # If you want it to hard-reset Bluetooth, you would do: bt = None


        # ---------------------------------------------
        # 6. Console Output
        # ---------------------------------------------
        print(f"\n--- Loop {loop_count} ---")
        
        if lidar is not None:
            print(f"LiDAR   : {distance} cm")
        else:
            print("LiDAR   : [DISCONNECTED]")

        if hr is not None:
            print(f"Heart   : {bpm} BPM")
        else:
            print("Heart   : [DISCONNECTED]")

        if mpu is not None:
            print(f"MPU6050 : OK")
        else:
            print("MPU6050 : [DISCONNECTED]")

        if image_b64:
            print(f"Camera  : Sent Frame ({len(image_b64)} bytes)")

        # Slow down slightly so we don't spam the "Reconnect" logic too fast
        time.sleep(0.2)