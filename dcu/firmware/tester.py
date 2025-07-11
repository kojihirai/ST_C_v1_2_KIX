#!/usr/bin/env python3
"""
Simple GPIO Tester for Contactor Control
Enables GPIO 4 for contactor operation - ON/OFF only
Uses pigpio library
"""

import pigpio
import time
import sys
import signal

# GPIO Configuration
CONTACTOR_GPIO = 27  # GPIO pin for contactor control

class ContactorTester:
    def __init__(self, gpio_pin=CONTACTOR_GPIO):
        self.gpio_pin = gpio_pin
        self.pi = None
        self.setup_gpio()
        
    def setup_gpio(self):
        """Initialize GPIO for contactor control"""
        try:
            # Initialize pigpio
            self.pi = pigpio.pi()
            
            if not self.pi.connected:
                print("✗ Failed to connect to pigpiod daemon")
                print("Make sure pigpiod is running: sudo pigpiod")
                sys.exit(1)
            
            # Set GPIO pin as output
            self.pi.set_mode(self.gpio_pin, pigpio.OUTPUT)
            self.pi.write(self.gpio_pin, 0)  # Start with LOW
            
            print(f"✓ GPIO {self.gpio_pin} initialized for contactor control")
            
        except Exception as e:
            print(f"✗ Error setting up GPIO: {e}")
            sys.exit(1)
    
    def enable_contactor(self):
        """Turn contactor ON"""
        try:
            self.pi.write(self.gpio_pin, 1)
            print(f"✓ Contactor ON - GPIO {self.gpio_pin} HIGH")
        except Exception as e:
            print(f"✗ Error enabling contactor: {e}")
    
    def disable_contactor(self):
        """Turn contactor OFF"""
        try:
            self.pi.write(self.gpio_pin, 0)
            print(f"✓ Contactor OFF - GPIO {self.gpio_pin} LOW")
        except Exception as e:
            print(f"✗ Error disabling contactor: {e}")
    
    def test_contactor(self, duration=2):
        """Test contactor operation for specified duration"""
        print(f"\n🧪 Testing contactor on GPIO {self.gpio_pin}")
        print(f"Duration: {duration} seconds")
        
        try:
            # Turn ON
            self.enable_contactor()
            time.sleep(duration)
            
            # Turn OFF
            self.disable_contactor()
            
            print("✓ Contactor test completed successfully")
            
        except Exception as e:
            print(f"✗ Error during contactor test: {e}")
    
    def pulse_test(self, pulses=3, on_time=0.5, off_time=0.5):
        """Test contactor with multiple pulses"""
        print(f"\n⚡ Pulse testing contactor on GPIO {self.gpio_pin}")
        print(f"Pulses: {pulses}, On time: {on_time}s, Off time: {off_time}s")
        
        try:
            for i in range(pulses):
                print(f"Pulse {i+1}/{pulses}")
                self.enable_contactor()
                time.sleep(on_time)
                self.disable_contactor()
                time.sleep(off_time)
            
            print("✓ Pulse test completed successfully")
            
        except Exception as e:
            print(f"✗ Error during pulse test: {e}")
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            if self.pi:
                self.pi.stop()
            print("✓ GPIO cleanup completed")
        except Exception as e:
            print(f"✗ Error during cleanup: {e}")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n⚠️  Interrupt received. Cleaning up...")
    if 'tester' in globals():
        tester.disable_contactor()
        tester.cleanup()
    sys.exit(0)

def main():
    """Main function to run contactor tests"""
    global tester
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🔌 Simple GPIO Contactor Tester (pigpio)")
    print("=" * 40)
    
    # Initialize tester
    tester = ContactorTester()
    
    try:
        print("\n📋 Contactor Test: ON for 5 seconds, then OFF")
        print("Contactor will be ON for 5 seconds...")
        tester.enable_contactor()
        time.sleep(5)
        tester.disable_contactor()
        
        print("\n✅ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
    finally:
        # Cleanup
        tester.cleanup()

if __name__ == "__main__":
    main()
