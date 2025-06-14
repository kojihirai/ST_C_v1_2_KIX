import serial
import time
from collections import deque
import statistics
import os
import struct

# Set max process priority (requires sudo for effect)
try:
    os.nice(-20)
except PermissionError:
    pass

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 6000000
WINDOW_SIZE = 100
PACKET_SIZE = 7
BATCH_SIZE = 100
AMP_SCALE = 100.0
SYNC_BYTE = 0x0A  # ASCII '\n'

def main():
    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=0,
            write_timeout=0,
            inter_byte_timeout=None,
            exclusive=True
        )

        timestamps = deque(maxlen=WINDOW_SIZE)
        start_time = time.time()
        sample_count = 0
        last_print_time = start_time
        last_values = None

        print("Starting high-speed serial test... Press Ctrl+C to stop")

        while True:
            if ser.in_waiting >= PACKET_SIZE * BATCH_SIZE:
                data = ser.read(PACKET_SIZE * BATCH_SIZE)
                now = time.time()

                for i in range(0, len(data), PACKET_SIZE):
                    msg = data[i:i+PACKET_SIZE]
                    if len(msg) == PACKET_SIZE and msg[-1] == SYNC_BYTE:
                        raw_drill, raw_power, raw_linear = struct.unpack('<hhh', msg[:-1])
                        drill = raw_drill / AMP_SCALE
                        power = raw_power / AMP_SCALE
                        linear = raw_linear / AMP_SCALE

                        timestamps.append(now)
                        sample_count += 1
                        last_values = (drill, power, linear)

                if now - last_print_time >= 0.1:
                    if len(timestamps) > 1:
                        dt = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
                        avg_dt = statistics.mean(dt)
                        sps = 1.0 / avg_dt if avg_dt > 0 else 0
                        d, p, l = last_values
                        print(f"\rSPS: {sps:.1f} | Drill: {d:.2f}A Power: {p:.2f}A Linear: {l:.2f}A", end='', flush=True)
                    last_print_time = now

            time.sleep(0.000001)

    except serial.SerialException as e:
        print(f"\nSerial error: {e}")
    except KeyboardInterrupt:
        print("\n\nTest stopped by user")
        if sample_count:
            duration = time.time() - start_time
            print(f"Total Samples: {sample_count}")
            print(f"Duration: {duration:.2f} s")
            print(f"Average SPS: {sample_count / duration:.1f}")
            if last_values:
                d, p, l = last_values
                print(f"Last values — Drill: {d:.2f}A Power: {p:.2f}A Linear: {l:.2f}A")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
