import time
from smbus import SMBus

class TfLunaI2C:
    """
    TfLunaI2C class functions as the i2c driver for the TF-Luna Lidar distance
    """
    DEFAULT_I2C_ADDR = 0x10
    
    # Register Names
    DIST_LO = 0x00
    AMP_LO = 0x02
    TEMP_LO = 0x04
    TICK_LO = 0x06
    ERROR_LO = 0x08
    VERSION_MAJOR = 0x0C
    FPS_LO = 0x26
    SAVE_SETTINGS = 0x20
    REBOOT = 0x21
    
    # Commands
    COMMIT = 0x01
    REBOOT_CODE = 0x02
    TRUE = 0x01
    FALSE = 0x00

    def __init__(self, address=DEFAULT_I2C_ADDR, us=True, bus=1):
        self.address = address
        self.us = us
        self.dist = 0
        self.amp = 0
        self.bus = bus
        self.i2cbus = SMBus(self.bus)
        
        # We attempt to load settings. If device is missing, this will fail 
        # (which is good, so the main script knows it's offline).
        self._load_settings()

    def _read_word(self, register):
        # We do NOT catch exceptions here. Let them bubble up.
        return self.i2cbus.read_word_data(self.address, register)

    def _write_word(self, register, data):
        self.i2cbus.write_word_data(self.address, register, data)

    def _read_byte(self, register):
        return self.i2cbus.read_byte_data(self.address, register)

    def _write_byte(self, register, data):
        self.i2cbus.write_byte_data(self.address, register, data)

    def read_data(self):
        """
        Reads data set from device.
        """
        # This will throw an OSError if the wire is disconnected
        distance = self._read_word(self.DIST_LO)
        amplitude = self._read_word(self.AMP_LO)
        
        # Filter obvious garbage data
        if distance > 1200: 
            distance = 0
            
        self.dist = distance
        self.amp = amplitude
        return [self.dist, self.amp]

    def _load_settings(self):
        # Just read the FPS to verify connection
        self.read_frame_rate()

    def read_frame_rate(self):
        return self._read_word(self.FPS_LO)
    
    # Helper properties required by your script
    @property
    def distance(self):
        return self.dist

    # Static conversions if needed
    @staticmethod
    def centimeters2feet(cm):
        return cm * 0.032808398950131

    @staticmethod
    def celsius2fahrenheit(celsius):
        return (1.8 * celsius) + 32.0