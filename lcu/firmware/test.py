import pigpio
import time
import threading
import signal
import sys
import math

# GPIO Pin Assignments
RPWM = 12
LPWM = 13
REN = 23
LEN = 24
ENC_A = 5
ENC_B = 6

# Constants
PULSES_PER_MM = 33
PWM_FREQ = 20000
SPEED_SAMPLE_INTERVAL_MS = 50
MAX_SPEED_MMPS = 10
SPEED_WINDOW = 10
INTEGRAL_MAX = 5.0
INTEGRAL_MIN = -5.0
DUTY_MIN = 5.0
DUTY_MAX = 100.0
ERROR_TOLERANCE = 0.002

# Globals
position = 0
offset = 0
running = True
user_speed = 0.0
user_direction = 1
user_stop = False
pi = pigpio.pi()

# Encoder callback
def encoder_callback(gpio, level, tick):
    global position
    A = pi.read(ENC_A)
    B = pi.read(ENC_B)
    delta = 0

    if gpio == ENC_A:
        delta = -1 if A == B else 1
    elif gpio == ENC_B:
        delta = -1 if A != B else 1

    position += delta

def get_position_ticks():
    return position - offset

def get_speed_mmps(prev_ticks, new_ticks, dt_sec):
    return (new_ticks - prev_ticks) / PULSES_PER_MM / dt_sec

def stop_motor():
    pi.hardware_PWM(RPWM, 0, 0)
    pi.hardware_PWM(LPWM, 0, 0)
    pi.write(REN, 1)
    pi.write(LEN, 1)

def set_motor_pwm(duty_percent, direction):
    duty = int(1_000_000 * duty_percent / 100)
    pi.write(REN, 1)
    pi.write(LEN, 1)
    if direction < 0:
        pi.hardware_PWM(RPWM, 0, 0)
        pi.hardware_PWM(LPWM, PWM_FREQ, duty)
    else:
        pi.hardware_PWM(LPWM, 0, 0)
        pi.hardware_PWM(RPWM, PWM_FREQ, duty)

def speed_control_loop():
    global user_speed
    duty = 30.0
    tick_history = [get_position_ticks()] * SPEED_WINDOW
    index = 0
    dt = SPEED_SAMPLE_INTERVAL_MS / 1000.0

    Kp = 8.0
    Ki = 1.0
    Kd = 0.3
    integral = 0.0
    prev_error = 0.0

    while running:
        if user_stop or user_speed <= 0.0:
            stop_motor()
            time.sleep(dt)
            continue

        time.sleep(dt)
        curr_ticks = get_position_ticks()
        avg_speed = get_speed_mmps(tick_history[index], curr_ticks, dt * SPEED_WINDOW)
        tick_history[index] = curr_ticks
        index = (index + 1) % SPEED_WINDOW

        error = user_speed - avg_speed
        if abs(error) < ERROR_TOLERANCE:
            error = 0.0
            integral *= 0.90
        else:
            integral += error * dt

        integral = max(min(integral, INTEGRAL_MAX), INTEGRAL_MIN)
        derivative = (error - prev_error) / dt
        prev_error = error

        raw_adjustment = Kp * error + Ki * integral + Kd * derivative
        target_duty = duty + raw_adjustment
        max_step = 0.3
        target_duty = max(min(target_duty, duty + max_step), duty - max_step)

        duty = max(min(target_duty, DUTY_MAX), DUTY_MIN)
        set_motor_pwm(duty, user_direction)

        print(f"Target: {user_speed:.2f} mm/s | Speed: {avg_speed:.3f} mm/s | PWM: {duty:.2f}%")

def home(speed_percent=50, timeout_sec=15):
    global offset
    print("=== Homing (retracting) ===")
    check_interval = 0.01
    required_still_cycles = 50
    still_counter = 0
    last_pos = position
    start = time.time()

    set_motor_pwm(speed_percent, -1)

    while time.time() - start < timeout_sec:
        time.sleep(check_interval)
        curr_pos = position
        delta = abs(curr_pos - last_pos)

        print(f"  Homing... encoder: {curr_pos} | delta: {delta}")
        if delta == 0:
            still_counter += 1
        else:
            still_counter = 0
        last_pos = curr_pos

        if still_counter >= required_still_cycles:
            print("Encoder stable — assuming hard stop.")
            break

    stop_motor()
    time.sleep(0.3)
    if abs(position - last_pos) > 0:
        print("Movement detected after stop. Retrying...")
        return home(speed_percent, timeout_sec)

    offset = position
    print(f"[HOME] Final encoder ticks: {offset}")
    print("Homing complete. Encoder virtual zero set.")

def shutdown_all(signum=None, frame=None):
    global running
    running = False
    stop_motor()
    pi.stop()
    print("Shutdown complete")
    sys.exit(0)

def main():
    global running, user_speed, user_stop
    signal.signal(signal.SIGINT, shutdown_all)

    pi.set_mode(RPWM, pigpio.OUTPUT)
    pi.set_mode(LPWM, pigpio.OUTPUT)
    pi.set_mode(REN, pigpio.OUTPUT)
    pi.set_mode(LEN, pigpio.OUTPUT)
    pi.set_mode(ENC_A, pigpio.INPUT)
    pi.set_mode(ENC_B, pigpio.INPUT)
    pi.set_pull_up_down(ENC_A, pigpio.PUD_UP)
    pi.set_pull_up_down(ENC_B, pigpio.PUD_UP)
    pi.callback(ENC_A, pigpio.EITHER_EDGE, encoder_callback)
    pi.callback(ENC_B, pigpio.EITHER_EDGE, encoder_callback)

    home(50, 15)
    time.sleep(1)

    thread = threading.Thread(target=speed_control_loop)
    thread.start()

    while running:
        try:
            cmd = input("Enter command (speed <val>, stop, quit): ").strip()
            if cmd.startswith("quit"):
                running = False
            elif cmd.startswith("stop"):
                user_stop = True
            elif cmd.startswith("speed"):
                parts = cmd.split()
                if len(parts) == 2:
                    user_speed = float(parts[1])
                    user_stop = False
        except Exception as e:
            print("Error:", e)

    thread.join()
    shutdown_all()

if __name__ == "__main__":
    main()
