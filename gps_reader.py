import serial
import pynmea2
import time

# Function to read and parse data from the GPS module
def read_gps_data():
    # The serial port may vary. '/dev/serial0' is common for Raspberry Pi hardware UART.
    # 9600 is a common baud rate for GPS modules.
    serial_port = "/dev/serial0"
    baud_rate = 9600

    try:
        # Open the serial port
        ser = serial.Serial(serial_port, baudrate=baud_rate, timeout=1)
        print(f"Serial port {serial_port} opened successfully.")
        
        while True:
            try:
                # Read a line of data from the serial port
                line = ser.readline().decode('utf-8', errors='ignore')

                # Check if the line contains NMEA data
                if line.startswith('$'):
                    # Parse the NMEA sentence
                    msg = pynmea2.parse(line)
                    
                    # We are interested in GGA messages, which contain fix data
                    if isinstance(msg, pynmea2.types.talker.GGA):
                        if msg.is_valid:
                            print(f"Timestamp: {msg.timestamp}")
                            print(f"Latitude: {msg.latitude:.6f} {msg.lat_dir}")
                            print(f"Longitude: {msg.longitude:.6f} {msg.lon_dir}")
                            print(f"Satellites: {msg.num_sats}")
                            print(f"Altitude: {msg.altitude} {msg.altitude_units}")
                            print("-" * 20)
                        else:
                            print("Waiting for a valid satellite fix...")
                
                time.sleep(0.5)

            except pynmea2.ParseError as e:
                # Handle cases where the NMEA sentence is malformed
                # print(f"Parse error: {e}")
                pass
            except UnicodeDecodeError:
                # Handle potential garbled data
                pass

    except serial.SerialException as e:
        print(f"Error: Could not open serial port {serial_port}. {e}")
    except KeyboardInterrupt:
        print("Program stopped by user.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    read_gps_data()
