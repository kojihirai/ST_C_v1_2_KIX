import serial
import time
from collections import deque
import statistics

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
WINDOW_SIZE = 100  # Number of samples to use for SPS calculation

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)  # Non-blocking mode
        time.sleep(2)  # Wait for connection to stabilize
        
        # Use deque for efficient rolling window of timestamps
        timestamps = deque(maxlen=WINDOW_SIZE)
        start_time = time.time()
        sample_count = 0
        
        print("Starting speed test...")
        print("Press Ctrl+C to stop and see results")
        
        while True:
            if ser.in_waiting:
                line = ser.readline()
                if line:
                    current_time = time.time()
                    timestamps.append(current_time)
                    sample_count += 1
                    
                    # Calculate and display SPS every 100 samples
                    if sample_count % 100 == 0:
                        if len(timestamps) > 1:
                            intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
                            avg_interval = statistics.mean(intervals)
                            current_sps = 1.0 / avg_interval if avg_interval > 0 else 0
                            print(f"\rCurrent SPS: {current_sps:.1f}", end="", flush=True)
            
            # Small sleep to prevent CPU hogging
            time.sleep(0.0001)
            
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