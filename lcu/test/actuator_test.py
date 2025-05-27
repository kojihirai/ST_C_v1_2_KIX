import time
import pigpio

MOTOR1_PINS = {"RPWM": 12, "LPWM": 13, "REN": 23, "LEN": 24}
MOTOR2_PINS = {"RPWM": 18, "LPWM": 19, "REN": 25, "LEN": 26}

pi = pigpio.pi()
if not pi.connected:
    raise Exception("Could not connect to pigpio daemon")

for pin in list(MOTOR1_PINS.values()) + list(MOTOR2_PINS.values()):
    pi.set_mode(pin, pigpio.OUTPUT)
    pi.write(pin, 0)

pi.write(MOTOR1_PINS["REN"], 1)
pi.write(MOTOR1_PINS["LEN"], 1)
pi.write(MOTOR2_PINS["REN"], 1)
pi.write(MOTOR2_PINS["LEN"], 1)

def move_motor(pins, speed):
    """Move motor with given pins and speed (-100 to 100)"""
    speed = max(min(speed, 100), -100)
    pwm = int(abs(speed) * 2.55)

    if speed > 0:
        pi.set_PWM_dutycycle(pins["RPWM"], pwm)
        pi.set_PWM_dutycycle(pins["LPWM"], 0)
    elif speed < 0:
        pi.set_PWM_dutycycle(pins["RPWM"], 0)
        pi.set_PWM_dutycycle(pins["LPWM"], pwm)
    else:
        pi.set_PWM_dutycycle(pins["RPWM"], 0)
        pi.set_PWM_dutycycle(pins["LPWM"], 0)

try:
    print("Moving both motors backward...")
    move_motor(MOTOR1_PINS, -50)
    move_motor(MOTOR2_PINS, -50)
    time.sleep(2)

    print("Moving both motors forward...")
    move_motor(MOTOR1_PINS, 50)
    move_motor(MOTOR2_PINS, 50)
    time.sleep(2)

    print("Stopping both motors...")
    move_motor(MOTOR1_PINS, 0)
    move_motor(MOTOR2_PINS, 0)

finally:
    for pin_set in [MOTOR1_PINS, MOTOR2_PINS]:
        pi.set_PWM_dutycycle(pin_set["RPWM"], 0)
        pi.set_PWM_dutycycle(pin_set["LPWM"], 0)
        pi.write(pin_set["REN"], 0)
        pi.write(pin_set["LEN"], 0)
    pi.stop()
