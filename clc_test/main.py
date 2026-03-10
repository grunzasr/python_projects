import tkinter as tk
from tkinter import ttk
import ctypes
import os
import sys
from PIL import Image, ImageTk
import version
from gui_app import ThroughputApp
import sys


def set_app_id(v_num):
    if sys.platform == "win32":
        try:
            myappid = f'industrial.rs485.tester.{v_num}'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except: pass

def show_about(root):
    about_win = tk.Toplevel(root)
    about_win.title(f"About - v{version.VERSION_NUMBER}")
    about_win.geometry("450x400")
    about_win.transient(root)
    about_win.grab_set()

    # Center logic
    root_x, root_y = root.winfo_x(), root.winfo_y()
    about_win.geometry(f"+{root_x + 50}+{root_y + 50}")

    # Large Icon (Cross-platform PIL)
    icon_path = os.path.join(os.path.dirname(__file__), "CLC_Tester.png") # Prefer PNG for Linux
    if not os.path.exists(icon_path):
        icon_path = os.path.join(os.path.dirname(__file__), "CLC_Tester.ico")
        
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path).resize((128, 128), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl = ttk.Label(about_win, image=photo)
            lbl.image = photo
            lbl.pack(pady=15)
        except: pass

    ttk.Label(about_win, text="RS-485 Python Serial Throughput GUI Tester", font=("Helvetica", 12, "bold")).pack()
    ttk.Label(about_win, text=f"Version {version.VERSION_NUMBER}").pack()
    ttk.Label(about_win, text=f"Build: {version.BUILD_DATE} {version.BUILD_TIME}", font=("Consolas", 9)).pack(pady=5)
    
    msg = "Cross-Platform RS-485 Tester\nLinux: Ensure user is in 'dialout' group."
    msg += "\r\nOriginal code created by Gemini -- https://gemini.google.com/share/167019f40cde"
    ttk.Label(about_win, text=msg, justify="center").pack(pady=10)
    ttk.Button(about_win, text="Close", command=about_win.destroy).pack(pady=15)

def main():
    root = tk.Tk()
    root.title(f"RS-485 Tool (v{version.VERSION_NUMBER})")
    set_app_id(version.VERSION_NUMBER)

    # Cross-platform Icon
    icon_ico = os.path.join(os.path.dirname(__file__), "CLC_Tester.ico")
    icon_png = os.path.join(os.path.dirname(__file__), "CLC_Tester.png")
    
    try:
        if sys.platform == "win32" and os.path.exists(icon_ico):
            root.iconbitmap(icon_ico)
        elif os.path.exists(icon_png):
            img = tk.PhotoImage(file=icon_png)
            root.iconphoto(True, img)
    except: pass
    
    
    # Splash screen support
    if getattr(sys, 'frozen', False ):
        try:
            import pyi_splash
        except ImportError:
            # Handle cases wehre the import might still fail
            py_splash = None
    else:
        class DummySplash:
            def update_text(self, text): pass
            def close(self): pass
            def is_alive(self): return False
        pyi_splash = DummySplash()
                

    # 80% Screen Scaling
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = int(sw*0.8), int(sh*0.8)
    root.geometry(f"{w}x{h}+{int((sw-w)/2)}+{int((sh-h)/2)}")

    # Menus
    mb = tk.Menu(root)
    fm = tk.Menu(mb, tearoff=0)
    fm.add_command(label="Exit", command=root.quit)
    mb.add_cascade(label="File", menu=fm)
    hm = tk.Menu(mb, tearoff=0)
    hm.add_command(label="About", command=lambda: show_about(root))
    mb.add_cascade(label="Help", menu=hm)
    root.config(menu=mb)

    root.lift()
    
    pyi_splash.close()

    app = ThroughputApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()