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
except ImportError as e:
    print(f"[CRITICAL] Library missing: {e}")

# Camera Imports
try:
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
except ImportError:
    print("[WARN] picamera2 library not found. Camera disabled.")
    CAMERA_AVAILABLE = False


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

def init_camera():
    if not CAMERA_AVAILABLE: return None
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
    if cam is None: return ""
    try:
        stream = io.BytesIO()
        cam.capture_file(stream, format='jpeg')
        stream.seek(0)
        b64_bytes = base64.b64encode(stream.read())
        return b64_bytes.decode('utf-8')
    except Exception as e:
        print(f"[CAM ERR] Capture failed")
        return ""


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
    cam = init_camera()

    try:
        bt = BluetoothSender() 
        bt.start()
        print("[OK] Bluetooth Sender started")
    except Exception as e:
        print(f"[FATAL] Bluetooth start failed: {e}")
        bt = None 

    loop_count = 0 
    IMAGE_SEND_RATE = 10 
    LIDAR_RETRY_RATE = 50 # Retry LiDAR only every 50 loops (~5 seconds)

    while True:
        loop_count += 1
        
        # --- SAFE VARIABLES ---
        bpm = 0
        distance = 0
        accel = [0, 0, 0]
        gyro = [0, 0, 0]
        image_b64 = ""

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
        if loop_count % IMAGE_SEND_RATE == 0:
            if cam is None and CAMERA_AVAILABLE: cam = init_camera()
            if cam is not None:
                try:
                    image_b64 = capture_frame_base64(cam)
                except: cam = None
        else:
            image_b64 = ""

        # 5. Send Data
        packet = {
            "bpm": bpm,
            "dist_cm": distance if distance is not None else 0,
            "accel": accel,
            "gyro": gyro,
            "image": image_b64
        }    

        if bt:
            bt.send_data(packet)

        # 6. Console Status
        status = f"Loop {loop_count} | Dist: {distance}cm | BPM: {bpm}"
        if image_b64: status += " | [CAM SENT]"
        if lidar is None: status += " | [LIDAR OFF]"
        print(status)

        time.sleep(0.1)