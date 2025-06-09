from pymodbus.client import ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

class LoadCellAmplifier:
    def __init__(self, port, baudrate=9600, slave_address=0x01, parity='N', stopbits=1, bytesize=8, timeout=1):
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=timeout
        )
        self.slave_address = slave_address
    
    def connect(self):
        if not self.client.connect():
            raise ConnectionError("Unable to connect to the Modbus device")
    
    def disconnect(self):
        self.client.close()

    def read_data_register(self, address):
        # Function code 0x03: Read data register
        result = self.client.read_holding_registers(address=address, count=1, unit=self.slave_address)
        if not result.isError():
            return result.registers[0]
        else:
            raise Exception(f"Error reading register at address {address}: {result}")
    
    def modify_switch_value(self, address, value):
        # Function code 0x05: Modify switch value (Quickly modify switch value)
        result = self.client.write_coil(address, value, slave=self.slave_address)
        if result.isError():
            raise Exception(f"Error modifying switch value at address {address}: {result}")

    def modify_data_register(self, start_address, values):
        # Function code 0x10: Modify multi-bit data register value
        builder = BinaryPayloadBuilder(byteorder=Endian.Big)
        for value in values:
            builder.add_16bit_int(value)
        
        payload = builder.to_registers()
        result = self.client.write_registers(start_address, payload, slave=self.slave_address)
        if result.isError():
            raise Exception(f"Error modifying data register at address {start_address}: {result}")
    
    def zero_calibration(self):
        # Write zero calibration value (Address 0x00H, Function code 0x03 or 0x10)
        self.modify_data_register(0x00, [0x0000])

    def set_baud_rate(self, rate):
        # Set baud rate (Address 0x18H, Function code 0x03 or 0x10)
        baud_rate_mapping = {4800: 1, 9600: 2, 19200: 3}
        if rate not in baud_rate_mapping:
            raise ValueError("Invalid baud rate. Choose from 4800, 9600, or 19200.")
        
        self.modify_data_register(0x18, [baud_rate_mapping[rate]])

    def restore_factory_settings(self):
        # Restore factory setting (Address 0x03H, Function code 0x05 or 0x10, write FF)
        self.modify_switch_value(0x03, True)  # Writing FF as True in this context

    def clear_display_value(self):
        # Clear display value (Address 0x00H, Function code 0x05 or 0x10, write FF)
        self.modify_switch_value(0x00, True)  # Writing FF as True in this context
    
    def read_weight_value(self):
        # Current weight value (Address 0x00H, Function code 0x03)
        return self.read_data_register(0x00)

# Example usage:
if __name__ == "__main__":
    try:
        load_cell = LoadCellAmplifier(port='/dev/ttyUSB0', baudrate=9600, slave_address=0x01)
        load_cell.connect()
        
        # Reading current weight value
        weight = load_cell.read_weight_value()
        print(f"Current Weight: {weight}")
        
        load_cell.disconnect()
    except Exception as e:
        print(f"Error: {e}")
