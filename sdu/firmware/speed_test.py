import serial
import time
from collections import deque
import statistics
import os

# Set process priority to maximum
os.nice(-20)  # Requires sudo privileges

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
WINDOW_SIZE = 100

def main():
    try:
        # Configure serial port for maximum performance
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=0,  # Non-blocking
            write_timeout=0,
            inter_byte_timeout=None,
            exclusive=True  # Exclusive access to port
        )
        
        # Use deque for efficient rolling window of timestamps
        timestamps = deque(maxlen=WINDOW_SIZE)
        start_time = time.time()
        sample_count = 0
        last_print_time = start_time
        
        print("Starting speed test...")
        print("Press Ctrl+C to stop and see results")
        
        while True:
            if ser.in_waiting:
                # Read all available data at once
                data = ser.read(ser.in_waiting)
                lines = data.split(b'\n')
                
                for line in lines:
                    if line:  # Skip empty lines
                        current_time = time.time()
                        timestamps.append(current_time)
                        sample_count += 1
                
                # Update display every 0.1 seconds instead of every 100 samples
                current_time = time.time()
                if current_time - last_print_time >= 0.1:
                    if len(timestamps) > 1:
                        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
                        avg_interval = statistics.mean(intervals)
                        current_sps = 1.0 / avg_interval if avg_interval > 0 else 0
                        print(f"\rCurrent SPS: {current_sps:.1f}", end="", flush=True)
                    last_print_time = current_time
            
            # Reduced sleep time for more frequent checks
            time.sleep(0.00001)
            
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
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main() 