import tkinter as tk
from gui_app import ThroughputApp

def main():
    root = tk.Tk()
    root.title("Modular RS-485 Tester")

    # 1. Get Screen Dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # 2. Calculate 80% of the monitor size
    width = int(screen_width * 0.8)
    height = int(screen_height * 0.8)

    # 3. Calculate position offsets to center the window
    x_offset = int((screen_width - width) / 2)
    y_offset = int((screen_height - height) / 2)

    # 4. Apply geometry: "WidthxHeight+X+Y"
    root.geometry(f"{width}x{height}+{x_offset}+{y_offset}")
    
    # Initialize the GUI component
    app = ThroughputApp(root)
    
    root.mainloop()

if __name__ == "__main__":
    main()