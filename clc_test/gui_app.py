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
        self.rowconfigure(6, weight=9) # Console area weight

        # --- Port Selection ---
        ttk.Label(self, text="Sender Port:").grid(row=0, column=0, sticky="w")
        self.sender_var = tk.StringVar()
        self.sender_entry = ttk.Entry(self, textvariable=self.sender_var)
        self.sender_entry.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Button(self, text="Select", command=lambda: self.pick_port(self.sender_var)).grid(row=0, column=2, padx=5)

        ttk.Label(self, text="Receiver Port:").grid(row=1, column=0, sticky="w")
        self.receiver_var = tk.StringVar()
        self.receiver_entry = ttk.Entry(self, textvariable=self.receiver_var)
        self.receiver_entry.grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Button(self, text="Select", command=lambda: self.pick_port(self.receiver_var)).grid(row=1, column=2, padx=5)

        # --- Standard Settings ---
        ttk.Label(self, text="Baud Rate:").grid(row=2, column=0, sticky="w")
        self.baud_rate = ttk.Combobox(self, values=[9600, 38400, 115200, 921600])
        self.baud_rate.set(115200)
        self.baud_rate.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(self, text="Payload (KB):").grid(row=3, column=0, sticky="w")
        self.payload_entry = ttk.Entry(self)
        self.payload_entry.insert(0, "10")
        self.payload_entry.grid(row=3, column=1, sticky="ew", pady=2)

        # --- Controls ---
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="Run Test", command=self.on_start)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)

        # --- Console (90% Weight) ---
        console_container = ttk.Frame(self)
        console_container.grid(row=6, column=0, columnspan=3, sticky="nsew")
        console_container.columnconfigure(0, weight=1)
        console_container.rowconfigure(0, weight=1)

        self.console = tk.Text(console_container, state='disabled', font=("Consolas", 10), wrap="none")
        self.console.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(console_container, orient=tk.VERTICAL, command=self.console.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll = ttk.Scrollbar(console_container, orient=tk.HORIZONTAL, command=self.console.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.console.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    def pick_port(self, target_var):
        popup = tk.Toplevel(self)
        popup.title("Select Hardware (FTDI highlighted Green)")
        popup.geometry("600x400")
        
        lb = tk.Listbox(popup, font=("Consolas", 10), selectmode=tk.SINGLE)
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ports = get_available_ports()
        for i, p in enumerate(ports):
            lb.insert(tk.END, p["text"])
            if p["is_ftdi"]:
                lb.itemconfig(i, {'fg': 'green'})
        
        def on_confirm():
            if lb.curselection():
                target_var.set(lb.get(lb.curselection()))
                popup.destroy()
        
        ttk.Button(popup, text="Confirm Selection", command=on_confirm).pack(pady=10)

    def apply_saved_settings(self):
        data = settings.load_settings()
        if data:
            self.sender_var.set(data.get('sender_port', ''))
            self.receiver_var.set(data.get('receiver_port', ''))
            self.baud_rate.set(data.get('baud_rate', '115200'))
            self.payload_entry.delete(0, tk.END)
            self.payload_entry.insert(0, data.get('payload_kb', '10'))

    def log(self, msg):
        self.console.config(state='normal')
        self.console.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.console.see(tk.END)
        self.console.config(state='disabled')

    def clear_log(self):
        self.console.config(state='normal')
        self.console.delete('1.0', tk.END)
        self.console.config(state='disabled')

    def on_start(self):
        try:
            s_raw = self.sender_var.get()
            r_raw = self.receiver_var.get()
            if not s_raw or not r_raw: raise ValueError("Select Ports")

            s_port = s_raw.split(":")[0].strip()
            r_port = r_raw.split(":")[0].strip()
            
            settings.save_settings(s_raw, r_raw, self.baud_rate.get(), self.payload_entry.get())

            params = {
                "s_port": s_port, "r_port": r_port,
                "baud": int(self.baud_rate.get()),
                "kb_size": int(self.payload_entry.get()),
                "sw_delay": 0.01, "log_callback": self.log
            }
            
            self.start_btn.config(state='disabled')
            tester = RS485Benchmark(**params)
            threading.Thread(target=lambda: [tester.run(), self.master.after(0, lambda: self.start_btn.config(state='normal'))], daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", str(e))