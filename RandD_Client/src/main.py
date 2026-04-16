import asyncio
import struct
from bleak import BleakClient, BleakScanner

# Replace these with your actual UUIDs from the firmware
SERVICE_UUID  = "0000fe40-cc7a-482a-984a-7f2ed5b3e58f"
ADC_CHAR_UUID = "0000fe41-8e22-4541-9d4c-21edae82ed19" # 32 bytes
LED_CHAR_UUID = "0000fe42-8e22-4541-9d4c-21edae82ed19" # 5 bytes
PB_UUID       = "0000fe43-8e22-4541-9d4c-21edae82ed19"

MAX_MTU = 80

def adc_notification_handler(sender, data):
    """
    Unpacks 32 bytes into 16 uint16_t ADC values.
    '<' = little-endian, 'H' = unsigned short (2 bytes)
    """
    channels = struct.unpack('<16H', data)
    print(f"ADC Snapshot: {channels}")

async def main():
    deviceName = "P2PSRX1"
    print("Scanning for devices named ", deviceName, " ..." )
    device = await BleakScanner.find_device_by_name( deviceName )
    
    if not device:
        print("Device not found.")
        return

    async with BleakClient(device) as client:
        print(f"Connected to {device.address}")
        
        print(f"initial MTU: {client.mtu_size}")
        
        try:
            if hasattr(client, "request_mtu"):
                await client.request_mtu(MAX_MTU)
                print(f"Requested MTU change to {MAX_MTU}")
            else:
                print("Manual MTU request may not be supported on this platform")
        except Exception as e:
            print(f"Failed to request MTU: {e}")
            
        print(f"MTU size is now {client.mtu_size}")
        

        # 1. Read the 34 LED states (5 bytes)
        led_data = await client.read_gatt_char(LED_CHAR_UUID)
        
        print("Active LEDs:")
        for i in range(34):
            byte_idx = i // 8
            bit_idx = i % 8
            is_on = (led_data[byte_idx] >> bit_idx) & 1
            if is_on:
                print(f"  - LED {i} is ON")

        # 2. Start Notifications for ADC channels
        print("\nStarting ADC stream (Press Ctrl+C to stop)...")
        await client.start_notify(ADC_CHAR_UUID, adc_notification_handler)
        
        # Keep the script running to receive notifications
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Disconnecting...")