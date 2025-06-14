import serial
import time
from collections import deque
import statistics
import os
import struct
import numpy as np

# Set process priority to maximum (optional, needs sudo)
try:
    os.nice(-20)
except PermissionError:
    pass  # Not fatal if not run with sudo

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 6000000  # Updated to match teensy.ino
WINDOW_SIZE = 1000  # Increased for better statistics
PACKET_SIZE = 7  # 3 x int16 + 1 sync byte = 7 bytes
BATCH_SIZE = 1000  # Increased for better throughput
AMP_SCALE = 100.0  # Integer was scaled by 100 (0.01A resolution)
SYNC_BYTE = b'\n'  # Match the sync byte from teensy.ino

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
        values = deque(maxlen=WINDOW_SIZE)
        start_time = time.time()
        sample_count = 0
        last_print_time = start_time
        last_values = None
        min_interval = float('inf')
        max_interval = 0

        print("Starting speed test...")
        print("Press Ctrl+C to stop and see results")
        
        while True:
            if ser.in_waiting >= PACKET_SIZE * BATCH_SIZE:
                data = ser.read(PACKET_SIZE * BATCH_SIZE)
                current_time = time.time()
                
                # Process all packets in the batch
                for i in range(0, len(data), PACKET_SIZE):
                    message = data[i:i+PACKET_SIZE]
                    if len(message) == PACKET_SIZE and message[-1] == ord(SYNC_BYTE):
                        # Unpack as 3 signed int16s, ignoring the sync byte
                        raw_drill, raw_power, raw_linear = struct.unpack('<hhh', message[:-1])
                        drill = raw_drill / AMP_SCALE
                        power = raw_power / AMP_SCALE
                        linear = raw_linear / AMP_SCALE

                        timestamps.append(current_time)
                        values.append((drill, power, linear))
                        sample_count += 1
                        last_values = (drill, power, linear)
                
                if current_time - last_print_time >= 0.1:
                    if len(timestamps) > 1:
                        intervals = np.diff(list(timestamps))
                        avg_interval = np.mean(intervals)
                        std_interval = np.std(intervals)
                        min_interval = min(min_interval, np.min(intervals))
                        max_interval = max(max_interval, np.max(intervals))
                        current_sps = 1.0 / avg_interval if avg_interval > 0 else 0
                        
                        if last_values:
                            print(f"\rSPS: {current_sps:.1f} | "
                                  f"Jitter: {std_interval*1000:.1f}ms | "
                                  f"Min: {min_interval*1000:.1f}ms | "
                                  f"Max: {max_interval*1000:.1f}ms | "
                                  f"Drill: {last_values[0]:.2f}A | "
                                  f"Power: {last_values[1]:.2f}A | "
                                  f"Linear: {last_values[2]:.2f}A", 
                                  end="", flush=True)
                    last_print_time = current_time

            time.sleep(0.000001)  # Minimized delay for max responsiveness

    except serial.SerialException as e:
        print(f"\nSerial error: {e}")
    except KeyboardInterrupt:
        print("\n\nTest stopped by user")
        if sample_count > 0:
            duration = time.time() - start_time
            total_sps = sample_count / duration
            print(f"Total samples: {sample_count}")
            print(f"Duration: {duration:.1f} seconds")
            print(f"Average SPS: {total_sps:.1f}")
            print(f"Min interval: {min_interval*1000:.1f}ms")
            print(f"Max interval: {max_interval*1000:.1f}ms")
            if len(timestamps) > 1:
                intervals = np.diff(list(timestamps))
                print(f"Average interval: {np.mean(intervals)*1000:.1f}ms")
                print(f"Interval std dev: {np.std(intervals)*1000:.1f}ms")
            if last_values:
                print(f"Last values - Drill: {last_values[0]:.2f}A Power: {last_values[1]:.2f}A Linear: {last_values[2]:.2f}A")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
