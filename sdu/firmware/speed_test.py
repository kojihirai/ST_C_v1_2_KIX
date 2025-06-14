import serial
import time
from collections import deque
import os
import struct

# Optional: set process to high priority
try:
    os.nice(-20)
except PermissionError:
    pass

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 2000000
WINDOW_SIZE = 100
MESSAGE_SIZE = 6  # 3 x int16
BATCH_SIZE = 100
AMP_SCALE = 100.0

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

        while True:
            if ser.in_waiting >= MESSAGE_SIZE * BATCH_SIZE:
                data = ser.read(MESSAGE_SIZE * BATCH_SIZE)
                current_time = time.time()

                for i in range(0, len(data), MESSAGE_SIZE):
                    message = data[i:i+MESSAGE_SIZE]
                    if len(message) == MESSAGE_SIZE:
                        raw_drill, raw_power, raw_linear = struct.unpack('<hhh', message)
                        # Optional conversion (not used here to save time):
                        # drill = raw_drill / AMP_SCALE
                        # power = raw_power / AMP_SCALE
                        # linear = raw_linear / AMP_SCALE
                        timestamps.append(current_time)
                        sample_count += 1

    except KeyboardInterrupt:
        duration = time.time() - start_time
        avg_sps = sample_count / duration if duration > 0 else 0
        print(f"\nStopped. Total samples: {sample_count}")
        print(f"Duration: {duration:.3f} sec")
        print(f"Average SPS: {avg_sps:.1f}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
