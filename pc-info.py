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
        self.update_interval = 5

        # Initialize update interval button
        self.update_interval_button = None
        
        # Track selection state to pause updates
        self.process_selected = False
        self.last_selected_pid = None

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
        self.display_system_info()
        self.display_gpu_info()
        
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
                # Always update system info and GPU info (but less frequently)
                self.system_info = get_system_info()
                
                # Schedule UI updates with small delays to keep UI responsive
                self.after_idle(self.display_system_info)
                self.after_idle(self.display_gpu_info)
                
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

    # Display GPU information
    def display_gpu_info(self):
        try:
            if hasattr(self, 'text_display'):
                gpu_info = get_gpu_info()
                if gpu_info:
                    self.text_display.insert("end", "\nGPU Information:\n")
                    self.text_display.insert("end", gpu_info)
                else:
                    self.text_display.insert("end", "\nLoading GPU information...")
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
                
                processes_sorted = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)
                return processes_sorted
            except Exception as e:
                logger.error(f"Error loading processes: {e}")
                return []
        
        def update_ui(processes_sorted):
            try:
                if not self.process_selected and hasattr(self, 'processes_tree'):  # Double-check selection state and existence
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

    # Display processes in treeview (legacy method for manual refresh)
    def display_processes(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if proc.info['name'] != 'System Idle Process':
                processes.append(proc.info)
        processes_sorted = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)
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