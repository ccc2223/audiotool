import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, StringVar
import threading
import time
import traceback
import subprocess
import concurrent.futures
import shutil
from pathlib import Path

class AudioToolApp:
    CONFIG_FILE = "audio_tool_config.json"
    
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Audio Toolbox")
        self.root.geometry("900x650")  # Set initial window size
        
        # Load configuration
        self.config = self.load_config()
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure('TButton', padding=5, font='Arial 10')
        self.style.configure('TNotebook.Tab', font='Arial 9 bold')
        self.style.configure('Info.TLabel', font='Arial 9 italic')
        self.style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        
        # Set up default settings if not present
        if "m4a_bitrate" not in self.config:
            self.config["m4a_bitrate"] = "320k"  # Hardcoded to 320k
        else:
            self.config["m4a_bitrate"] = "320k"  # Force update to 320k
            
        self.save_config()
        
        # Initialize threading parameters BEFORE creating widgets
        # For managing concurrent processing
        self.max_workers = max(1, os.cpu_count() - 2) if os.cpu_count() else 2  # Leave 2 cores free for system
        self.futures = []
        self.processed_count = 0
        self.total_files = 0
            
        # Conversion threads
        self.current_conversion_thread = None
        self.stop_conversion = False
        
        # Debug variables
        self.debug_mode = False
            
        # Create GUI elements
        self.create_widgets()
        self.setup_folder_views()

    def create_widgets(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # App description at the top
        description = ttk.Label(main_frame, 
                              text="Advanced Audio Toolbox - Split, Join, and Convert Audio Files", 
                              font=("Arial", 12, "bold"))
        description.pack(pady=(0, 10))
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)

        # Create tabs
        self.create_split_tab()
        self.create_join_tab()
        self.create_convert_tab()
        self.create_settings_tab()
        
        # Progress frame
        self.progress_frame = ttk.LabelFrame(main_frame, text="Progress")
        self.progress_frame.pack(fill='x', pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.progress_frame, variable=self.progress_var, length=100)
        self.progress.pack(fill='x', side=tk.TOP, padx=10, pady=5)
        
        # Progress info
        self.progress_label = ttk.Label(self.progress_frame, text="Ready")
        self.progress_label.pack(fill='x', side=tk.TOP, padx=10, pady=(0, 5))
        
        # Cancel button below progress bar
        self.cancel_btn = ttk.Button(self.progress_frame, text="Cancel", command=self.cancel_operation, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.TOP, pady=(0, 5))
        
        # Status bar
        self.status = ttk.Label(main_frame, text="Ready", borderwidth=1, relief="sunken")
        self.status.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

    def create_split_tab(self):
        split_tab = ttk.Frame(self.notebook)
        self.notebook.add(split_tab, text="Split Audio")
        
        # Folder selection frame
        folder_frame = ttk.Frame(split_tab)
        folder_frame.pack(fill='x', pady=5)
        
        # Folder selection with labels
        ttk.Label(folder_frame, text="Input:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.split_input_path = ttk.Label(folder_frame, text="Not selected", style="Info.TLabel")
        self.split_input_path.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(folder_frame, text="Select Input Folder",
                  command=lambda: self.select_folder("split_input")).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(folder_frame, text="Output:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.split_output_path = ttk.Label(folder_frame, text="Not selected", style="Info.TLabel")
        self.split_output_path.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(folder_frame, text="Select Output Folder",
                  command=lambda: self.select_folder("split_output")).grid(row=1, column=2, padx=5, pady=5)
        
        # Folder contents views in a frame
        view_frame = ttk.Frame(split_tab)
        view_frame.pack(fill='both', expand=True, pady=5)
        
        # File viewers with counts
        self.split_input_tree = self.create_file_tree(view_frame, "Split Input Files")
        self.split_input_tree.pack(side=tk.LEFT, fill='both', expand=True, padx=5)
        
        self.split_output_tree = self.create_file_tree(view_frame, "Split Output Files")
        self.split_output_tree.pack(side=tk.RIGHT, fill='both', expand=True, padx=5)
        
        # Button frame
        button_frame = ttk.Frame(split_tab)
        button_frame.pack(pady=10)
        
        # Split button with tooltip
        split_btn = ttk.Button(button_frame, text="Split Files (12min)", 
                              command=self.split_files)
        self.create_tooltip(split_btn, "Split WAV files into 12-minute segments")
        split_btn.pack(side=tk.LEFT, padx=10)
        
        # Convert button with tooltip
        convert_btn = ttk.Button(button_frame, text="Convert All to WAV", 
                               command=self.convert_all_to_wav)
        self.create_tooltip(convert_btn, "Convert all non-WAV files in input folder to WAV format (saved in same folder)")
        convert_btn.pack(side=tk.LEFT, padx=10)

    def create_join_tab(self):
        join_tab = ttk.Frame(self.notebook)
        self.notebook.add(join_tab, text="Join Audio")
        
        # Folder selection frame
        folder_frame = ttk.Frame(join_tab)
        folder_frame.pack(fill='x', pady=5)
        
        # Folder selection with labels
        ttk.Label(folder_frame, text="Input:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.join_input_path = ttk.Label(folder_frame, text="Not selected", style="Info.TLabel")
        self.join_input_path.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(folder_frame, text="Select Input Folder",
                  command=lambda: self.select_folder("join_input")).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(folder_frame, text="Output:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.join_output_path = ttk.Label(folder_frame, text="Not selected", style="Info.TLabel")
        self.join_output_path.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(folder_frame, text="Select Output Folder",
                  command=lambda: self.select_folder("join_output")).grid(row=1, column=2, padx=5, pady=5)
        
        # Folder contents views in a frame
        view_frame = ttk.Frame(join_tab)
        view_frame.pack(fill='both', expand=True, pady=5)
        
        # File viewers
        self.join_input_tree = self.create_file_tree(view_frame, "Join Input Files")
        self.join_input_tree.pack(side=tk.LEFT, fill='both', expand=True, padx=5)
        
        self.join_output_tree = self.create_file_tree(view_frame, "Join Output Files")
        self.join_output_tree.pack(side=tk.RIGHT, fill='both', expand=True, padx=5)
        
        # Button frame
        button_frame = ttk.Frame(join_tab)
        button_frame.pack(pady=10)
        
        # Join button with tooltip
        join_btn = ttk.Button(button_frame, text="Auto-Join Segmented Files", 
                            command=self.auto_join_files)
        self.create_tooltip(join_btn, "Join files with _part1, _part2, etc. naming pattern")
        join_btn.pack(side=tk.LEFT, padx=10)
        
        # New Convert to M4A button with tooltip
        convert_m4a_btn = ttk.Button(button_frame, text="Convert Output to M4A", 
                                   command=self.convert_output_to_m4a)
        self.create_tooltip(convert_m4a_btn, 
                          f"Convert all joined WAV files to M4A format (320k CBR)")
        convert_m4a_btn.pack(side=tk.LEFT, padx=10)

    def create_convert_tab(self):
        convert_tab = ttk.Frame(self.notebook)
        self.notebook.add(convert_tab, text="Convert")
        
        # Info label
        info_label = ttk.Label(convert_tab, 
                             text="Convert individual files between WAV and M4A formats",
                             style="Info.TLabel")
        info_label.pack(pady=(10, 5))
        
        # File selection frame
        file_frame = ttk.Frame(convert_tab)
        file_frame.pack(fill='x', pady=5)
        
        # File and folder selection with labels
        ttk.Label(file_frame, text="Input File:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.convert_input_path = ttk.Label(file_frame, text="Not selected", style="Info.TLabel")
        self.convert_input_path.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(file_frame, text="Select Input File",
                  command=self.select_convert_file).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Output Folder:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.convert_output_path = ttk.Label(file_frame, text="Not selected", style="Info.TLabel")
        self.convert_output_path.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(file_frame, text="Select Output Folder",
                  command=lambda: self.select_folder("convert_output")).grid(row=1, column=2, padx=5, pady=5)
        
        # File views in a frame
        view_frame = ttk.Frame(convert_tab)
        view_frame.pack(fill='both', expand=True, pady=5)
        
        # File and output viewers
        self.convert_input_tree = self.create_file_tree(view_frame, "Input File")
        self.convert_input_tree.pack(side=tk.LEFT, fill='both', expand=True, padx=5)
        
        self.convert_output_tree = self.create_file_tree(view_frame, "Output Folder")
        self.convert_output_tree.pack(side=tk.RIGHT, fill='both', expand=True, padx=5)
        
        # Convert button with tooltip
        convert_btn = ttk.Button(convert_tab, text="Convert File", 
                               command=self.convert_file)
        self.create_tooltip(convert_btn, "Convert between WAV and M4A formats (M4A uses 320k CBR)")
        convert_btn.pack(pady=10)

    def create_settings_tab(self):
        settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(settings_tab, text="Settings")
        
        # Main settings frame
        settings_frame = ttk.LabelFrame(settings_tab, text="Conversion Settings")
        settings_frame.pack(padx=20, pady=20, fill='x')
        
        # Bitrate info
        ttk.Label(settings_frame, text="M4A Bitrate: 320k (constant bit rate)").grid(
            row=0, column=0, padx=5, pady=10, sticky='w')
        
        # Threading info - ensure self.max_workers is defined first
        worker_count = getattr(self, 'max_workers', 2)  # Default to 2 if not defined
        ttk.Label(settings_frame, text=f"Multi-threading: Using {worker_count} worker threads").grid(
            row=1, column=0, padx=5, pady=10, sticky='w')
        
        # Performance tips
        perf_frame = ttk.LabelFrame(settings_tab, text="Performance Information")
        perf_frame.pack(padx=20, pady=10, fill='x')
        
        perf_info = (
            f"• Using direct FFmpeg calls for maximum performance\n"
            f"• Processing {worker_count} files simultaneously\n"
            f"• Files are processed directly from disk (no memory overhead)\n"
            f"• All WAV to M4A conversions use 320k CBR (constant bit rate)"
        )
        
        ttk.Label(perf_frame, text=perf_info).pack(anchor='w', padx=10, pady=10)
        
        # Quality info
        quality_frame = ttk.LabelFrame(settings_tab, text="Audio Quality Information")
        quality_frame.pack(padx=20, pady=10, fill='x')
        
        quality_info = (
            "• WAV: Uncompressed audio, maximum quality\n"
            "• M4A: Compressed audio using AAC at 320k CBR\n"
            "• M4A files are typically 3-5x smaller than WAV with minimal quality loss"
        )
        
        ttk.Label(quality_frame, text=quality_info).pack(anchor='w', padx=10, pady=10)
        
        # Debug mode checkbox (hidden feature)
        debug_frame = ttk.Frame(settings_tab)
        debug_frame.pack(padx=20, pady=10, fill='x')
        
        self.debug_var = tk.IntVar(value=0)
        debug_cb = ttk.Checkbutton(debug_frame, text="Debug Mode (verbose logging)", 
                                 variable=self.debug_var,
                                 command=self.toggle_debug_mode)
        debug_cb.pack(anchor='w')

    def toggle_debug_mode(self):
        """Toggle debug mode on/off"""
        self.debug_mode = bool(self.debug_var.get())
        if self.debug_mode:
            self.show_status("Debug mode enabled - verbose logging will be shown")
        else:
            self.show_status("Debug mode disabled")

    def debug_print(self, message):
        """Print debug messages when debug mode is enabled"""
        if self.debug_mode:
            print(f"DEBUG: {message}")
            self.show_status(f"DEBUG: {message}")

    def create_file_tree(self, parent, title):
        frame = ttk.LabelFrame(parent, text=title)
        
        # Add count label at top of frame
        self.count_var = tk.StringVar(value="0 files")
        count_label = ttk.Label(frame, textvariable=self.count_var, style="Info.TLabel")
        count_label.pack(anchor='e', padx=5)
        
        # Create treeview with scrollbar
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill='both', expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=('name', 'size'), show='headings', height=8)
        tree.heading('name', text='File Name')
        tree.heading('size', text='Size (MB)')
        tree.column('name', width=250)
        tree.column('size', width=80)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store the count_var in the frame for later access
        frame.count_var = self.count_var
        
        return frame

    def create_tooltip(self, widget, text):
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create tooltip window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(self.tooltip, text=text, background="#ffffe0", 
                             relief="solid", borderwidth=1, padding=2)
            label.pack()
            
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def setup_folder_views(self):
        # Initialize folder views from config
        self.update_folder_view("split_input")
        self.update_folder_view("split_output")
        self.update_folder_view("join_input")
        self.update_folder_view("join_output")
        self.update_folder_view("convert_output")
        
        # Update path labels
        self.update_path_labels()

    def update_path_labels(self):
        """Update all path labels with current folder paths"""
        # Split tab
        split_input = self.config.get("split_input", "")
        self.split_input_path.config(text=self.shorten_path(split_input) if split_input else "Not selected")
        
        split_output = self.config.get("split_output", "")
        self.split_output_path.config(text=self.shorten_path(split_output) if split_output else "Not selected")
        
        # Join tab
        join_input = self.config.get("join_input", "")
        self.join_input_path.config(text=self.shorten_path(join_input) if join_input else "Not selected")
        
        join_output = self.config.get("join_output", "")
        self.join_output_path.config(text=self.shorten_path(join_output) if join_output else "Not selected")
        
        # Convert tab
        convert_input = self.config.get("convert_input", "")
        self.convert_input_path.config(text=self.shorten_path(convert_input) if convert_input else "Not selected")
        
        convert_output = self.config.get("convert_output", "")
        self.convert_output_path.config(text=self.shorten_path(convert_output) if convert_output else "Not selected")

    def shorten_path(self, path):
        """Shorten long paths for display"""
        if len(path) > 40:
            return "..." + path[-37:]
        return path

    def select_folder(self, folder_type):
        path = filedialog.askdirectory()
        if path:
            self.config[folder_type] = path
            self.save_config()
            self.update_folder_view(folder_type)
            self.update_path_labels()
            self.show_status(f"{folder_type.replace('_', ' ').title()} updated to: {path}")

    def update_folder_view(self, folder_type):
        trees = {
            "split_input": self.split_input_tree,
            "split_output": self.split_output_tree,
            "join_input": self.join_input_tree,
            "join_output": self.join_output_tree,
            "convert_output": self.convert_output_tree
        }
        
        target_tree = trees.get(folder_type)
        if not target_tree:
            return
            
        path = self.config.get(folder_type, "")
        
        # Get the treeview widget
        tree_widget = target_tree.winfo_children()[1].winfo_children()[0]
        
        # Clear existing items
        for item in tree_widget.get_children():
            tree_widget.delete(item)
        
        # Populate with new items
        file_count = 0
        if os.path.exists(path):
            for f in os.listdir(path):
                full_path = os.path.join(path, f)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path) / (1024 * 1024)  # MB
                    tree_widget.insert('', 'end', values=(f, f"{size:.2f}"))
                    file_count += 1
        
        # Update file count
        target_tree.count_var.set(f"{file_count} files")

    # Threading support for UI responsiveness
    def enable_cancel_button(self):
        """Enable the cancel button during operations"""
        self.cancel_btn.config(state=tk.NORMAL)
    
    def disable_cancel_button(self):
        """Disable the cancel button when no operation is running"""
        self.cancel_btn.config(state=tk.DISABLED)
    
    def cancel_operation(self):
        """Signal the running thread to stop"""
        self.stop_conversion = True
        self.show_status("Cancelling operation... please wait")
    
    def update_progress(self, value, status_text=None):
        """Safely update progress from any thread"""
        self.progress_var.set(value)
        if status_text:
            self.progress_label.config(text=status_text)
            self.show_status(status_text)
        self.root.update_idletasks()

    # Check if ffmpeg is installed
    def check_ffmpeg(self):
        """Check if ffmpeg is installed and available"""
        try:
            # Run ffmpeg with -version to check if it's available
            subprocess.run(['ffmpeg', '-version'], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE, 
                         check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            messagebox.showerror("FFmpeg Not Found", 
                               "FFmpeg is required but not found in your system PATH.\n\n"
                               "Please install FFmpeg and make sure it's in your PATH.")
            return False

    # Process file conversion results from thread pool
    def process_conversion_results(self):
        """Process results from the thread pool and update progress"""
        if not self.futures:
            return
            
        # Check if all futures are done
        all_done = all(future.done() for future in self.futures)
        cancelled = self.stop_conversion
        
        # Count completed conversions
        completed = sum(1 for future in self.futures if future.done())
        
        # Update progress
        if self.total_files > 0:
            progress = (completed / self.total_files) * 100
            self.update_progress(progress, f"Processed {completed}/{self.total_files} files")
        
        # If all done or cancelled, clean up
        if all_done or cancelled:
            # Collect any errors
            errors = []
            for future in self.futures:
                if future.done() and not future.cancelled():
                    try:
                        result = future.result()
                        if result and isinstance(result, str) and "error" in result.lower():
                            errors.append(result)
                    except Exception as e:
                        errors.append(str(e))
            
            # Show final status
            if cancelled:
                self.update_progress(0, "Operation cancelled")
                messagebox.showinfo("Operation Cancelled", "The operation was cancelled.")
            elif errors:
                self.update_progress(100, f"Completed with {len(errors)} errors")
                error_msg = "\n".join(errors[:5])  # Show first 5 errors
                if len(errors) > 5:
                    error_msg += f"\n... and {len(errors) - 5} more errors"
                messagebox.showwarning("Completed with Errors", 
                                     f"Operation completed with {len(errors)} errors:\n\n{error_msg}")
            else:
                self.update_progress(100, "Operation completed successfully")
                messagebox.showinfo("Operation Complete", 
                                  f"Successfully processed {self.processed_count} files.")
            
            # Reset after a delay
            self.root.after(2000, lambda: self.update_progress(0, "Ready"))
            self.disable_cancel_button()
            self.stop_conversion = False
            self.futures = []
            self.total_files = 0
        else:
            # Schedule another check
            self.root.after(100, self.process_conversion_results)

    # New implementation: Convert WAV to M4A using FFmpeg directly
    def convert_wav_to_m4a(self, input_file, output_file):
        """Convert WAV to M4A using FFmpeg directly"""
        try:
            if self.stop_conversion:
                return "Cancelled"
                
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', input_file,           # Input file
                '-c:a', 'aac',              # AAC codec
                '-b:a', '320k',             # 320k bitrate (CBR)
                '-map_metadata', '0',       # Copy metadata
                '-movflags', '+faststart',  # Optimize for streaming
                '-y',                        # Overwrite output if exists
                output_file                  # Output file
            ]
            
            # Run the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            return "Success"
        except subprocess.CalledProcessError as e:
            self.debug_print(f"FFmpeg error: {e.stderr}")
            return f"Error converting {os.path.basename(input_file)}: FFmpeg error"
        except Exception as e:
            self.debug_print(f"Exception: {str(e)}")
            return f"Error converting {os.path.basename(input_file)}: {str(e)}"

    # New implementation: Convert to WAV using FFmpeg directly
    def convert_to_wav(self, input_file, output_file):
        """Convert any audio file to WAV using FFmpeg directly"""
        try:
            if self.stop_conversion:
                return "Cancelled"
                
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', input_file,           # Input file
                '-c:a', 'pcm_s16le',        # PCM 16-bit codec
                '-map_metadata', '0',       # Copy metadata
                '-y',                        # Overwrite output if exists
                output_file                  # Output file
            ]
            
            # Run the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            return "Success"
        except subprocess.CalledProcessError as e:
            self.debug_print(f"FFmpeg error: {e.stderr}")
            return f"Error converting {os.path.basename(input_file)}: FFmpeg error"
        except Exception as e:
            self.debug_print(f"Exception: {str(e)}")
            return f"Error converting {os.path.basename(input_file)}: {str(e)}"
    
    # New function to convert all WAV files to M4A with multithreading
    def convert_output_to_m4a(self):
        output_folder = self.config.get("join_output", "")
        
        if not output_folder:
            messagebox.showerror("Error", "Please select an output folder first!")
            return
            
        # Check if ffmpeg is available
        if not self.check_ffmpeg():
            return
        
        # Don't start a new conversion if one is already running
        if self.current_conversion_thread and self.current_conversion_thread.is_alive():
            messagebox.showinfo("Conversion in Progress", "A conversion is already running. Please wait for it to complete.")
            return
            
        # Start conversion in a separate thread
        self.stop_conversion = False
        self.enable_cancel_button()
        self.current_conversion_thread = threading.Thread(
            target=self._convert_output_to_m4a_thread, 
            args=(output_folder,)
        )
        self.current_conversion_thread.daemon = True
        self.current_conversion_thread.start()

    def _convert_output_to_m4a_thread(self, output_folder):
        """Background thread for WAV to M4A conversion with multiprocessing"""
        try:
            # Get all WAV files
            wav_files = [f for f in os.listdir(output_folder) 
                       if os.path.isfile(os.path.join(output_folder, f)) and 
                       f.lower().endswith('.wav')]
            
            self.total_files = len(wav_files)
            self.processed_count = 0
            
            if self.total_files == 0:
                def show_no_files():
                    messagebox.showinfo("No WAV Files", "No WAV files found in the output folder.")
                    self.disable_cancel_button()
                self.root.after(0, show_no_files)
                return
                
            # Reset progress bar and start processing
            self.root.after(0, lambda: self.update_progress(0, "Starting conversion..."))
            
            # Create a thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit conversion tasks
                self.futures = []
                for filename in wav_files:
                    if self.stop_conversion:
                        break
                        
                    input_path = os.path.join(output_folder, filename)
                    base_name = os.path.splitext(filename)[0]
                    output_path = os.path.join(output_folder, f"{base_name}.m4a")
                    
                    future = executor.submit(self.convert_wav_to_m4a, input_path, output_path)
                    self.futures.append(future)
                
                # Start monitoring progress
                self.root.after(100, self.process_conversion_results)
                
                # Wait for completion (this is running in a background thread)
                for i, future in enumerate(concurrent.futures.as_completed(self.futures)):
                    if self.stop_conversion:
                        for f in self.futures:
                            if not f.done():
                                f.cancel()
                        break
                    
                    result = future.result()
                    if result == "Success":
                        self.processed_count += 1
                        
        except Exception as e:
            self.debug_print(f"Critical error in conversion thread: {str(e)}")
            self.debug_print(traceback.format_exc())
            
            # Show error in main thread
            def show_error():
                messagebox.showerror("Error", str(e))
                self.update_progress(0, "Error occurred")
                self.disable_cancel_button()
            self.root.after(0, show_error)

    # New implementation: Convert all files to WAV with multithreading
    def convert_all_to_wav(self):
        input_folder = self.config.get("split_input", "")
        
        if not input_folder:
            messagebox.showerror("Error", "Please select an input folder first!")
            return
            
        # Check if ffmpeg is available
        if not self.check_ffmpeg():
            return
            
        # Don't start a new conversion if one is already running
        if self.current_conversion_thread and self.current_conversion_thread.is_alive():
            messagebox.showinfo("Conversion in Progress", "A conversion is already running. Please wait for it to complete.")
            return
            
        # Start conversion in a separate thread
        self.stop_conversion = False
        self.enable_cancel_button()
        self.current_conversion_thread = threading.Thread(
            target=self._convert_all_to_wav_thread, 
            args=(input_folder,)
        )
        self.current_conversion_thread.daemon = True
        self.current_conversion_thread.start()

    def _convert_all_to_wav_thread(self, input_folder):
        """Background thread for conversion to WAV with multiprocessing"""
        try:
            # Get all non-WAV audio files
            files = [f for f in os.listdir(input_folder) 
                   if os.path.isfile(os.path.join(input_folder, f)) and 
                   not f.lower().endswith('.wav') and
                   f.lower().endswith(('.mp3', '.m4a', '.aac', '.ogg', '.flac'))]
            
            self.total_files = len(files)
            self.processed_count = 0
            
            if self.total_files == 0:
                def show_no_files():
                    messagebox.showinfo("No Files to Convert", 
                        "No non-WAV audio files found in the input folder.")
                    self.disable_cancel_button()
                self.root.after(0, show_no_files)
                return
                
            # Reset progress bar and start processing
            self.root.after(0, lambda: self.update_progress(0, "Starting conversion..."))
            
            # Create a thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit conversion tasks
                self.futures = []
                for filename in files:
                    if self.stop_conversion:
                        break
                        
                    input_path = os.path.join(input_folder, filename)
                    base_name = os.path.splitext(filename)[0]
                    output_path = os.path.join(input_folder, f"{base_name}.wav")
                    
                    future = executor.submit(self.convert_to_wav, input_path, output_path)
                    self.futures.append(future)
                
                # Start monitoring progress
                self.root.after(100, self.process_conversion_results)
                
                # Wait for completion (this is running in a background thread)
                for i, future in enumerate(concurrent.futures.as_completed(self.futures)):
                    if self.stop_conversion:
                        for f in self.futures:
                            if not f.done():
                                f.cancel()
                        break
                    
                    result = future.result()
                    if result == "Success":
                        self.processed_count += 1
                        
                # Update folder view
                if not self.stop_conversion:
                    self.root.after(0, lambda: self.update_folder_view("split_input"))
                    
        except Exception as e:
            self.debug_print(f"Critical error in conversion thread: {str(e)}")
            self.debug_print(traceback.format_exc())
            
            # Show error in main thread
            def show_error():
                messagebox.showerror("Error", str(e))
                self.update_progress(0, "Error occurred")
                self.disable_cancel_button()
            self.root.after(0, show_error)

    # Split files function using ffmpeg
    def split_files(self):
        input_folder = self.config.get("split_input", "")
        output_folder = self.config.get("split_output", "")
        
        if not input_folder or not output_folder:
            messagebox.showerror("Error", "Please select both input and output folders!")
            return
            
        # Check if ffmpeg is available
        if not self.check_ffmpeg():
            return
            
        # Don't start a new operation if one is already running
        if self.current_conversion_thread and self.current_conversion_thread.is_alive():
            messagebox.showinfo("Operation in Progress", "An operation is already running. Please wait for it to complete.")
            return
            
        # Start splitting in a separate thread
        self.stop_conversion = False
        self.enable_cancel_button()
        self.current_conversion_thread = threading.Thread(
            target=self._split_files_thread, 
            args=(input_folder, output_folder)
        )
        self.current_conversion_thread.daemon = True
        self.current_conversion_thread.start()

    def split_audio_file(self, input_file, output_pattern, segment_length=12):
        """Split audio file into segments using ffmpeg"""
        try:
            if self.stop_conversion:
                return "Cancelled"
                
            # Build FFmpeg command for segmenting
            cmd = [
                'ffmpeg',
                '-i', input_file,                   # Input file
                '-f', 'segment',                    # Use segment muxer
                '-segment_time', str(segment_length * 60),  # Segment length in seconds
                '-c', 'copy',                       # Copy streams (no re-encoding)
                '-map', '0',                        # Map all streams
                '-reset_timestamps', '1',           # Reset timestamps for each segment
                '-y',                               # Overwrite output if exists
                output_pattern                      # Output pattern
            ]
            
            # Run the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # Count segments
            output_dir = os.path.dirname(output_pattern)
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            segment_count = len([f for f in os.listdir(output_dir) 
                               if f.startswith(f"{base_name}_part") and f.endswith(".wav")])
            
            return f"Split into {segment_count} parts"
        except subprocess.CalledProcessError as e:
            self.debug_print(f"FFmpeg error: {e.stderr}")
            return f"Error splitting {os.path.basename(input_file)}: FFmpeg error"
        except Exception as e:
            self.debug_print(f"Exception: {str(e)}")
            return f"Error splitting {os.path.basename(input_file)}: {str(e)}"

    def _split_files_thread(self, input_folder, output_folder):
        """Background thread for splitting files"""
        try:
            # Get all WAV files
            wav_files = [f for f in os.listdir(input_folder) 
                       if os.path.isfile(os.path.join(input_folder, f)) and 
                       f.lower().endswith('.wav')]
            
            self.total_files = len(wav_files)
            self.processed_count = 0
            
            if self.total_files == 0:
                def show_no_files():
                    messagebox.showwarning("No WAV Files", "No WAV files found in input folder")
                    self.disable_cancel_button()
                self.root.after(0, show_no_files)
                return
                
            # Reset progress bar
            self.root.after(0, lambda: self.update_progress(0, "Starting splitting operation..."))
            
            # Create a thread pool with fewer workers for splitting
            # (splitting can be more resource-intensive)
            max_workers_split = max(1, min(self.max_workers, 3))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_split) as executor:
                # Submit splitting tasks
                self.futures = []
                for filename in wav_files:
                    if self.stop_conversion:
                        break
                        
                    input_path = os.path.join(input_folder, filename)
                    base_name = os.path.splitext(filename)[0]
                    output_pattern = os.path.join(output_folder, f"{base_name}_part%03d.wav")
                    
                    # For each file, we need to split it into segments
                    future = executor.submit(self.split_audio_file, input_path, output_pattern)
                    self.futures.append(future)
                
                # Start monitoring progress
                self.root.after(100, self.process_conversion_results)
                
                # Wait for completion (this is running in a background thread)
                for i, future in enumerate(concurrent.futures.as_completed(self.futures)):
                    if self.stop_conversion:
                        for f in self.futures:
                            if not f.done():
                                f.cancel()
                        break
                    
                    result = future.result()
                    if "Error" not in result and "Cancelled" not in result:
                        self.processed_count += 1
                        
                # Update folder view
                if not self.stop_conversion:
                    self.root.after(0, lambda: self.update_folder_view("split_output"))
                    
        except Exception as e:
            self.debug_print(f"Critical error in splitting thread: {str(e)}")
            self.debug_print(traceback.format_exc())
            
            # Show error in main thread
            def show_error():
                messagebox.showerror("Error", str(e))
                self.update_progress(0, "Error occurred")
                self.disable_cancel_button()
            self.root.after(0, show_error)

    # Join the segmented files using ffmpeg
    def join_audio_files(self, file_list, output_file):
        """Join audio files using ffmpeg"""
        try:
            if self.stop_conversion:
                return "Cancelled"
                
            # Create a temporary file list
            temp_list_file = output_file + ".list"
            with open(temp_list_file, 'w') as f:
                for file_path in file_list:
                    f.write(f"file '{file_path}'\n")
            
            # Build FFmpeg command for joining
            cmd = [
                'ffmpeg',
                '-f', 'concat',                # Use concat demuxer
                '-safe', '0',                  # Allow unsafe file paths
                '-i', temp_list_file,          # Input from list file
                '-c', 'copy',                  # Copy streams (no re-encoding)
                '-y',                          # Overwrite output if exists
                output_file                    # Output file
            ]
            
            # Run the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # Clean up temporary file
            os.remove(temp_list_file)
            
            return "Success"
        except subprocess.CalledProcessError as e:
            self.debug_print(f"FFmpeg error: {e.stderr}")
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)
            return f"Error joining files: FFmpeg error"
        except Exception as e:
            self.debug_print(f"Exception: {str(e)}")
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)
            return f"Error joining files: {str(e)}"

    def auto_join_files(self):
        input_folder = self.config.get("join_input", "")
        output_folder = self.config.get("join_output", "")
        
        if not input_folder or not output_folder:
            messagebox.showerror("Error", "Please select both input and output folders!")
            return
            
        # Check if ffmpeg is available
        if not self.check_ffmpeg():
            return
            
        # Don't start a new operation if one is already running
        if self.current_conversion_thread and self.current_conversion_thread.is_alive():
            messagebox.showinfo("Operation in Progress", "An operation is already running. Please wait for it to complete.")
            return
            
        # Start joining in a separate thread
        self.stop_conversion = False
        self.enable_cancel_button()
        self.current_conversion_thread = threading.Thread(
            target=self._auto_join_files_thread, 
            args=(input_folder, output_folder)
        )
        self.current_conversion_thread.daemon = True
        self.current_conversion_thread.start()

    def _auto_join_files_thread(self, input_folder, output_folder):
        """Background thread for joining files"""
        try:
            # Group files by fileID
            file_groups = {}
            for filename in os.listdir(input_folder):
                if filename.lower().endswith('.wav') and '_part' in filename:
                    parts = filename.split('_part')
                    if len(parts) == 2:
                        part_num_str = parts[1].split('.')[0]
                        # Check if part number is numeric
                        if part_num_str.isdigit() or (part_num_str.startswith('0') and part_num_str[1:].isdigit()):
                            file_id = parts[0]
                            try:
                                part_num = int(part_num_str)
                                file_groups.setdefault(file_id, []).append((part_num, filename))
                            except ValueError:
                                # Skip if part number isn't a valid integer
                                continue
            
            self.total_files = len(file_groups)
            self.processed_count = 0
            
            if self.total_files == 0:
                def show_no_files():
                    messagebox.showwarning("No Files Found", 
                        "No segmented files found with pattern [name]_part[number].wav")
                    self.disable_cancel_button()
                self.root.after(0, show_no_files)
                return
                
            # Reset progress bar
            self.root.after(0, lambda: self.update_progress(0, "Starting join operation..."))
            
            # Process each group one at a time (joining is sequential by nature)
            # but we can process multiple groups concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                self.futures = []
                
                for file_id, parts in file_groups.items():
                    if self.stop_conversion:
                        break
                    
                    # Sort parts numerically
                    parts.sort()
                    
                    # Create list of full file paths in order
                    file_paths = [os.path.join(input_folder, filename) for _, filename in parts]
                    output_path = os.path.join(output_folder, f"{file_id}_joined.wav")
                    
                    # Submit job to thread pool
                    future = executor.submit(self.join_audio_files, file_paths, output_path)
                    self.futures.append(future)
                
                # Start monitoring progress
                self.root.after(100, self.process_conversion_results)
                
                # Wait for completion (this is running in a background thread)
                for future in concurrent.futures.as_completed(self.futures):
                    if self.stop_conversion:
                        for f in self.futures:
                            if not f.done():
                                f.cancel()
                        break
                        
                    result = future.result()
                    if result == "Success":
                        self.processed_count += 1
                
                # Update folder view
                if not self.stop_conversion:
                    self.root.after(0, lambda: self.update_folder_view("join_output"))
                
        except Exception as e:
            self.debug_print(f"Critical error in join thread: {str(e)}")
            self.debug_print(traceback.format_exc())
            
            # Show error in main thread
            def show_error():
                messagebox.showerror("Error", str(e))
                self.update_progress(0, "Error occurred")
                self.disable_cancel_button()
            self.root.after(0, show_error)

    def select_convert_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav *.m4a *.mp3 *.aac *.ogg *.flac")]
        )
        if file_path:
            self.config["convert_input"] = file_path
            self.save_config()
            self.update_convert_input_view()
            self.update_path_labels()
            self.show_status(f"Selected file: {os.path.basename(file_path)}")

    def update_convert_input_view(self):
        tree = self.convert_input_tree.winfo_children()[1].winfo_children()[0]
        for item in tree.get_children():
            tree.delete(item)
        
        if "convert_input" in self.config:
            file_path = self.config["convert_input"]
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path) / (1024 * 1024)
                tree.insert('', 'end', values=(os.path.basename(file_path), f"{size:.2f}"))
                self.convert_input_tree.count_var.set("1 file")
            else:
                self.convert_input_tree.count_var.set("0 files")

    def convert_file(self):
        input_file = self.config.get("convert_input", "")
        output_folder = self.config.get("convert_output", "")
        
        if not input_file or not output_folder:
            messagebox.showerror("Error", "Please select both input file and output folder!")
            return
            
        # Check if ffmpeg is available
        if not self.check_ffmpeg():
            return
            
        # Don't start a new operation if one is already running
        if self.current_conversion_thread and self.current_conversion_thread.is_alive():
            messagebox.showinfo("Operation in Progress", "An operation is already running. Please wait for it to complete.")
            return
            
        # Start conversion in a separate thread
        self.stop_conversion = False
        self.enable_cancel_button()
        self.current_conversion_thread = threading.Thread(
            target=self._convert_file_thread, 
            args=(input_file, output_folder)
        )
        self.current_conversion_thread.daemon = True
        self.current_conversion_thread.start()

    def _convert_file_thread(self, input_file, output_folder):
        """Background thread for single file conversion"""
        try:
            # Determine conversion direction
            input_ext = os.path.splitext(input_file)[1].lower()
            filename = os.path.basename(input_file)
            base_name = os.path.splitext(filename)[0]

            if input_ext == ".wav":
                output_ext = ".m4a"
                output_path = os.path.join(output_folder, f"{base_name}_converted{output_ext}")
                conversion_type = "WAV to M4A"
                # Convert WAV to M4A
                self.total_files = 1
                self.processed_count = 0
                
                # Reset progress
                self.root.after(0, lambda: self.update_progress(0, f"Converting {filename} to M4A..."))
                
                # Run conversion
                result = self.convert_wav_to_m4a(input_file, output_path)
                
                if result == "Success":
                    self.processed_count = 1
                    self.root.after(0, lambda: self.update_progress(100, f"Converted {filename} to M4A"))
                    
                    # Show success
                    self.root.after(0, lambda: messagebox.showinfo("Success", 
                        f"Conversion completed successfully!\n"
                        f"Conversion: {conversion_type} (320k CBR)\n"
                        f"Output file: {os.path.basename(output_path)}"))
                    
                    # Update folder view
                    self.root.after(0, lambda: self.update_folder_view("convert_output"))
                else:
                    # Show error
                    self.root.after(0, lambda: messagebox.showerror("Error", result))
            else:
                # Convert to WAV
                output_ext = ".wav"
                output_path = os.path.join(output_folder, f"{base_name}_converted{output_ext}")
                conversion_type = f"{input_ext[1:].upper()} to WAV"
                
                self.total_files = 1
                self.processed_count = 0
                
                # Reset progress
                self.root.after(0, lambda: self.update_progress(0, f"Converting {filename} to WAV..."))
                
                # Run conversion
                result = self.convert_to_wav(input_file, output_path)
                
                if result == "Success":
                    self.processed_count = 1
                    self.root.after(0, lambda: self.update_progress(100, f"Converted {filename} to WAV"))
                    
                    # Show success
                    self.root.after(0, lambda: messagebox.showinfo("Success", 
                        f"Conversion completed successfully!\n"
                        f"Conversion: {conversion_type}\n"
                        f"Output file: {os.path.basename(output_path)}"))
                    
                    # Update folder view
                    self.root.after(0, lambda: self.update_folder_view("convert_output"))
                else:
                    # Show error
                    self.root.after(0, lambda: messagebox.showerror("Error", result))
            
            # Reset after a delay
            self.root.after(2000, lambda: self.update_progress(0, "Ready"))
            self.disable_cancel_button()

        except Exception as e:
            self.debug_print(f"Critical error in conversion thread: {str(e)}")
            self.debug_print(traceback.format_exc())
            
            # Show error in main thread
            def show_error():
                messagebox.showerror("Error", str(e))
                self.update_progress(0, "Error occurred")
                self.disable_cancel_button()
            self.root.after(0, show_error)

    # Configuration handling
    def load_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "split_input": "",
            "split_output": "",
            "join_input": "",
            "join_output": "",
            "convert_input": "",
            "convert_output": "",
            "m4a_bitrate": "320k"  # Hardcoded to 320k
        }

    def save_config(self):
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def show_status(self, message):
        self.status.config(text=message)
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioToolApp(root)
    root.mainloop()