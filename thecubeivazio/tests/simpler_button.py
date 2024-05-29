import RPi.GPIO as GPIO
import time

BUTTON_PIN = 17

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def read_button_state():
    return GPIO.input(BUTTON_PIN)

def main():
    setup_gpio()
    try:
        while True:
            state = read_button_state()
            if state == GPIO.HIGH:
                print("Pin is HIGH")
            else:
                print("Pin is LOW")
            time.sleep(0.1)
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Exiting program")

if __name__ == "__main__":
    main()
