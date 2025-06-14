import serial
import time
from collections import deque
import os
import struct

# Optional: set high priority
try:
    os.nice(-20)
except PermissionError:
    pass

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 2000000
WINDOW_SIZE = 100
FRAME_SIZE = 25              # 1 sync + 4 samples * 6 bytes
SAMPLES_PER_FRAME = 4
BATCH_SIZE = 100             # Number of frames to read at once

def find_sync(data):
    for i in range(len(data) - FRAME_SIZE + 1):
        if data[i] == 0xAA:
            return i
    return -1

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

        print("Reading... Press Ctrl+C to stop")

        while True:
            if ser.in_waiting >= FRAME_SIZE * BATCH_SIZE:
                raw = ser.read(FRAME_SIZE * BATCH_SIZE)
                i = 0

                while i <= len(raw) - FRAME_SIZE:
                    if raw[i] == 0xAA:
                        payload = raw[i+1:i+25]
                        if len(payload) == 24:
                            for j in range(0, 24, 6):
                                sample = payload[j:j+6]
                                if len(sample) == 6:
                                    raw_drill, raw_power, raw_linear = struct.unpack('<hhh', sample)
                                    # Optionally scale here
                                    timestamps.append(time.time())
                                    sample_count += 1
                        i += FRAME_SIZE
                    else:
                        i += 1  # Sync byte not found, resync
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
