import os
import platform
import logging
import datetime
import requests
import threading
import psutil
import cpuinfo
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
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

class PCInfoApp(tk.Tk):
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

        # Create menu bar
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        # Create File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.destroy)

        # Create Settings menu
        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Change Update Interval", command=self.change_update_interval)

        # Create text widget to display information
        self.text_display = tk.Text(self)
        self.text_display.pack(fill=tk.BOTH, expand=True)
        self.text_display.config(state="disabled")

        # Create treeview to display processes
        self.processes_tree = ttk.Treeview(self, columns=("pid", "name", "cpu_percent", "memory_percent"))
        self.processes_tree.heading("#0", text="PID")
        self.processes_tree.heading("pid", text="PID")
        self.processes_tree.heading("name", text="Name")
        self.processes_tree.heading("cpu_percent", text="CPU %")
        self.processes_tree.heading("memory_percent", text="Memory %")
        self.processes_tree.pack(fill=tk.BOTH, expand=True)

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

    # Switch to hardware information tab
    def switch_to_hardware(self):
        self.clear_text_display()  # Clear the text display
        self.display_system_info()
        self.display_gpu_info()

    # Switch to tasks information tab
    def switch_to_tasks(self):
        self.clear_text_display()  # Clear the text display
        self.display_processes()  # Display processes

    # Display settings
    def change_update_interval(self):
        new_interval = simpledialog.askinteger("Change Update Interval", "Enter the new update interval (seconds):", parent=self)
        if new_interval is not None and new_interval > 0:
            self.update_interval = new_interval
            messagebox.showinfo("Success", f"Update interval set to {new_interval} seconds.")
        elif new_interval is not None:
            messagebox.showerror("Error", "Update interval must be a positive integer.")

    # Update information in another thread
    def update_information_threaded(self):
        while True:
            self.system_info = get_system_info()
            self.display_system_info()
            self.display_gpu_info()
            self.display_processes()
            time.sleep(self.update_interval)

    def display_system_info(self):
        self.text_display.config(state="normal")
        self.text_display.delete("1.0", tk.END)  # Clear previous content
        if self.system_info:
            self.text_display.insert(tk.END, "System Information:\n")
            for key, value in self.system_info.items():
                self.text_display.insert(tk.END, f"{key}: {value}\n")
        else:
            self.text_display.insert(tk.END, "Loading hardware information...")
        self.text_display.config(state="disabled")

    # Display GPU information
    def display_gpu_info(self):
        gpu_info = get_gpu_info()
        self.text_display.config(state="normal")
        if gpu_info:
            self.text_display.insert(tk.END, "\nGPU Information:\n")
            self.text_display.insert(tk.END, gpu_info)
        else:
            self.text_display.insert(tk.END, "\nLoading GPU information...")
        self.text_display.config(state="disabled")

    # Display processes in treeview
    def display_processes(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if proc.info['name'] != 'System Idle Process':
                processes.append(proc.info)
        processes_sorted = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)
        self.processes_tree.delete(*self.processes_tree.get_children())  # Clear previous content
        for proc_info in processes_sorted:
            self.processes_tree.insert("", tk.END, values=(proc_info['pid'], proc_info['name'], proc_info['cpu_percent'], proc_info['memory_percent']))

    # Clear the text display
    def clear_text_display(self):
        self.text_display.config(state="normal")
        self.text_display.delete("1.0", tk.END)
        self.text_display.config(state="disabled")
    
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