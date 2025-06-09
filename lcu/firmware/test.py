#################################################
# LoadCell_Driver.py
#
# Driver for Load Cell Module
#
# Author:
# Date: 2024-09-27
#
# Copyright (c) 2024, All rights reserved.
#################################################

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
import struct
import time

class LoadCellDriver:
    def __init__(self, port, baudrate, parity, stopbits, bytesize, timeout, slave_id, scale_factor=100):
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
        self.scale_factor = scale_factor

    def __del__(self):
        try:
            self.client.close()
        except:
            pass

    def connect(self):
        try:
            self.connected = self.client.connect()
            return self.connected
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
        """
        Reads `length` registers starting at `address`, unpacks as signed if requested,
        then divides by scale_factor to apply the 1/100 scaling.
        """
        if not self.connected:
            print("Not connected")
            return None

        try:
            response = self.client.read_holding_registers(address=address, count=length, slave=self.slave_id)
            if response.isError():
                print(f"Failed to read parameter at address {hex(address)}")
                return None

            # unpack raw value
            if length == 1:
                raw = response.registers[0]
                if signed:
                    raw = struct.unpack('>h', struct.pack('>H', raw))[0]
            else:  # length == 2
                raw = (response.registers[0] << 16) | response.registers[1]
                if signed:
                    raw = struct.unpack('>i', struct.pack('>I', raw))[0]

            scaled = raw / self.scale_factor
            print(f"Read {raw} from {hex(address)} → scaled: {scaled}")
            return scaled

        except ModbusException as e:
            print(f"ModbusException at {hex(address)}: {e}")
        except Exception as e:
            print(f"Unexpected error at {hex(address)}: {e}")
        return None

    def write_parameter(self, address, value):
        """
        Writes a single register. `value` should be the unscaled integer.
        """
        if not self.connected:
            print("Not connected")
            return False

        try:
            response = self.client.write_register(address, int(value), slave=self.slave_id)
            if response.isError():
                print(f"Failed to write {value} to {hex(address)}")
                return False
            print(f"Wrote {value} to {hex(address)}")
            return True

        except ModbusException as e:
            print(f"ModbusException at {hex(address)}: {e}")
        except Exception as e:
            print(f"Unexpected error at {hex(address)}: {e}")
        return False

if __name__ == "__main__":
    driver = LoadCellDriver(
        port="/dev/ttyUSB0",
        baudrate=9600,
        parity='N',
        stopbits=1,
        bytesize=8,
        timeout=1,
        slave_id=1,
        scale_factor=100  # divide raw readings by 100
    )
    if driver.connect():
        weight = driver.read_parameter(0x00, length=2, signed=True)
        print(f"Weight: {weight}")
        time.sleep(0.1)
        driver.disconnect()
