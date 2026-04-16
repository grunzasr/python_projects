import sys
import re
import os
import time
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QComboBox, QPushButton, QTextEdit, 
                             QFileDialog, QMessageBox, QLabel)
from PySide6.QtGui import QAction, QColor, QStandardItemModel, QStandardItem, QIcon
from PySide6.QtCore import Qt, QThread, Signal, Slot

APP_VERSION = "1.4.0"

class SerialWorker(QThread):
    """Threaded worker to handle serial data reading without blocking the UI."""
    data_received = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, port_name, baudrate=9600):
        super().__init__()
        self.port_name = port_name
        self.baudrate = baudrate
        self._run_flag = True

    def run(self):
        try:
            # Configure the serial port (Modbus RTU defaults)
            with serial.Serial(self.port_name, self.baudrate, timeout=0.1) as ser:
                self.data_received.emit(f"System: Opened {self.port_name} at {self.baudrate} baud.")
                
                while self._run_flag:
                    if ser.in_waiting > 0:
                        # Reading raw data for monitoring purposes
                        raw_data = ser.read(ser.in_waiting)
                        # Hex representation is common for Modbus debugging
                        hex_data = raw_data.hex(' ').upper()
                        self.data_received.emit(f"RX: {hex_data}")
                    
                    time.sleep(0.01) # Small sleep to prevent CPU spiking
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self._run_flag = False
        self.wait()

class ModbusMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"RS-485 Modbus Monitor - v{APP_VERSION}")
        self.resize(850, 600)
        
        self.worker = None # Placeholder for our thread
        
        # Icon Setup
        base_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_path, "Resources", "ModbusMonitor.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            self.app_icon = QIcon(icon_path)
        else:
            self.app_icon = None

        self.setup_menu()
        self.setup_ui()
        
    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        
        save_action = QAction("Save Log", self)
        save_action.triggered.connect(self.save_log)
        file_menu.addAction(save_action)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        port_layout = QHBoxLayout()
        self.port_selector = QComboBox()
        self.refresh_ports()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_ports)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)

        port_layout.addWidget(QLabel("Port:"))
        port_layout.addWidget(self.port_selector, 1)
        port_layout.addWidget(refresh_btn)
        port_layout.addWidget(self.connect_btn)
        
        layout.addLayout(port_layout)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: #1e1e1e; color: #00FF00; font-family: 'Consolas';")
        layout.addWidget(self.log_display)

    def refresh_ports(self):
        self.port_selector.clear()
        model = QStandardItemModel()
        ports = list(serial.tools.list_ports.comports())

        def natural_sort_key(p):
            return [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', p.device)]

        ports.sort(key=natural_sort_key)

        for port in ports:
            mfr = port.manufacturer or "Unknown"
            display_text = f"{port.device} | {mfr} | {port.description}"
            item = QStandardItem(display_text)
            # Store the raw device name (e.g., COM3) in the UserData role
            item.setData(port.device, Qt.UserRole)
            
            if "FTDI" in (f"{port.description} {mfr}").upper():
                item.setForeground(QColor("green"))
            else:
                item.setForeground(QColor("black"))
            model.appendRow(item)
        
        self.port_selector.setModel(model)

    def toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self.stop_logging()
        else:
            self.start_logging()

    def start_logging(self):
        # Get the actual port name from the hidden data role
        index = self.port_selector.currentIndex()
        port_name = self.port_selector.model().item(index).data(Qt.UserRole)
        
        if not port_name:
            return

        self.worker = SerialWorker(port_name)
        self.worker.data_received.connect(self.update_log)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.start()
        
        self.connect_btn.setText("Disconnect")
        self.port_selector.setEnabled(False)

    def stop_logging(self):
        if self.worker:
            self.worker.stop()
            self.log_display.append("System: Connection closed.")
        
        self.connect_btn.setText("Connect")
        self.port_selector.setEnabled(True)

    @Slot(str)
    def update_log(self, text):
        self.log_display.append(text)

    @Slot(str)
    def handle_error(self, err_msg):
        QMessageBox.critical(self, "Serial Error", f"An error occurred: {err_msg}")
        self.stop_logging()

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "Text Files (*.txt)")
        if path:
            with open(path, 'w') as f:
                f.write(self.log_display.toPlainText())

    def show_about(self):
        about_msg = QMessageBox(self)
        about_msg.setWindowTitle("About")
        about_msg.setText(f"RS-485 Modbus Monitor v{APP_VERSION}")
        if self.app_icon:
            about_msg.setWindowIcon(self.app_icon)
            about_msg.setIconPixmap(self.app_icon.pixmap(64, 64))
        about_msg.exec()

    def closeEvent(self, event):
        """Clean up thread before closing app."""
        self.stop_logging()
        event.accept()

if __name__ == "__main__":
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"modbus.monitor.{APP_VERSION}")

    app = QApplication(sys.argv)
    window = ModbusMonitor()
    window.show()
    sys.exit(app.exec())