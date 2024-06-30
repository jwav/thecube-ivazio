"""
A simple class to read and write to the GPIO pins of a Raspberry Pi using the RPi.GPIO library.
"""
from thecubeivazio.cube_utils import is_raspberry_pi

# if we're not on an rpi, we'll be using this mock class
if not is_raspberry_pi():
    class CubeGpio:
        @staticmethod
        def set_pin(pin: int, value: bool) -> bool:
            return True
        @staticmethod
        def read_pin(pin: int) -> bool:
            return False
        @staticmethod
        def cleanup():
            pass

else:
    # if we're on an rpi, we'll be using the RPi.GPIO library
    import RPi.GPIO as GPIO

    class CubeGpio:
        @staticmethod
        def set_pin(pin: int, value: bool) -> bool:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, value)
                return True
            except Exception as e:
                print(f"Error setting pin {pin} to {value}: {e}")
                return False

        @staticmethod
        def read_pin(pin: int) -> bool:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(pin, GPIO.IN)
                return GPIO.input(pin)
            except Exception as e:
                print(f"Error reading pin {pin}: {e}")
                return False

        @staticmethod
        def cleanup():
            GPIO.cleanup()
            print("GPIO.cleanup() called")