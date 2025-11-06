import serial
import struct
import time

ser = serial.Serial('/dev/serial0',115200,timeout=1)

while True:
    if ser.read() == b'Y' and ser.read() == b'Y':
        frame=ser.read(7)
        if len(frame) == 7:
            distance = frame[0] + frame[1]*256
            strength = frame[2] + frame[3]*256
            print(f"Distance: {distance} cm | Strength: {strength}")
    time.sleep(0.05)