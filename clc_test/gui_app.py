import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from rs485_engine import RS485Benchmark, get_available_ports
import settings_manager as settings

class ThroughputApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding="10")
        self.master = master
        self.pack(fill=tk.BOTH, expand=True)
        self.setup_ui()
        self.apply_saved_settings()

    def setup_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(7, weight=9)

        # Port Selection
        ttk.Label(self, text="Sender Port:").grid(row=0, column=0, sticky="w")
        self.sender_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.sender_var).grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Button(self, text="Select", command=lambda: self.pick_port(self.sender_var)).grid(row=0, column=2, padx=5)

        ttk.Label(self, text="Receiver Port:").grid(row=1, column=0, sticky="w")
        self.receiver_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.receiver_var).grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Button(self, text="Select", command=lambda: self.pick_port(self.receiver_var)).grid(row=1, column=2, padx=5)

        # Baud & Payload
        ttk.Label(self, text="Baud Rate:").grid(row=2, column=0, sticky="w")
        self.baud_rate = ttk.Combobox(self, values=[9600, 38400, 115200, 921600])
        self.baud_rate.set(9600)
        self.baud_rate.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(self, text="Payload (bytes):").grid(row=3, column=0, sticky="w")
        self.payload_entry = ttk.Entry(self)
        self.payload_entry.insert(0, "10")
        self.payload_entry.grid(row=3, column=1, sticky="ew", pady=2)

        # Controls
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="Run Test", command=self.on_start)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.modbus_btn = ttk.Button(btn_frame, text="Modbus CMD", command=self.on_modbus_cmd)
        self.modbus_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        # 4-20 mA Settings
        self.loop_group = ttk.LabelFrame(self, text=" 4-20 mA Loop Control ")
        self.loop_group.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        self.level_send_btn = ttk.Button(self.loop_group, text="Send Level", command=self.on_send_level)
        self.level_send_btn.pack(side=tk.LEFT, padx=5, pady=5)
        # 1. Create a variable to hold the slider's value (0.0 to 100.0)
        self.level_val = tk.IntVar(value=400)

        # 2. Define the Scale (Slider)
        # standard 4-20 mA range logic:
        self.level_slider = ttk.Scale(
            self.loop_group, #loop_btn_frame, 
            from_=0, 
            to=4095, 
            variable=self.level_val, 
            orient=tk.HORIZONTAL,
            length=150,
            command=self.update_level_label
            )

        # 3. Pack it to the right of the button
        self.level_slider.pack(side=tk.LEFT, padx=10)

        # 4. (Optional) Add a label to show the exact number
        self.level_label = ttk.Label(self.loop_group, text="400")
        self.level_label.pack(side=tk.LEFT)
        self.level_units_label = ttk.Label(self.loop_group, text=" ADC counts")
        self.level_units_label.pack(side=tk.LEFT)        
        
        # Console
        con_f = ttk.Frame(self)
        con_f.grid(row=7, column=0, columnspan=3, sticky="nsew")
        con_f.columnconfigure(0, weight=1); con_f.rowconfigure(0, weight=1)
        self.console = tk.Text(con_f, state='disabled', font=("Consolas", 10), wrap="none")
        self.console.grid(row=0, column=0, sticky="nsew")
        vs = ttk.Scrollbar(con_f, orient=tk.VERTICAL, command=self.console.yview)
        vs.grid(row=0, column=1, sticky="ns")
        self.console.configure(yscrollcommand=vs.set)

    def pick_port(self, target_var):
        popup = tk.Toplevel(self)
        popup.title("Select Port")
        lb = tk.Listbox(popup, font=("Consolas", 10), width=60)
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ports = get_available_ports()
        for i, p in enumerate(ports):
            lb.insert(tk.END, p["text"])
            if p["is_ftdi"]: lb.itemconfig(i, {'fg': 'green'})
        def confirm():
            if lb.curselection():
                target_var.set(lb.get(lb.curselection()))
                popup.destroy()
        ttk.Button(popup, text="OK", command=confirm).pack(pady=5)

    def log(self, msg):
        self.console.config(state='normal')
        self.console.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.console.see(tk.END)
        self.console.config(state='disabled')

    def clear_log(self):
        self.console.config(state='normal')
        self.console.delete('1.0', tk.END)
        self.console.config(state='disabled')

    def get_clean_ports(self):
        # Splits based on first colon to handle /dev/ttyUSB0: Description
        s_raw = self.sender_var.get()
        r_raw = self.receiver_var.get()
        if not s_raw or not r_raw: raise ValueError("Select Ports First")
        return s_raw.split(":")[0].strip(), r_raw.split(":")[0].strip()

    def on_start(self):
        try:
            s, r = self.get_clean_ports()
            settings.save_settings(self.sender_var.get(), self.receiver_var.get(), self.baud_rate.get(), self.payload_entry.get())
            tester = RS485Benchmark(s, r, int(self.baud_rate.get()), int(self.payload_entry.get()), 0.01, self.log)
            self.start_btn.config(state='disabled')
            threading.Thread(target=lambda: [tester.run(), self.master.after(0, lambda: self.start_btn.config(state='normal'))], daemon=True).start()
        except Exception as e: messagebox.showerror("Error", str(e))
        
    def on_send_level(self):
        try:
            s, r = self.get_clean_ports()
            settings.save_settings(self.sender_var.get(), self.receiver_var.get(), self.baud_rate.get(), self.payload_entry.get())
            tester = RS485Benchmark(s, r, int(self.baud_rate.get()), 1, 0.01, self.log)
            
            self.level_send_btn.config(state='disabled')
            
            threading.Thread(target=tester.send_modbus_loop, address=1, register=50000, value=self.level_val, daemon=True).start()
            
            
        except Exception as e: messagebox.showerror("Error", str(e))        

    def on_modbus_cmd(self):
        try:
            s, r = self.get_clean_ports()
            settings.save_settings(self.sender_var.get(), self.receiver_var.get(), self.baud_rate.get(), self.payload_entry.get())
            tester = RS485Benchmark(s, r, int(self.baud_rate.get()), 1, 0.01, self.log)
            threading.Thread(target=tester.send_modbus_preset, daemon=True).start()
        except Exception as e: messagebox.showerror("Error", str(e))

    def apply_saved_settings(self):
        d = settings.load_settings()
        if d:
            self.sender_var.set(d.get('sender_port', ''))
            self.receiver_var.set(d.get('receiver_port', ''))
            self.baud_rate.set(d.get('baud_rate', '115200'))
            self.payload_entry.delete(0, tk.END); self.payload_entry.insert(0, d.get('payload', '10'))
            
    def update_level_label(self, val):
        # val is passed as a string by the scale, so we convert to integer
        float_val = float(val)
        int_val = int(float_val)
        self.level_label.config(text=f"{int_val}")