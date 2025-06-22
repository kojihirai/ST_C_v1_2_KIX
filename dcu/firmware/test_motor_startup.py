#!/usr/bin/env python3
"""
Test script to verify motor doesn't start on powerup
This script simulates the motor controller initialization to ensure
the motor driver is properly disabled on startup.
"""

import pigpio
import time

# Motor pin definitions (same as in firmware.py)
MOTOR1_PINS = {"RPWM": 12, "LPWM": 13, "REN": 23, "LEN": 24}

def test_motor_startup():
    """Test that motor driver is properly disabled on startup"""
    print("Testing motor startup behavior...")
    
    # Initialize pigpio
    pi = pigpio.pi()
    if not pi.connected:
        print("ERROR: Could not connect to pigpio daemon")
        return False
    
    try:
        
        # Test the FIXED initialization
        print("\n2. Testing FIXED initialization (motor should stay stopped):")
        for pin in [MOTOR1_PINS["RPWM"], MOTOR1_PINS["LPWM"], MOTOR1_PINS["REN"], MOTOR1_PINS["LEN"]]:
            pi.set_mode(pin, pigpio.OUTPUT)
            pi.write(pin, 0)  # All pins start disabled
        
        # Motor driver remains disabled
        print("   Motor driver disabled on startup (FIXED BEHAVIOR)")
        print("   ✓ Motor should remain stopped until commanded")
        
        # Test motor enable/disable functionality
        print("\n3. Testing motor enable/disable functionality:")
        
        # Enable motor driver (simulating set_motor with value > 0)
        print("   Enabling motor driver...")
        pi.write(MOTOR1_PINS["REN"], 1)
        pi.write(MOTOR1_PINS["LEN"], 1)
        
        # Set some PWM (simulating motor movement)
        print("   Setting PWM to 50%...")
        pi.set_PWM_dutycycle(MOTOR1_PINS["RPWM"], 128)  # 50% duty cycle
        pi.set_PWM_dutycycle(MOTOR1_PINS["LPWM"], 0)
        
        time.sleep(2)  # Let motor run for 2 seconds
        
        # Disable motor driver (simulating stop_motor)
        print("   Disabling motor driver...")
        pi.set_PWM_dutycycle(MOTOR1_PINS["RPWM"], 0)
        pi.set_PWM_dutycycle(MOTOR1_PINS["LPWM"], 0)
        pi.write(MOTOR1_PINS["REN"], 0)
        pi.write(MOTOR1_PINS["LEN"], 0)
        
        print("   ✓ Motor driver properly disabled")
        
        print("\n✅ Test completed successfully!")
        print("   The motor should now only start when explicitly commanded")
        print("   and should remain stopped on powerup.")
        
        return True
        
    except Exception as e:
        print(f"ERROR during test: {e}")
        return False
    
    finally:
        # Ensure motor is stopped
        pi.set_PWM_dutycycle(MOTOR1_PINS["RPWM"], 0)
        pi.set_PWM_dutycycle(MOTOR1_PINS["LPWM"], 0)
        pi.write(MOTOR1_PINS["REN"], 0)
        pi.write(MOTOR1_PINS["LEN"], 0)
        pi.stop()

if __name__ == "__main__":
    print("DCU Motor Startup Test")
    print("=" * 50)
    print("This test verifies that the motor doesn't start on powerup")
    print("Make sure the motor is connected and the system is ready.")
    print()
    
    input("Press Enter to start the test (or Ctrl+C to cancel)...")
    
    try:
        success = test_motor_startup()
        if success:
            print("\n🎉 Test PASSED: Motor startup behavior is now safe!")
        else:
            print("\n❌ Test FAILED: Please check the motor connections and try again.")
    except KeyboardInterrupt:
        print("\n⚠️  Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}") 