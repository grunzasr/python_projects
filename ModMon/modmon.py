import sys
import re
import os
import time
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QComboBox, QPushButton, QTextEdit, 
                             QFileDialog, QMessageBox, QLabel, QMenu, QInputDialog,
                             QGroupBox)
from PySide6.QtGui import QAction, QColor, QStandardItemModel, QStandardItem, QIcon, QActionGroup
from PySide6.QtCore import Qt, QThread, Signal, Slot

APP_VERSION = "1.8.0"

class SerialWorker(QThread):
    data_received = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, port_name, config):
        super().__init__()
        self.port_name = port_name
        self.config = config
        self._run_flag = True
        self.serial_port = None

    def run(self):
        try:
            with serial.Serial(
                port=self.port_name, baudrate=self.config['baud'],
                bytesize=self.config['bytesize'], parity=self.config['parity'],
                stopbits=self.config['stopbits'], timeout=0.1
            ) as self.serial_port:
                self.data_received.emit(f"System: Connected to {self.port_name}...")
                while self._run_flag:
                    if self.serial_port.in_waiting > 0:
                        raw_data = self.serial_port.read(self.serial_port.in_waiting)
                        self.data_received.emit(f"RX: {raw_data.hex(' ').upper()}")
                    time.sleep(0.01)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def send_hex(self, hex_str):
        if self.serial_port and self.serial_port.is_open:
            try:
                clean_hex = hex_str.replace(" ", "")
                data = bytes.fromhex(clean_hex)
                self.serial_port.write(data)
                self.data_received.emit(f"TX: {hex_str.upper()}")
            except ValueError:
                self.error_occurred.emit("Invalid Hex string!")

    def stop(self):
        self._run_flag = False
        self.wait()

class ModbusMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"RS-485 Modbus Monitor - v{APP_VERSION}")
        self.resize(950, 700)
        
        self.worker = None
        self.serial_config = {
            'baud': 9600, 'bytesize': serial.EIGHTBITS,
            'parity': serial.PARITY_NONE, 'stopbits': serial.STOPBITS_ONE
        }
        
        # Presets now store Name and Hex
        self.presets = [
            {"name": "Read Reg 0", "hex": "01 03 00 00 00 01 84 0A"},
            {"name": "Button 2", "hex": ""},
            {"name": "Button 3", "hex": ""},
            {"name": "Button 4", "hex": ""}
        ] 

        icon_path = os.path.join(os.path.dirname(__file__), "Resources", "ModbusMonitor.ico")
        self.app_icon = QIcon(icon_path) if os.path.exists(icon_path) else None
        if self.app_icon: self.setWindowIcon(self.app_icon)

        self.setup_menu()
        self.setup_ui()
        
    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Save Log", self.save_log)
        file_menu.addAction("Exit", self.close)

        self.settings_menu = menubar.addMenu("&Settings")
        
        # Serial Settings
        baud_menu = self.settings_menu.addMenu("Baud Rate")
        baud_group = QActionGroup(self)
        for b in [9600, 19200, 38400, 115200]:
            act = QAction(str(b), self, checkable=True)
            if b == 9600: act.setChecked(True)
            act.triggered.connect(lambda chk, v=b: self.set_config('baud', v))
            baud_group.addAction(act); baud_menu.addAction(act)

        # Modbus Presets Configuration
        preset_menu = self.settings_menu.addMenu("Configure Buttons")
        for i in range(4):
            act = QAction(f"Configure Button {i+1}...", self)
            act.triggered.connect(lambda chk, idx=i: self.configure_preset(idx))
            preset_menu.addAction(act)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About", self.show_about)

    def configure_preset(self, index):
        # 1. Ask for Name
        new_name, ok1 = QInputDialog.getText(self, f"Button {index+1} Name", 
                                            "Enter display label:",
                                            text=self.presets[index]["name"])
        if not ok1: return

        # 2. Ask for Hex
        new_hex, ok2 = QInputDialog.getText(self, f"Button {index+1} Data", 
                                           "Enter Modbus Hex:",
                                           text=self.presets[index]["hex"])
        if ok2:
            self.presets[index]["name"] = new_name
            self.presets[index]["hex"] = new_hex
            # Update the button label on the UI immediately
            self.preset_btns[index].setText(new_name)
            self.log_display.append(f"System: Button {index+1} configured as '{new_name}'.")

    def set_config(self, key, value):
        self.serial_config[key] = value

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Top Bar
        port_layout = QHBoxLayout()
        self.port_selector = QComboBox()
        self.refresh_ports()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        port_layout.addWidget(QLabel("Port:"))
        port_layout.addWidget(self.port_selector, 1)
        port_layout.addWidget(self.connect_btn)
        port_layout.addWidget(QPushButton("Clear", clicked=self.clear_log))
        layout.addLayout(port_layout)

        # Monitor
        self.log_display = QTextEdit(readOnly=True)
        self.log_display.setStyleSheet("background-color: #1e1e1e; color: #00FF00; font-family: 'Consolas';")
        layout.addWidget(self.log_display)

        # Preset Buttons Row
        button_group = QGroupBox("Modbus Commands (TX)")
        btn_layout = QHBoxLayout(button_group)
        self.preset_btns = []
        for i in range(4):
            # Create button with the stored name
            btn = QPushButton(self.presets[i]["name"])
            btn.clicked.connect(lambda chk, idx=i: self.send_preset(idx))
            btn.setEnabled(False) 
            self.preset_btns.append(btn)
            btn_layout.addWidget(btn)
        layout.addWidget(button_group)

    def refresh_ports(self):
        self.port_selector.clear()
        model = QStandardItemModel()
        ports = sorted(serial.tools.list_ports.comports(), 
                       key=lambda p: [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', p.device)])
        for port in ports:
            item = QStandardItem(f"{port.device} | {port.description}")
            item.setData(port.device, Qt.UserRole)
            if "FTDI" in f"{port.description} {port.manufacturer}".upper():
                item.setForeground(QColor("green"))
            model.appendRow(item)
        self.port_selector.setModel(model)

    def send_preset(self, index):
        if self.worker and self.worker.isRunning():
            hex_str = self.presets[index]["hex"]
            if hex_str.strip():
                self.worker.send_hex(hex_str)
            else:
                self.log_display.append(f"Error: Button '{self.presets[index]['name']}' has no hex data.")

    def toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.connect_btn.setText("Connect")
            self.port_selector.setEnabled(True)
            for b in self.preset_btns: b.setEnabled(False)
        else:
            idx = self.port_selector.currentIndex()
            if idx < 0: return
            port_name = self.port_selector.model().item(idx).data(Qt.UserRole)
            self.worker = SerialWorker(port_name, self.serial_config)
            self.worker.data_received.connect(self.log_display.append)
            self.worker.error_occurred.connect(lambda e: QMessageBox.critical(self, "Error", e))
            self.worker.start()
            self.connect_btn.setText("Disconnect")
            self.port_selector.setEnabled(False)
            for b in self.preset_btns: b.setEnabled(True)

    def clear_log(self):
        self.log_display.clear()

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "Text Files (*.txt)")
        if path:
            with open(path, 'w') as f: f.write(self.log_display.toPlainText())

    def show_about(self):
        QMessageBox.about(self, "About", f"Modbus Monitor v{APP_VERSION}")

    def closeEvent(self, event):
        if self.worker: self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModbusMonitor()
    window.show()
    sys.exit(app.exec())