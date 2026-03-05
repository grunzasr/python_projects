import serial
import serial.tools.list_ports
import threading
import time
import random
import re

class RS485Benchmark:
    def __init__(self, s_port, r_port, baud, kb_size, sw_delay, log_callback):
        self.s_port = s_port
        self.r_port = r_port
        self.baud = baud
        self.total_target_data = kb_size * 1024
        self.sw_delay = sw_delay
        self.log_callback = log_callback
        self.error_count = 0
        self.bytes_verified = 0

    @staticmethod
    def calculate_crc(data: bytes) -> bytes:
        """Standard Modbus CRC-16 (LITTLE ENDIAN)"""
        crc = 0xFFFF
        for pos in data:
            crc ^= pos
            for _ in range(8):
                if (crc & 0x0001) != 0:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc.to_bytes(2, byteorder='little')

    def send_modbus_preset(self, address=1, register=50000, value=100):
        try:
            ser_send = serial.Serial(self.s_port, self.baud, timeout=0.1)
            ser_recv = serial.Serial(self.r_port, self.baud, timeout=0.1)
            
            payload = bytearray([address, 0x06])
            payload.extend(register.to_bytes(2, 'big'))
            payload.extend(value.to_bytes(2, 'big'))
            
            full_packet = payload + self.calculate_crc(payload)
            self.log_callback(f"MODBUS TX: {full_packet.hex(' ').upper()}")
            
            start_time = time.perf_counter()
            ser_send.dtr = True
            time.sleep(self.sw_delay)
            ser_send.write(full_packet)
            ser_send.flush()
            time.sleep(self.sw_delay)
            ser_send.dtr = False
            
            received = b""
            timeout = time.time() + 1.5
            while time.time() < timeout:
                if ser_recv.in_waiting:
                    received += ser_recv.read(ser_recv.in_waiting)
                    if len(received) >= 8: break
            
            latency = (time.perf_counter() - start_time) * 1000
            if received[:8] == full_packet:
                self.log_callback(f"SUCCESS: Received in {latency:.2f}ms")
            else:
                self.log_callback(f"FAILED: Mismatch. Got: {received.hex(' ').upper()}")

            ser_send.close() ; ser_recv.close()
        except Exception as e:
            self.log_callback(f"Modbus Error: {str(e)}")

    def run(self):
        try:
            ser_send = serial.Serial(self.s_port, self.baud, timeout=0.1)
            ser_recv = serial.Serial(self.r_port, self.baud, timeout=0.1)
            ser_send.dtr = False ; ser_recv.dtr = False
            
            data_pool = b"RS485_LINUX_WIN_TEST_" * (self.total_target_data // 10)
            bytes_sent = 0
            self.bytes_verified = 0
            self.error_count = 0

            def receiver_worker():
                start_listen = time.time()
                while self.bytes_verified < self.total_target_data:
                    if time.time() - start_listen > 10: break
                    if ser_recv.in_waiting >= 3:
                        raw_packet = ser_recv.read(ser_recv.in_waiting)
                        if len(raw_packet) >= 3:
                            payload = raw_packet[:-2]
                            if raw_packet[-2:] == self.calculate_crc(payload):
                                self.bytes_verified += len(payload)
                                start_listen = time.time()
                            else:
                                self.error_count += 1

            recv_thread = threading.Thread(target=receiver_worker, daemon=True)
            recv_thread.start()

            start_time = time.time()
            while bytes_sent < self.total_target_data:
                chunk_len = min(random.randint(1, 80), self.total_target_data - bytes_sent)
                payload = data_pool[bytes_sent : bytes_sent + chunk_len]
                packet = payload + self.calculate_crc(payload)

                ser_send.dtr = True
                time.sleep(self.sw_delay)
                ser_send.write(packet)
                ser_send.flush()
                time.sleep(self.sw_delay)
                ser_send.dtr = False
                bytes_sent += chunk_len
                
            recv_thread.join(timeout=2)
            duration = time.time() - start_time
            self.log_callback(f"Done. Speed: {(self.bytes_verified*8/duration)/1000:.2f} kbps")

            ser_send.close() ; ser_recv.close()
        except Exception as e:
            self.log_callback(f"Engine Error: {str(e)}")

def get_available_ports():
    ports = list(serial.tools.list_ports.comports())
    def get_num(p):
        # Handles COM1, /dev/ttyUSB0, /dev/ttyS10 etc.
        match = re.search(r'\d+', p.device)
        return int(match.group()) if match else 0
    ports.sort(key=get_num)
    
    results = []
    for p in ports:
        desc = f"{p.device}: {p.description} [{p.hwid}]"
        is_ftdi = any(x in p.description.upper() or x in p.hwid.upper() 
                     for x in ["FTDI", "0403", "FUTURE TECHNOLOGY"])
        results.append({"text": desc, "is_ftdi": is_ftdi})
    return results