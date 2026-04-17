import sys
import re
import os
import time
import json # Added for persistence
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QComboBox, QPushButton, QTextEdit, 
                             QFileDialog, QMessageBox, QLabel, QMenu, QInputDialog,
                             QGroupBox)
from PySide6.QtGui import QAction, QColor, QStandardItemModel, QStandardItem, QIcon, QActionGroup, QScreen, QCursor
from PySide6.QtCore import Qt, QThread, Signal, Slot, QPoint

APP_VERSION = "2.2.0"
# Formatted as an HTML link for clickability
GEMINI_INFO = '<a href="https://gemini.google.com/share/a92b0d141920">https://gemini.google.com/share/a92b0d141920</a>'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ICON_PATH = os.path.join(BASE_DIR, "Resources", "ModbusMonitor.ico")

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
            parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
            with serial.Serial(
                port=self.port_name, 
                baudrate=int(self.config['baud']),
                parity=parity_map.get(self.config['parity'], serial.PARITY_NONE),
                timeout=0.1
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
        
        # --- Handle Dynamic Sizing (80% of current monitor) ---
        self.apply_initial_geometry()
        
        self.worker = None
        self.load_settings()

        # Icon handling with explicit path check
        if os.path.exists(ICON_PATH):
            self.app_icon = QIcon(ICON_PATH)
            self.setWindowIcon(self.app_icon)
        else:
            self.app_icon = None
            print(f"Warning: Icon not found at {ICON_PATH}")

        self.setup_menu()
        self.setup_ui()
        
    def apply_initial_geometry(self):
        """Calculates 80% of the screen size where the app is launched."""
        # Get the screen where the mouse cursor is currently located
        # Get the current mouse pointer position
        cursor_pos = QCursor.pos()
        
        # Find the screen containing that position
        screen = QApplication.screenAt(cursor_pos)
        
        if not screen:
            screen = QApplication.primaryScreen()
            
        screen_geometry = screen.availableGeometry()
        
        # Calculate 80% of width and height
        width = int(screen_geometry.width() * 0.8)
        height = int(screen_geometry.height() * 0.8)
        
        # Center the window on that screen
        x = screen_geometry.x() + (screen_geometry.width() - width) // 2
        y = screen_geometry.y() + (screen_geometry.height() - height) // 2
        
        self.setGeometry(x, y, width, height)
        
    def load_settings(self):
        defaults = {
            "serial_config": {'baud': 9600, 'parity': 'N'},
            "presets": [
                {"name": "Read Reg 0", "hex": "01 03 00 00 00 01 84 0A"},
                {"name": "Button 2", "hex": ""},
                {"name": "Button 3", "hex": ""},
                {"name": "Button 4", "hex": ""}
            ]
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.serial_config = data.get("serial_config", defaults["serial_config"])
                    self.presets = data.get("presets", defaults["presets"])
            except Exception:
                self.serial_config = defaults["serial_config"]; self.presets = defaults["presets"]
        else:
            self.serial_config = defaults["serial_config"]; self.presets = defaults["presets"]

    def save_settings(self):
        data = {"serial_config": self.serial_config, "presets": self.presets}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Save Log", self.save_log)
        file_menu.addAction("Exit", self.close)

        self.settings_menu = menubar.addMenu("&Settings")
        
        baud_menu = self.settings_menu.addMenu("Baud Rate")
        baud_group = QActionGroup(self)
        for b in [9600, 19200, 38400, 115200]:
            act = QAction(str(b), self, checkable=True)
            if b == self.serial_config['baud']: act.setChecked(True)
            act.triggered.connect(lambda chk, v=b: self.update_serial_setting('baud', v))
            baud_group.addAction(act); baud_menu.addAction(act)

        # Parity
        parity_menu = self.settings_menu.addMenu("Parity")
        parity_group = QActionGroup(self)
        for label, key in [("None", 'N'), ("Even", 'E'), ("Odd", 'O')]:
            act = QAction(label, self, checkable=True)
            if key == self.serial_config['parity']: act.setChecked(True)
            act.triggered.connect(lambda chk, k=key: self.update_serial_setting('parity', k))
            parity_group.addAction(act); parity_menu.addAction(act)

        preset_menu = self.settings_menu.addMenu("Configure Buttons")
        for i in range(4):
            act = QAction(f"Configure Button {i+1}...", self)
            act.triggered.connect(lambda chk, idx=i: self.configure_preset(idx))
            preset_menu.addAction(act)

        menubar.addMenu("&Help").addAction("About", self.show_about)

    def update_serial_setting(self, key, value):
        self.serial_config[key] = value
        self.save_settings()

    def configure_preset(self, index):
        new_name, ok1 = QInputDialog.getText(self, "Button Name", "Label:", text=self.presets[index]["name"])
        if not ok1: return
        new_hex, ok2 = QInputDialog.getText(self, "Button Data", "Hex:", text=self.presets[index]["hex"])
        if ok2:
            self.presets[index] = {"name": new_name, "hex": new_hex}
            self.preset_btns[index].setText(new_name)
            self.save_settings()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Top Control Bar
        port_layout = QHBoxLayout()
        self.port_selector = QComboBox()
        self.refresh_ports()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        # New Separate Button
        separate_btn = QPushButton("Separate")
        separate_btn.clicked.connect(self.add_separator)
        
        port_layout.addWidget(QLabel("Port:"))
        port_layout.addWidget(self.port_selector, 1)
        port_layout.addWidget(self.connect_btn)
        port_layout.addWidget(separate_btn) # Placed to the right of connect/disconnect
        port_layout.addWidget(QPushButton("Clear", clicked=self.clear_log))
        layout.addLayout(port_layout)

        # Log Window
        self.log_display = QTextEdit(readOnly=True)
        self.log_display.setStyleSheet("background-color: #1e1e1e; color: #00FF00; font-family: 'Consolas';")
        layout.addWidget(self.log_display)

        # Preset Buttons Row
        button_group = QGroupBox("Modbus Commands (TX)")
        btn_layout = QHBoxLayout(button_group)
        self.preset_btns = []
        for i in range(4):
            btn = QPushButton(self.presets[i]["name"])
            btn.clicked.connect(lambda chk, idx=i: self.send_preset(idx))
            btn.setEnabled(False) 
            self.preset_btns.append(btn)
            btn_layout.addWidget(btn)
        layout.addWidget(button_group)

    def add_separator(self):
        """Adds 72 dash characters to the log window."""
        self.log_display.append("-" * 72)

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
            self.worker.send_hex(self.presets[index]["hex"])

    def toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.connect_btn.setText("Connect")
            self.port_selector.setEnabled(True)
            self.settings_menu.setEnabled(True)
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
            self.settings_menu.setEnabled(False)
            for b in self.preset_btns: b.setEnabled(True)

    def clear_log(self): self.log_display.clear()
    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "Text Files (*.txt)")
        if path:
            with open(path, 'w') as f: f.write(self.log_display.toPlainText())

    def show_about(self):
        # Using a custom message box to allow for a clickable link
        msg = QMessageBox(self)
        msg.setWindowTitle("About")
        msg.setIcon(QMessageBox.Information)
        
        # Set text as RichText to enable HTML link interpretation
        msg.setTextFormat(Qt.RichText)
        msg.setText(f"<b>RS-485 Modbus Monitor</b><br>Version {APP_VERSION}<br><br>{GEMINI_INFO}")
        
        # This is the secret sauce for clickable links in QMessageBox
        msg.button(QMessageBox.Ok) 
        
        if self.app_icon:
            msg.setWindowIcon(self.app_icon)
            msg.setIconPixmap(self.app_icon.pixmap(64, 64))
            
        msg.exec()

    def closeEvent(self, event):
        self.save_settings()
        if self.worker: self.worker.stop()
        event.accept()

if __name__ == "__main__":
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"modbus.monitor.{APP_VERSION}")
    
    app = QApplication(sys.argv)
    window = ModbusMonitor()
    window.show()
    sys.exit(app.exec())