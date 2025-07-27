import os
import platform
import logging
import datetime
import requests
import threading
import psutil
import cpuinfo
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from tkinter import ttk  # For Treeview widget
import subprocess
import time


# Set up logging
def setup_logging():
    log_dir = "Log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = os.path.join(log_dir, f"PC-Info - {current_datetime}.log")

    logger = logging.getLogger("PC-Info")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# Set the appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class PCInfoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PC Info")
        self.resizable(width=False, height=False)
        self.geometry("800x600")  # Set a fixed window size
        self.protocol("WM_DELETE_WINDOW", self.on_close)  # Handle window closing event

        # Check internet connection
        if not self.check_internet_connection():
            messagebox.showerror("Error", "Internet connection is required to run this application.")
            self.destroy()  # Close the window if there's no internet connection
            return

        # Create menu bar frame
        self.menu_bar = ctk.CTkFrame(self, height=40)
        self.menu_bar.pack(fill="x", padx=0, pady=0)
        self.menu_bar.pack_propagate(False)

        # File Menu
        self.file_menu_button = ctk.CTkOptionMenu(
            self.menu_bar, 
            values=["Exit"],
            command=self.file_menu_callback,
            width=60,
            height=30
        )
        self.file_menu_button.pack(side="left", padx=5, pady=5)
        self.file_menu_button.set("File")

        # View Menu
        self.view_menu_button = ctk.CTkOptionMenu(
            self.menu_bar,
            values=["System Info", "Processes", "Refresh Now"],
            command=self.view_menu_callback,
            width=60,
            height=30
        )
        self.view_menu_button.pack(side="left", padx=5, pady=5)
        self.view_menu_button.set("View")

        # Settings Menu
        self.settings_menu_button = ctk.CTkOptionMenu(
            self.menu_bar,
            values=["Change Update Interval", "Theme: Dark", "Theme: Light", "Theme: System"],
            command=self.settings_menu_callback,
            width=80,
            height=30
        )
        self.settings_menu_button.pack(side="left", padx=5, pady=5)
        self.settings_menu_button.set("Settings")

        # Help Menu
        self.help_menu_button = ctk.CTkOptionMenu(
            self.menu_bar,
            values=["About"],
            command=self.help_menu_callback,
            width=60,
            height=30
        )
        self.help_menu_button.pack(side="left", padx=5, pady=5)
        self.help_menu_button.set("Help")

        # Status label on the right side
        self.status_label = ctk.CTkLabel(self.menu_bar, text="Ready")
        self.status_label.pack(side="right", padx=10, pady=5)

        # Create tabview for organizing content
        self.tabview = ctk.CTkTabview(self, width=780, height=500)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add tabs
        self.tabview.add("System Info")
        self.tabview.add("Processes")
        
        # Create text widget for system information
        self.text_display = ctk.CTkTextbox(self.tabview.tab("System Info"))
        self.text_display.pack(fill="both", expand=True, padx=10, pady=10)

        # Create frame for treeview in processes tab
        self.tree_frame = ctk.CTkFrame(self.tabview.tab("Processes"))
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create treeview to display processes
        self.processes_tree = ttk.Treeview(self.tree_frame, columns=("pid", "name", "cpu_percent", "memory_percent"))
        self.processes_tree.heading("#0", text="PID")
        self.processes_tree.heading("pid", text="PID")
        self.processes_tree.heading("name", text="Name")
        self.processes_tree.heading("cpu_percent", text="CPU %")
        self.processes_tree.heading("memory_percent", text="Memory %")
        self.processes_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Load system information
        self.system_info = get_system_info()

        if not self.system_info:
            self.update_information()
        else:
            self.display_system_info()
            self.display_gpu_info()  # Call display_gpu_info() to display GPU info when opening
            self.display_processes()  # Display processes when opening

        # Initialize update interval
        self.update_interval = 2

        # Initialize update interval button
        self.update_interval_button = None

        # Start the update thread
        self.update_thread = threading.Thread(target=self.update_information_threaded, daemon=True)
        self.update_thread.start()

    # Check internet connection
    def check_internet_connection(self):
        try:
            requests.get("http://www.google.com", timeout=3)
            return True
        except requests.ConnectionError:
            return False

    # Menu callback functions
    def file_menu_callback(self, choice):
        if choice == "Exit":
            self.destroy()
        # Reset the menu to show "File" again
        self.file_menu_button.set("File")

    def view_menu_callback(self, choice):
        if choice == "System Info":
            self.tabview.set("System Info")
        elif choice == "Processes":
            self.tabview.set("Processes")
        elif choice == "Refresh Now":
            self.manual_refresh()
            self.status_label.configure(text="Refreshed")
            self.after(2000, lambda: self.status_label.configure(text="Ready"))
        # Reset the menu to show "View" again
        self.view_menu_button.set("View")

    def settings_menu_callback(self, choice):
        if choice == "Change Update Interval":
            self.change_update_interval()
        elif choice == "Theme: Dark":
            ctk.set_appearance_mode("dark")
            self.status_label.configure(text="Theme changed to Dark")
            self.after(2000, lambda: self.status_label.configure(text="Ready"))
        elif choice == "Theme: Light":
            ctk.set_appearance_mode("light")
            self.status_label.configure(text="Theme changed to Light")
            self.after(2000, lambda: self.status_label.configure(text="Ready"))
        elif choice == "Theme: System":
            ctk.set_appearance_mode("system")
            self.status_label.configure(text="Theme changed to System")
            self.after(2000, lambda: self.status_label.configure(text="Ready"))
        # Reset the menu to show "Settings" again
        self.settings_menu_button.set("Settings")

    def help_menu_callback(self, choice):
        if choice == "About":
            messagebox.showinfo("About PC Info", 
                              "PC Info v2.0\n"
                              "A system information tool\n"
                              "Built with CustomTkinter\n\n"
                              "Features:\n"
                              "• System Hardware Information\n"
                              "• GPU Information\n"
                              "• Process Monitoring\n"
                              "• Real-time Updates\n"
                              "• Modern Dark/Light Themes")
        # Reset the menu to show "Help" again
        self.help_menu_button.set("Help")

    # Switch to hardware information tab
    def switch_to_hardware(self):
        self.tabview.set("System Info")

    # Switch to tasks information tab
    def switch_to_tasks(self):
        self.tabview.set("Processes")

    # Display settings
    def change_update_interval(self):
        new_interval = simpledialog.askinteger("Change Update Interval", "Enter the new update interval (seconds):", parent=self)
        if new_interval is not None and new_interval > 0:
            self.update_interval = new_interval
            self.status_label.configure(text=f"Update interval: {new_interval}s")
            self.after(3000, lambda: self.status_label.configure(text="Ready"))
            messagebox.showinfo("Success", f"Update interval set to {new_interval} seconds.")
        elif new_interval is not None:
            messagebox.showerror("Error", "Update interval must be a positive integer.")

    # Manual refresh method
    def manual_refresh(self):
        self.status_label.configure(text="Updating...")
        self.system_info = get_system_info()
        self.display_system_info()
        self.display_gpu_info()
        self.display_processes()
        self.status_label.configure(text="Updated")
        self.after(2000, lambda: self.status_label.configure(text="Ready"))

    # Update information in another thread
    def update_information_threaded(self):
        while True:
            try:
                self.system_info = get_system_info()
                self.display_system_info()
                self.display_gpu_info()
                self.display_processes()
                # Update status periodically to show it's working
                if hasattr(self, 'status_label'):
                    self.after(0, lambda: self.status_label.configure(text="Auto-updated"))
                    self.after(1000, lambda: self.status_label.configure(text="Ready"))
            except Exception as e:
                logger.error(f"Error in update thread: {e}")
            time.sleep(self.update_interval)

    def display_system_info(self):
        self.text_display.delete("0.0", "end")  # Clear previous content
        if self.system_info:
            self.text_display.insert("0.0", "System Information:\n")
            for key, value in self.system_info.items():
                self.text_display.insert("end", f"{key}: {value}\n")
        else:
            self.text_display.insert("0.0", "Loading hardware information...")

    # Display GPU information
    def display_gpu_info(self):
        gpu_info = get_gpu_info()
        if gpu_info:
            self.text_display.insert("end", "\nGPU Information:\n")
            self.text_display.insert("end", gpu_info)
        else:
            self.text_display.insert("end", "\nLoading GPU information...")

    # Display processes in treeview
    def display_processes(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if proc.info['name'] != 'System Idle Process':
                processes.append(proc.info)
        processes_sorted = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)
        self.processes_tree.delete(*self.processes_tree.get_children())  # Clear previous content
        for proc_info in processes_sorted:
            self.processes_tree.insert("", "end", values=(proc_info['pid'], proc_info['name'], proc_info['cpu_percent'], proc_info['memory_percent']))

    # Clear the text display
    def clear_text_display(self):
        self.text_display.delete("0.0", "end")
    
    # Handle window closing event
    def on_close(self):
        self.destroy()  # Close the Tkinter window
        root.quit()  # Exit the main loop

# Retrieve system information
def get_system_info():
    # CPU Info
    cpu_info = platform.processor()
    cpu_name = cpuinfo.get_cpu_info()['brand_raw']
    cpu_count = psutil.cpu_count()

    # RAM Info
    ram_info = psutil.virtual_memory()
    ram_amount_gb = round(ram_info.total / (1024 ** 3))

    # Disk Info
    disk_info = psutil.disk_usage('/')
    disk_total_gb = round(disk_info.total / (1024 ** 3))

    # System Info
    system_info = {
        "CPU Info": cpu_info,
        "CPU Name": cpu_name,
        "CPU Count": cpu_count,
        "RAM Amount": ram_amount_gb,
        "Storage Total": disk_total_gb,
        "System": platform.system(),
        "Exact Version": platform.platform(),
        "Architecture": platform.architecture()[0],
        "Python Version": platform.python_version()
    }
    return system_info

def get_gpu_info():
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True)
            output_lines = result.stdout.split('\n')
            gpu_info = ""
            for line in output_lines:
                if 'Chipset Model' in line:
                    gpu_info += f"GPU: {line.strip()}\n"
            if gpu_info:
                return gpu_info
            else:
                return "No GPU information available."
        elif system == 'Windows':  # Windows
            result = subprocess.run(['wmic', 'path', 'win32_videocontroller', 'get', 'caption'], capture_output=True, text=True)
            output_lines = result.stdout.split('\n')
            gpu_info = ""
            for line in output_lines:
                if 'NVIDIA' in line or 'AMD' in line or 'Intel' in line:
                    gpu_info += f"GPU: {line.strip()}\n"
            if gpu_info:
                return gpu_info
            else:
                return "No GPU information available."
        elif system == 'Linux':  # Linux
            result = subprocess.run(['lspci', '-vnn', '|', 'grep', '-i', 'vga', '|', 'grep', '-i', 'vga', '|', 'cut', '-d', ']', '-f', '3'], capture_output=True, text=True, shell=True)
            gpu_info = result.stdout.strip()
            if gpu_info:
                return f"GPU: {gpu_info}"
            else:
                return "No GPU information available."
        else:
            return "Unsupported platform."
    except Exception as e:
        logger.error(f"An error occurred while retrieving GPU information: {e}")
        return "Failed to retrieve GPU information."

if __name__ == "__main__":
    root = PCInfoApp()
    root.mainloop()