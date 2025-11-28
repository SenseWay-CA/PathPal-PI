import time
import board
import busio
from hr2 import HeartRateMonitor
import time
from TfLunaI2C import TfLunaI2C
import adafruit_mpu6050
from bt_sender import BluetoothSender 

# Camera Imports
import io
import base64
try:
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
except ImportError:
    print("[WARN] picamera2 library not found. Camera disabled.")
    CAMERA_AVAILABLE = False

# ---------------------------------------------------------------
# MAX30102
# ---------------------------------------------------------------
def init_max30102():
    try:
        hr = HeartRateMonitor()
        hr.start_sensor()
        print("[OK] MAX30102 initialized")
        return hr
    except Exception as e:
        print("[ERR] MAX30102 init failed (will retry):", e)
        return None

# ---------------------------------------------------------------
# MPU6050 – Adafruit CircuitPython library
# ---------------------------------------------------------------
def init_mpu6050():
    try:
        # Re-initialize I2C to ensure clean bus state
        i2c = busio.I2C(board.SCL, board.SDA)
        mpu = adafruit_mpu6050.MPU6050(i2c)
        print("[OK] MPU6050 initialized (CircuitPython)")
        return mpu
    except Exception as e:
        print("[ERR] MPU init failed (will retry):", e)
        return None

# ---------------------------------------------------------------
# TF-Luna LiDAR
# ---------------------------------------------------------------
def init_lidar():
    try:
        lidar = TfLunaI2C()
        lidar.us = False
        print("[OK] TF-Luna initialized")
        return lidar
    except Exception as e:
        print("[ERR] TF-Luna init failed (will retry):", e)
        return None

# ---------------------------------------------------------------
# Pi Camera 3 (Picamera2)
# ---------------------------------------------------------------
def init_camera():
    if not CAMERA_AVAILABLE:
        return None
    
    try:
        picam2 = Picamera2()
        # Configure specifically for low bandwidth (Bluetooth)
        config = picam2.create_still_configuration(main={"size": (320, 240)})
        picam2.configure(config)
        picam2.start()
        print("[OK] Pi Camera 3 initialized (320x240)")
        return picam2
    except Exception as e:
        print("[ERR] Camera init failed (will retry):", e)
        return None

def capture_frame_base64(cam):
    """Captures a JPEG frame and returns a base64 string."""
    if cam is None:
        return ""
    
    try:
        stream = io.BytesIO()
        cam.capture_file(stream, format='jpeg')
        stream.seek(0)
        b64_bytes = base64.b64encode(stream.read())
        return b64_bytes.decode('utf-8')
    except Exception as e:
        print(f"[ERR] Camera capture error: {e}")
        # We raise the exception so the main loop knows to reset the camera
        raise e 

# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("Initializing sensors...")
    
    # Initial attempts
    mpu = init_mpu6050()
    lidar = init_lidar()
    hr = init_max30102()
    cam = init_camera()

    # Initialize Bluetooth - We generally want this to stay alive
    try:
        bt = BluetoothSender() 
        bt.start()
    except Exception as e:
        print(f"[FATAL] Bluetooth Init Failed: {e}")
        # If BT fails, we might still want to run to debug sensors, 
        # or exit. For now we continue.
        bt = None

    print("\n Loop starting. Hot-plugging enabled.\n")

    loop_count = 0 

    while True:
        loop_count += 1
        
        # ------------------------------------------------
        # 1. MAX30102 Handling
        # ------------------------------------------------
        bpm = 0
        
        # If sensor is missing, try to init
        if hr is None:
            hr = init_max30102()
            
        # If sensor exists, try to read
        if hr:
            try:
                bpm = hr.bpm
            except Exception as e:
                print(f"[READ ERR] MAX30102: {e}")
                hr = None # Force re-init next loop
                bpm = 0

        # ------------------------------------------------
        # 2. TF-Luna Handling
        # ------------------------------------------------
        distance = 0
        
        if lidar is None:
            lidar = init_lidar()
            
        if lidar:
            try:    
                lidar.read_data()
                distance = lidar.dist
            except Exception as e:
                print(f"[READ ERR] TF-Luna: {e}")
                lidar = None # Force re-init next loop
                distance = 0

        # ------------------------------------------------
        # 3. MPU6050 Handling
        # ------------------------------------------------
        accel = [0, 0, 0]
        gyro = [0, 0, 0]
        
        if mpu is None:
            mpu = init_mpu6050()
            
        if mpu:
            try:
                accel = mpu.acceleration
                gyro  = mpu.gyro
            except Exception as e:
                print(f"[READ ERR] MPU6050: {e}")
                mpu = None # Force re-init next loop
                accel = [0, 0, 0]
                gyro = [0, 0, 0]

        # ------------------------------------------------
        # 4. Camera Handling
        # ------------------------------------------------
        image_b64 = ""
        
        if cam is None and CAMERA_AVAILABLE:
            # Optional: Don't retry camera every single loop if it fails, 
            # as it is heavy. Only retry every 20 loops (approx 4 seconds)
            if loop_count % 20 == 0: 
                cam = init_camera()
        
        if cam:
            try:
                image_b64 = capture_frame_base64(cam)
            except Exception:
                print("[READ ERR] Camera lost.")
                cam = None # Force re-init
                image_b64 = ""

        # ------------------------------------------------
        # 5. Construct & Send Packet
        # ------------------------------------------------
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
                # We do NOT set bt = None here usually, as sockets might recover.
                # But if you want to force a BT restart, you could.

        # ------------------------------------------------
        # 6. Console Status
        # ------------------------------------------------
        print("-------------------------------------------------------")
        print(f"MAX30102 → BPM: {bpm} " + ("(Active)" if hr else "(OFFLINE)"))
        print(f"TF-Luna  → Dist: {distance} " + ("(Active)" if lidar else "(OFFLINE)"))
        if accel != [0,0,0]:
             print(f"MPU6050  → Accel: {accel}")
        else:
             print("MPU6050  → (OFFLINE)")

        if image_b64:
            print(f"Camera   → Sent Frame ({len(image_b64)} bytes)")
        
        # Short sleep to prevent CPU spamming if everything fails
        time.sleep(0.2)