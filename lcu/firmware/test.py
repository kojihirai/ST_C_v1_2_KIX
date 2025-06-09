#################################################
# LoadCell_Driver.py
#
# Driver for Load Cell Module
#
# Author: 
# Date: 2024-09-27

# Property of:
#
# Copyright (c) 2024, All rights reserved.
#################################################

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
import struct
import time

class LoadCellDriver:
    def __init__(self, port, baudrate, parity, stopbits, bytesize, timeout, slave_id):
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize
        )
        self.slave_id = slave_id
        self.connected = False

    def __del__(self):
        self.client.close()

    def connect(self):
        try:
            self.client.connect()
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        try:
            self.client.close()
            self.connected = False
            print("Successfully disconnected")
        except Exception as e:
            print(f"Failed to disconnect: {e}")

    def read_parameter(self, address, length=1, signed=False):
        try:
            # Read holding registers
            response = self.client.read_holding_registers(address, length)
            if not response.isError():
                if length == 1:
                    # 16-bit register
                    value = response.registers[0]
                    if signed:
                        value = struct.unpack('>h', struct.pack('>H', value))[0]
                elif length == 2:
                    # 32-bit register (combine two 16-bit registers)
                    value = (response.registers[0] << 16) | response.registers[1]
                    if signed:
                        value = struct.unpack('>i', struct.pack('>I', value))[0]

                print(f"Read value from address {hex(address)}: {value}")
                return value
            else:
                print(f"Failed to read parameter at address {hex(address)}")
                return None
        except ModbusException as e:
            print(f"ModbusException: Failed to read parameter at address {hex(address)}: {e}")
        except Exception as e:
            print(f"Unexpected error: Failed to read parameter at address {hex(address)}: {e}")
            return None

    def write_parameter(self, address, value):
        try:
            # Write single register
            response = self.client.write_register(address, value, slave=self.slave_id)
            if not response.isError():
                print(f"Successfully wrote value {value} to address {hex(address)}")
                return True
            else:
                print(f"Failed to write value {value} to address {hex(address)}")
                return False
        except ModbusException as e:
            print(f"ModbusException: Failed to write parameter at address {hex(address)}: {e}")
        except Exception as e:
            print(f"Unexpected error: Failed to write parameter at address {hex(address)}: {e}")
            return False

if __name__ == "__main__":
    modbus_control = LoadCellDriver("/dev/ttyUSB0", 9600, "N", 1, 8, 1, 1)
    modbus_control.connect()
    
    modbus_control.read_parameter(0x00, length=2, signed=True)
    time.sleep(0.1)
    
    modbus_control.disconnect()
