import os
import time
import psutil
import logging
import cpuinfo
import requests
import datetime
import platform
import threading
import subprocess
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from tkinter import ttk 

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
            values=["System Info", "Processes", "Refresh Now", "End Selected Process"],
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
        self.processes_tree = ttk.Treeview(self.tree_frame, columns=("name", "cpu_percent", "memory_percent"))
        self.processes_tree.heading("#0", text="PID")
        self.processes_tree.heading("name", text="Process Name")
        self.processes_tree.heading("cpu_percent", text="CPU Usage %")
        self.processes_tree.heading("memory_percent", text="Memory %")
        
        # Improved column widths for better readability
        self.processes_tree.column("#0", width=80, minwidth=60)
        self.processes_tree.column("name", width=300, minwidth=200)
        self.processes_tree.column("cpu_percent", width=120, minwidth=100)
        self.processes_tree.column("memory_percent", width=120, minwidth=100)
        
        # Style the treeview for dark theme
        self.setup_treeview_style()
        
        # Add context menu for process management
        self.setup_process_context_menu()
        
        # Bind keyboard events for process management
        self.processes_tree.bind('<Delete>', self.kill_selected_process_key)
        self.processes_tree.bind('<Button-3>', self.show_context_menu)  # Right click
        self.processes_tree.bind('<<TreeviewSelect>>', self.on_process_select)  # Selection changed
        self.processes_tree.bind('<Button-1>', self.on_process_click)  # Left click
        
        # Bind column header clicks for sorting
        self.processes_tree.heading("#0", command=lambda: self.sort_processes("pid"))
        self.processes_tree.heading("name", command=lambda: self.sort_processes("name"))
        self.processes_tree.heading("cpu_percent", command=lambda: self.sort_processes("cpu_percent"))
        self.processes_tree.heading("memory_percent", command=lambda: self.sort_processes("memory_percent"))
        
        self.processes_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Initialize update interval
        self.update_interval = 5

        # Initialize update interval button
        self.update_interval_button = None
        
        # Track selection state to pause updates
        self.process_selected = False
        self.last_selected_pid = None
        
        # Track sorting state
        self.sort_column = "cpu_percent"  # Default sort column
        self.sort_reverse = True  # Default to descending (highest CPU first)

        # Load system information
        self.system_info = get_system_info()
        
        # Load GPU information once and cache it
        self.gpu_info = get_gpu_info()
        
        # Flag to track if system info display is initialized
        self.system_info_displayed = False

        if not self.system_info:
            self.update_information()
        else:
            self.display_complete_system_info()  # Display all system info once
            self.display_processes()  # Display processes when opening

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

    # Setup treeview style for better theme integration
    def setup_treeview_style(self):
        style = ttk.Style()
        
        # Configure colors based on current appearance mode
        current_mode = ctk.get_appearance_mode()
        
        if current_mode == "Dark":
            # Dark theme colors
            bg_color = "#212121"
            fg_color = "#ffffff"
            select_bg = "#1f538d"
            select_fg = "#ffffff"
            field_bg = "#2b2b2b"
            heading_bg = "#2b2b2b"
        else:
            # Light theme colors
            bg_color = "#ffffff"
            fg_color = "#000000"
            select_bg = "#0078d4"
            select_fg = "#ffffff"
            field_bg = "#f0f0f0"
            heading_bg = "#e1e1e1"
        
        # Configure treeview style with better readability
        style.theme_use('clam')
        style.configure("Treeview",
                       background=bg_color,
                       foreground=fg_color,
                       fieldbackground=field_bg,
                       borderwidth=1,
                       relief="solid",
                       font=('Segoe UI', 10, 'normal'),  # Larger, clearer font
                       rowheight=25)  # Increased row height for better readability
        
        # Configure alternating row colors for better readability
        if current_mode == "Dark":
            alternate_color = "#2d2d2d"
        else:
            alternate_color = "#f8f8f8"
            
        self.processes_tree.tag_configure('oddrow', background=field_bg)
        self.processes_tree.tag_configure('evenrow', background=alternate_color)
        
        style.configure("Treeview.Heading",
                       background=heading_bg,
                       foreground=fg_color,
                       borderwidth=1,
                       relief="solid",
                       font=('Segoe UI', 11, 'bold'))  # Bold headers with larger font
        
        style.map("Treeview",
                 background=[('selected', select_bg)],
                 foreground=[('selected', select_fg)])
        
        style.map("Treeview.Heading",
                 background=[('active', heading_bg)],
                 foreground=[('active', fg_color)])

    # Setup context menu for process management
    def setup_process_context_menu(self):
        import tkinter as tk
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="End Process", command=self.kill_selected_process)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Refresh Process List", command=self.manual_refresh)

    # Show context menu on right click
    def show_context_menu(self, event):
        # Select the item under the cursor
        item = self.processes_tree.identify_row(event.y)
        if item:
            self.processes_tree.selection_set(item)
            self.processes_tree.focus(item)
            # Show context menu
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    # Handle process selection
    def on_process_select(self, event):
        selected_items = self.processes_tree.selection()
        if selected_items:
            self.process_selected = True
            # Get PID of selected process
            selected_item = selected_items[0]
            self.last_selected_pid = self.processes_tree.item(selected_item)['text']
            self.status_label.configure(text="Process selected - Updates paused")
        else:
            self.process_selected = False
            self.last_selected_pid = None
            self.status_label.configure(text="Ready")

    # Handle left click to potentially deselect
    def on_process_click(self, event):
        # Check if click is on empty area
        item = self.processes_tree.identify_row(event.y)
        if not item:
            # Clicked on empty area, clear selection
            self.processes_tree.selection_remove(self.processes_tree.selection())
            self.process_selected = False
            self.last_selected_pid = None
            self.status_label.configure(text="Ready")

    # Sort processes by column
    def sort_processes(self, column):
        # Toggle sort direction if clicking the same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            # Set default sort direction for each column
            if column == "pid":
                self.sort_reverse = False  # PID ascending by default
            elif column == "name":
                self.sort_reverse = False  # Name ascending by default
            elif column in ["cpu_percent", "memory_percent"]:
                self.sort_reverse = True  # CPU/Memory descending by default
        
        # Update column headers to show sort direction
        self.update_column_headers()
        
        # Refresh the process list with new sorting
        if not self.process_selected:
            self.display_processes_threaded()
        else:
            # If a process is selected, update immediately
            self.display_processes()

    # Update column headers to show sort indicators
    def update_column_headers(self):
        # Reset all headers
        self.processes_tree.heading("#0", text="PID")
        self.processes_tree.heading("name", text="Process Name")
        self.processes_tree.heading("cpu_percent", text="CPU Usage %")
        self.processes_tree.heading("memory_percent", text="Memory %")
        
        # Add sort indicator to current sort column
        sort_indicator = " ↓" if self.sort_reverse else " ↑"
        
        if self.sort_column == "pid":
            self.processes_tree.heading("#0", text=f"PID{sort_indicator}")
        elif self.sort_column == "name":
            self.processes_tree.heading("name", text=f"Process Name{sort_indicator}")
        elif self.sort_column == "cpu_percent":
            self.processes_tree.heading("cpu_percent", text=f"CPU Usage %{sort_indicator}")
        elif self.sort_column == "memory_percent":
            self.processes_tree.heading("memory_percent", text=f"Memory %{sort_indicator}")

    # Get sort key for a process
    def get_sort_key(self, proc_info):
        if self.sort_column == "pid":
            return int(proc_info.get('pid', 0))
        elif self.sort_column == "name":
            return proc_info.get('name', '').lower()
        elif self.sort_column == "cpu_percent":
            return float(proc_info.get('cpu_percent', 0) or 0)
        elif self.sort_column == "memory_percent":
            return float(proc_info.get('memory_percent', 0) or 0)
        return 0

    # Kill selected process via keyboard shortcut (Delete key)
    def kill_selected_process_key(self, event):
        self.kill_selected_process()

    # Kill the selected process
    def kill_selected_process(self):
        selected_item = self.processes_tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a process to terminate.")
            return

        # Get PID from the selected item
        pid_str = self.processes_tree.item(selected_item[0])['text']
        process_name = self.processes_tree.item(selected_item[0])['values'][0]
        
        try:
            pid = int(pid_str)
            
            # Confirm before killing the process
            result = messagebox.askyesno(
                "Confirm Process Termination",
                f"Are you sure you want to terminate the process?\n\n"
                f"Process: {process_name}\n"
                f"PID: {pid}\n\n"
                f"Warning: Terminating system processes may cause instability!"
            )
            
            if result:
                try:
                    process = psutil.Process(pid)
                    process_name_actual = process.name()
                    
                    # Check if it's a critical system process
                    critical_processes = ['System', 'Registry', 'csrss.exe', 'winlogon.exe', 'services.exe', 'lsass.exe', 'svchost.exe']
                    if process_name_actual in critical_processes:
                        messagebox.showerror(
                            "Cannot Terminate Process",
                            f"Cannot terminate critical system process: {process_name_actual}\n"
                            f"This could cause system instability or crash."
                        )
                        return
                    
                    # Try graceful termination first
                    process.terminate()
                    
                    # Wait a bit for graceful termination
                    try:
                        process.wait(timeout=3)
                        self.status_label.configure(text=f"Process {process_name} terminated")
                        logger.info(f"Successfully terminated process: {process_name} (PID: {pid})")
                    except psutil.TimeoutExpired:
                        # Force kill if graceful termination failed
                        process.kill()
                        self.status_label.configure(text=f"Process {process_name} force killed")
                        logger.info(f"Force killed process: {process_name} (PID: {pid})")
                    
                    # Reset status after 3 seconds
                    self.after(3000, lambda: self.status_label.configure(text="Ready"))
                    
                    # Clear selection and resume updates
                    self.process_selected = False
                    self.last_selected_pid = None
                    
                    # Refresh the process list
                    self.display_processes()
                    
                except psutil.NoSuchProcess:
                    messagebox.showinfo("Process Not Found", f"Process with PID {pid} no longer exists.")
                except psutil.AccessDenied:
                    messagebox.showerror(
                        "Access Denied", 
                        f"Access denied. Cannot terminate process: {process_name}\n"
                        f"You may need administrator privileges to terminate this process."
                    )
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to terminate process: {str(e)}")
                    logger.error(f"Failed to terminate process {process_name} (PID: {pid}): {str(e)}")
                    
        except ValueError:
            messagebox.showerror("Error", "Invalid process ID.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
            logger.error(f"Unexpected error in kill_selected_process: {str(e)}")

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
        elif choice == "End Selected Process":
            self.tabview.set("Processes")  # Switch to processes tab first
            self.kill_selected_process()
        # Reset the menu to show "View" again
        self.view_menu_button.set("View")

    def settings_menu_callback(self, choice):
        if choice == "Change Update Interval":
            self.change_update_interval()
        elif choice == "Theme: Dark":
            ctk.set_appearance_mode("dark")
            self.setup_treeview_style()  # Update treeview style
            self.status_label.configure(text="Theme changed to Dark")
            self.after(2000, lambda: self.status_label.configure(text="Ready"))
        elif choice == "Theme: Light":
            ctk.set_appearance_mode("light")
            self.setup_treeview_style()  # Update treeview style
            self.status_label.configure(text="Theme changed to Light")
            self.after(2000, lambda: self.status_label.configure(text="Ready"))
        elif choice == "Theme: System":
            ctk.set_appearance_mode("system")
            self.setup_treeview_style()  # Update treeview style
            self.status_label.configure(text="Theme changed to System")
            self.after(2000, lambda: self.status_label.configure(text="Ready"))
        # Reset the menu to show "Settings" again
        self.settings_menu_button.set("Settings")

    def help_menu_callback(self, choice):
        if choice == "About":
            messagebox.showinfo("About PC Info", 
                              "PC Info v2.1\n"
                              "A system information tool\n"
                              "Built with CustomTkinter\n\n"
                              "Features:\n"
                              "• System Hardware Information\n"
                              "• GPU Information\n"
                              "• Process Monitoring\n"
                              "• Process Termination (Right-click or Del key)\n"
                              "• Real-time Updates\n"
                              "• Modern Dark/Light Themes\n\n"
                              "Controls:\n"
                              "• Right-click on process: Context menu\n"
                              "• Delete key: Terminate selected process")
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
        # Reload GPU info on manual refresh
        self.gpu_info = get_gpu_info()
        
        # Reset the display flag and show complete info
        self.system_info_displayed = False
        self.display_complete_system_info()
        
        # Clear selection before manual refresh
        if self.process_selected:
            self.processes_tree.selection_remove(self.processes_tree.selection())
            self.process_selected = False
            self.last_selected_pid = None
        
        self.display_processes()
        self.status_label.configure(text="Updated")
        self.after(2000, lambda: self.status_label.configure(text="Ready"))

    # Update information in another thread
    def update_information_threaded(self):
        while True:
            try:
                # Always update system info (but less frequently)
                self.system_info = get_system_info()
                
                # Update only system info part (preserve GPU info display)
                self.after_idle(self.update_system_info_only)
                
                # Only update processes if none is selected
                if not self.process_selected:
                    self.after_idle(self.display_processes_threaded)
                    # Update status periodically to show it's working
                    if hasattr(self, 'status_label'):
                        self.after_idle(lambda: self.status_label.configure(text="Auto-updated"))
                        self.after(1000, lambda: self.status_label.configure(text="Ready") if hasattr(self, 'status_label') else None)
                else:
                    # Check if the selected process still exists
                    if self.last_selected_pid:
                        try:
                            pid = int(self.last_selected_pid)
                            if not psutil.pid_exists(pid):
                                # Selected process no longer exists, resume updates
                                self.after_idle(self.clear_selection_and_resume)
                        except (ValueError, psutil.NoSuchProcess):
                            self.after_idle(self.clear_selection_and_resume)
                            
            except Exception as e:
                logger.error(f"Error in update thread: {e}")
            time.sleep(self.update_interval)

    # Clear selection and resume updates
    def clear_selection_and_resume(self):
        try:
            if hasattr(self, 'processes_tree'):
                self.processes_tree.selection_remove(self.processes_tree.selection())
            self.process_selected = False
            self.last_selected_pid = None
            if hasattr(self, 'status_label'):
                self.status_label.configure(text="Selected process ended - Resuming updates")
                self.after(2000, lambda: self.status_label.configure(text="Ready") if hasattr(self, 'status_label') else None)
            self.after_idle(self.display_processes_threaded)
        except Exception as e:
            logger.error(f"Error in clear_selection_and_resume: {e}")

    def display_system_info(self):
        try:
            if hasattr(self, 'text_display'):
                self.text_display.delete("0.0", "end")  # Clear previous content
                if self.system_info:
                    self.text_display.insert("0.0", "System Information:\n")
                    for key, value in self.system_info.items():
                        self.text_display.insert("end", f"{key}: {value}\n")
                        # Small yield to keep UI responsive during large updates
                        self.update_idletasks()
                else:
                    self.text_display.insert("0.0", "Loading hardware information...")
        except Exception as e:
            logger.error(f"Error updating system info display: {e}")

    # Display complete system information (system + GPU) - called once
    def display_complete_system_info(self):
        try:
            if hasattr(self, 'text_display') and not self.system_info_displayed:
                self.text_display.delete("0.0", "end")  # Clear previous content
                
                # Display system information
                if self.system_info:
                    self.text_display.insert("0.0", "System Information:\n")
                    for key, value in self.system_info.items():
                        self.text_display.insert("end", f"{key}: {value}\n")
                else:
                    self.text_display.insert("0.0", "Loading hardware information...\n")
                
                # Display GPU information
                if hasattr(self, 'gpu_info') and self.gpu_info:
                    self.text_display.insert("end", "\nGPU Information:\n")
                    self.text_display.insert("end", self.gpu_info)
                else:
                    self.text_display.insert("end", "\nGPU Information not available\n")
                
                self.system_info_displayed = True
                self.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating complete system info display: {e}")

    # Update only system information (without GPU, for threaded updates)
    def update_system_info_only(self):
        try:
            if hasattr(self, 'text_display') and hasattr(self, 'system_info') and self.system_info_displayed:
                # Find and update only the system information part
                current_content = self.text_display.get("0.0", "end")
                
                # Split content to preserve GPU info
                lines = current_content.split('\n')
                gpu_start_index = -1
                
                for i, line in enumerate(lines):
                    if line.startswith("GPU Information:"):
                        gpu_start_index = i
                        break
                
                # Rebuild system info section
                system_lines = ["System Information:"]
                for key, value in self.system_info.items():
                    system_lines.append(f"{key}: {value}")
                
                if gpu_start_index > 0:
                    # Preserve GPU info
                    gpu_lines = lines[gpu_start_index:]
                    new_content = '\n'.join(system_lines + [''] + gpu_lines)
                else:
                    new_content = '\n'.join(system_lines)
                
                self.text_display.delete("0.0", "end")
                self.text_display.insert("0.0", new_content)
                self.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating system info only: {e}")

    # Display GPU information (legacy method - now unused in automatic updates)
    def display_gpu_info(self):
        try:
            if hasattr(self, 'text_display') and hasattr(self, 'gpu_info'):
                if self.gpu_info:
                    self.text_display.insert("end", "\nGPU Information:\n")
                    self.text_display.insert("end", self.gpu_info)
                else:
                    self.text_display.insert("end", "\nGPU Information not available\n")
                # Small yield to keep UI responsive
                self.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating GPU info display: {e}")

    # Display processes in treeview (thread-safe version)
    def display_processes_threaded(self):
        def load_processes():
            try:
                processes = []
                # Use a smaller batch size to avoid long blocking operations
                count = 0
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    if proc.info['name'] != 'System Idle Process':
                        processes.append(proc.info)
                        count += 1
                        # Yield control periodically during data collection
                        if count % 50 == 0:
                            time.sleep(0.001)  # Very short sleep to yield control
                
                # Sort using current sort settings
                return processes
            except Exception as e:
                logger.error(f"Error loading processes: {e}")
                return []
        
        def update_ui(processes):
            try:
                if not self.process_selected and hasattr(self, 'processes_tree'):  # Double-check selection state and existence
                    # Sort the processes using current sort settings
                    processes_sorted = sorted(processes, key=self.get_sort_key, reverse=self.sort_reverse)
                    
                    # Remember current selection if any
                    current_selection = self.processes_tree.selection()
                    selected_pid = None
                    if current_selection:
                        try:
                            selected_pid = self.processes_tree.item(current_selection[0])['text']
                        except:
                            pass  # Ignore errors if item no longer exists
                    
                    # Clear and repopulate in smaller chunks to keep UI responsive
                    self.processes_tree.delete(*self.processes_tree.get_children())
                    
                    # Process items in smaller batches
                    batch_size = 25
                    for batch_start in range(0, len(processes_sorted), batch_size):
                        batch_end = min(batch_start + batch_size, len(processes_sorted))
                        batch = processes_sorted[batch_start:batch_end]
                        
                        for index, proc_info in enumerate(batch, start=batch_start):
                            # Format CPU and memory percentages for better readability
                            cpu_percent = f"{proc_info['cpu_percent']:.1f}%" if proc_info['cpu_percent'] else "0.0%"
                            memory_percent = f"{proc_info['memory_percent']:.1f}%" if proc_info['memory_percent'] else "0.0%"
                            
                            # Alternate row colors for better readability
                            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
                            
                            # Insert process
                            try:
                                item_id = self.processes_tree.insert("", "end", text=str(proc_info['pid']), 
                                                                   values=(proc_info['name'], cpu_percent, memory_percent),
                                                                   tags=(tag,))
                                
                                # Restore selection if this was the previously selected process
                                if selected_pid and str(proc_info['pid']) == selected_pid:
                                    self.processes_tree.selection_set(item_id)
                                    self.processes_tree.focus(item_id)
                            except:
                                pass  # Ignore individual item errors
                        
                        # Yield control between batches
                        if batch_end < len(processes_sorted):
                            self.after_idle(lambda b=batch_end: self.update_after_yield(processes_sorted, b, selected_pid))
                            return  # Exit and continue with next batch later
                    
                    # Update column headers after all processes are loaded
                    self.update_column_headers()
                            
            except Exception as e:
                logger.error(f"Error updating process UI: {e}")
        
        # Load processes in a separate thread to avoid UI freezing
        import threading
        def background_load():
            processes = load_processes()
            # Update UI in main thread
            self.after_idle(lambda: update_ui(processes))
        
        thread = threading.Thread(target=background_load, daemon=True)
        thread.start()

    # Helper method for batched updates
    def update_after_yield(self, processes_sorted, start_index, selected_pid):
        batch_size = 25
        batch_end = min(start_index + batch_size, len(processes_sorted))
        batch = processes_sorted[start_index:batch_end]
        
        for index, proc_info in enumerate(batch, start=start_index):
            cpu_percent = f"{proc_info['cpu_percent']:.1f}%" if proc_info['cpu_percent'] else "0.0%"
            memory_percent = f"{proc_info['memory_percent']:.1f}%" if proc_info['memory_percent'] else "0.0%"
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            
            try:
                item_id = self.processes_tree.insert("", "end", text=str(proc_info['pid']), 
                                                   values=(proc_info['name'], cpu_percent, memory_percent),
                                                   tags=(tag,))
                
                if selected_pid and str(proc_info['pid']) == selected_pid:
                    self.processes_tree.selection_set(item_id)
                    self.processes_tree.focus(item_id)
            except:
                pass
        
        # Continue with next batch if there are more items
        if batch_end < len(processes_sorted):
            self.after_idle(lambda: self.update_after_yield(processes_sorted, batch_end, selected_pid))
        else:
            # Update column headers when all batches are done
            self.update_column_headers()

    # Display processes in treeview (legacy method for manual refresh)
    def display_processes(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if proc.info['name'] != 'System Idle Process':
                processes.append(proc.info)
        
        # Sort using current sort settings
        processes_sorted = sorted(processes, key=self.get_sort_key, reverse=self.sort_reverse)
        
        self.processes_tree.delete(*self.processes_tree.get_children())  # Clear previous content
        
        for index, proc_info in enumerate(processes_sorted):
            # Format CPU and memory percentages for better readability
            cpu_percent = f"{proc_info['cpu_percent']:.1f}%" if proc_info['cpu_percent'] else "0.0%"
            memory_percent = f"{proc_info['memory_percent']:.1f}%" if proc_info['memory_percent'] else "0.0%"
            
            # Alternate row colors for better readability
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            
            # Use PID as the text for the first column (#0) and remove it from values
            self.processes_tree.insert("", "end", text=str(proc_info['pid']), 
                                     values=(proc_info['name'], cpu_percent, memory_percent),
                                     tags=(tag,))
        
        # Update column headers
        self.update_column_headers()

    # Clear the text display
    def clear_text_display(self):
        self.text_display.delete("0.0", "end")
    
    # Handle window closing event
    def on_close(self):
        try:
            # Stop any ongoing operations
            self.process_selected = False
            # Give time for threads to finish
            if hasattr(self, 'update_thread'):
                self.update_thread = None
            self.destroy()  # Close the Tkinter window
        except Exception as e:
            logger.error(f"Error during window closing: {e}")
            self.destroy()

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
        gpu_list = []

        # Helper: Add GPU only if it's not a duplicate
        def add_gpu(info):
            if not any(info['name'] in gpu['name'] for gpu in gpu_list):
                gpu_list.append(info)

        # --- NVIDIA-GPUs via nvidia-smi ---
        def query_nvidia_smi():
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().splitlines()
                    for line in lines:
                        parts = line.strip().split(',')
                        if len(parts) >= 3:
                            name = parts[0].strip()
                            memory = f"{parts[1].strip()} MB"
                            driver = parts[2].strip()
                            add_gpu({'name': name, 'memory': memory, 'driver': driver, 'source': 'nvidia-smi'})
            except Exception:
                pass

        # --- Windows: WMI fallback (Intel/AMD/2nd GPU) ---
        def query_windows_wmi():
            try:
                powershell_cmd = """
                Get-CimInstance Win32_VideoController | ForEach-Object {
                    Write-Output "NAME: $($_.Name)"
                    Write-Output "VRAM: $($_.AdapterRAM)"
                    Write-Output "DRIVER: $($_.DriverVersion)"
                    Write-Output "---"
                }
                """
                result = subprocess.run(['powershell', '-Command', powershell_cmd],
                                        capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    blocks = result.stdout.strip().split('---')
                    for block in blocks:
                        lines = block.strip().splitlines()
                        gpu = {}
                        for line in lines:
                            if line.startswith("NAME:"):
                                gpu["name"] = line.split(":", 1)[1].strip()
                            elif line.startswith("VRAM:"):
                                try:
                                    vram_bytes = int(line.split(":", 1)[1].strip())
                                    if vram_bytes > 0:
                                        vram_gb = vram_bytes / (1024 ** 3)
                                        gpu["memory"] = f"{vram_gb:.1f} GB" if vram_gb >= 1 else f"{vram_bytes / (1024**2):.0f} MB"
                                except:
                                    pass
                            elif line.startswith("DRIVER:"):
                                gpu["driver"] = line.split(":", 1)[1].strip()

                        if gpu.get("name"):
                            gpu['source'] = 'WMI'
                            add_gpu(gpu)
            except:
                pass

        # --- macOS GPU info ---
        def query_macos():
            try:
                result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True)
                lines = result.stdout.splitlines()
                current_gpu = {}

                for line in lines:
                    line = line.strip()
                    if line.startswith("Chipset Model:"):
                        if current_gpu:
                            current_gpu['source'] = 'macOS'
                            add_gpu(current_gpu)
                        current_gpu = {"name": line.split(":", 1)[1].strip()}
                    elif "VRAM" in line:
                        current_gpu["memory"] = line.split(":", 1)[1].strip()
                    elif "Vendor:" in line:
                        current_gpu["vendor"] = line.split(":", 1)[1].strip()

                if current_gpu:
                    current_gpu['source'] = 'macOS'
                    add_gpu(current_gpu)
            except:
                pass

        # --- Linux GPU via lspci ---
        def query_linux():
            try:
                result = subprocess.run(['lspci'], capture_output=True, text=True)
                lines = result.stdout.splitlines()
                for line in lines:
                    if any(kw in line for kw in ['VGA', '3D', 'Display']):
                        name = line.split(':')[-1].strip()
                        add_gpu({'name': name, 'source': 'lspci'})
            except:
                pass

        # Detect system and query
        if system == 'Windows':
            query_nvidia_smi()
            query_windows_wmi()
        elif system == 'Darwin':
            query_macos()
        elif system == 'Linux':
            query_nvidia_smi()
            query_linux()
        else:
            return "Unsupported OS."

        # Format output
        if not gpu_list:
            return "No GPUs detected."

        output = ""
        for i, gpu in enumerate(gpu_list, 1):
            if len(gpu_list) > 1:
                output += f"=== GPU {i} ===\n"
            output += f"GPU: {gpu['name']}\n"
            if gpu.get('memory'):
                output += f"VRAM: {gpu['memory']}\n"
            if gpu.get('driver'):
                output += f"Driver: {gpu['driver']}\n"
            if gpu.get('vendor'):
                output += f"Vendor: {gpu['vendor']}\n"
            output += f"Source: {gpu['source']}\n\n"

        return output.strip()

    except Exception as e:
        return f"Fehler bei GPU-Erkennung: {e}"

if __name__ == "__main__":
    root = PCInfoApp()
    root.mainloop()