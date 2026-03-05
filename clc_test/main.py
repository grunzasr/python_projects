import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
import os
from PIL import Image, ImageTk

# Local module imports
import version
from gui_app import ThroughputApp

def set_app_id(v_num):
    """
    Tells Windows this is a unique application to ensure the taskbar
    displays the custom icon and groups windows correctly by version.
    """
    try:
        # AppUserModelID format: Company.Product.SubProduct.Version
        myappid = f'industrial.rs485.tester.{v_num}'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        # Fallback for non-Windows or environments where ctypes fails
        pass

def show_about(root):
    """Creates a custom, modal 'About' window with a large icon and build info."""
    about_win = tk.Toplevel(root)
    about_win.title(f"About - v{version.VERSION_NUMBER}")
    about_win.geometry("450x380")
    about_win.resizable(False, False)
    
    # Make the window modal
    about_win.transient(root)
    about_win.grab_set()

    # Center the about window relative to the main window
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    about_win.geometry(f"+{root_x + 100}+{root_y + 100}")

    # --- Large Icon Section ---
    icon_path = os.path.join(os.path.dirname(__file__), "CLC_Tester.ico")
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path)
            img = img.resize((128, 128), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            img_label = ttk.Label(about_win, image=photo)
            img_label.image = photo  # Keep reference to prevent garbage collection
            img_label.pack(pady=15)
        except Exception:
            ttk.Label(about_win, text="[RS-485 Tool Icon]").pack(pady=15)

    # --- Version & Build Metadata ---
    ttk.Label(about_win, text="RS-485 Benchmarking Utility", font=("Helvetica", 12, "bold")).pack()
    ttk.Label(about_win, text=f"Version {version.VERSION_NUMBER}", font=("Helvetica", 10)).pack(pady=2)
    
    metadata_frame = ttk.Frame(about_win)
    metadata_frame.pack(pady=5)
    ttk.Label(metadata_frame, text=f"Build Date: {version.BUILD_DATE}", font=("Consolas", 9)).pack()
    ttk.Label(metadata_frame, text=f"Build Time: {version.BUILD_TIME}", font=("Consolas", 9)).pack()

    ttk.Label(about_win, text="\nIndustrial Protocol Testing\nModbus CRC-16 & DTR Driver Control", justify="center").pack()

    ttk.Button(about_win, text="Close", command=about_win.destroy).pack(pady=20)

def main():
    root = tk.Tk()
    
    # 1. Set Taskbar Title & App ID (including version)
    app_title = f"RS-485 Benchmarking Tool (v{version.VERSION_NUMBER})"
    root.title(app_title)
    set_app_id(version.VERSION_NUMBER)

    # 2. Set Window Icons
    icon_path = os.path.join(os.path.dirname(__file__), "CLC_Tester.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

    # 3. Responsive Scaling (80% of Monitor)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    width = int(screen_width * 0.8)
    height = int(screen_height * 0.8)
    x = int((screen_width - width) / 2)
    y = int((screen_height - height) / 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    # 4. Top-Level Menu Bar
    menubar = tk.Menu(root)
    
    # File Menu
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=file_menu)
    
    # Help Menu
    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(label="About", command=lambda: show_about(root))
    menubar.add_cascade(label="Help", menu=help_menu)
    
    root.config(menu=menubar)

    # 5. Load Main Application UI
    app = ThroughputApp(root)
    
    root.mainloop()

if __name__ == "__main__":
    main()