#!/usr/bin/env python3
"""
Simple GPIO Tester for Contactor Control
Enables GPIO 4 for contactor operation - ON/OFF only
"""

import RPi.GPIO as GPIO
import time
import sys
import signal

# GPIO Configuration
CONTACTOR_GPIO = 4  # GPIO pin for contactor control

class ContactorTester:
    def __init__(self, gpio_pin=CONTACTOR_GPIO):
        self.gpio_pin = gpio_pin
        self.setup_gpio()
        
    def setup_gpio(self):
        """Initialize GPIO for contactor control"""
        try:
            # Set GPIO mode to BCM numbering
            GPIO.setmode(GPIO.BCM)
            
            # Set GPIO pin as output
            GPIO.setup(self.gpio_pin, GPIO.OUT, initial=GPIO.LOW)
            
            print(f"✓ GPIO {self.gpio_pin} initialized for contactor control")
            
        except Exception as e:
            print(f"✗ Error setting up GPIO: {e}")
            sys.exit(1)
    
    def enable_contactor(self):
        """Turn contactor ON"""
        try:
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            print(f"✓ Contactor ON - GPIO {self.gpio_pin} HIGH")
        except Exception as e:
            print(f"✗ Error enabling contactor: {e}")
    
    def disable_contactor(self):
        """Turn contactor OFF"""
        try:
            GPIO.output(self.gpio_pin, GPIO.LOW)
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
            GPIO.cleanup()
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
    
    print("🔌 Simple GPIO Contactor Tester")
    print("=" * 40)
    
    # Initialize tester
    tester = ContactorTester()
    
    try:
        # Test 1: Basic ON/OFF
        print("\n📋 Test 1: Basic Contactor Control")
        tester.test_contactor(duration=3)
        
        # Test 2: Pulse test
        print("\n📋 Test 2: Pulse Test")
        tester.pulse_test(pulses=3, on_time=0.5, off_time=0.5)
        
        # Test 3: Manual control demo
        print("\n📋 Test 3: Manual Control Demo")
        print("Contactor will be ON for 5 seconds...")
        tester.enable_contactor()
        time.sleep(5)
        tester.disable_contactor()
        
        print("\n✅ All tests completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
    finally:
        # Cleanup
        tester.cleanup()

if __name__ == "__main__":
    main()
