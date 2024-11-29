import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import asyncio
import logging
import subprocess
import threading
from pathlib import Path
import os
import json
from typing import Optional

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.FileHandler('music_downloader.log'), logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

class MusicDownloaderApp:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Music Downloader")
        self.window.geometry("800x600")
        
        # Theme settings
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Configuration
        self.config = self.load_config()
        
        # Create asyncio event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Status label for download progress
        self.status_var = tk.StringVar(value="Ready")
        
        # Initialize downloaded_songs
        self.downloaded_songs = []
        
        self.setup_ui()
        
        # Check for FFmpeg installation
        self.check_ffmpeg()

    def check_ffmpeg(self):
        """Check if FFmpeg is installed and available in PATH."""
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            logger.info("FFmpeg is available.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", "FFmpeg is not installed or not found in PATH.")
            logger.error("FFmpeg is not installed or not found in PATH.")
            self.window.destroy()

    def load_config(self) -> dict:
        """Load configuration from config.json or create default"""
        config_path = Path("config.json")
        default_config = {
            "output_dir": "downloads",
            "converted_dir": "converted",
            "supported_formats": ["mp3", "wav", "m4a", "flac"],
            "default_format": "mp3",
            "max_concurrent_downloads": 3,
            "spotify_bitrate": "128k",
            "spotify_threads": 4
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                # Update with default_config to add any missing keys
                config = {**default_config, **config}
                return config
            return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            return default_config

    def setup_ui(self):
        """Set up the main UI components"""
        self.main_container = ctk.CTkFrame(self.window)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Welcome screen
        self.welcome_frame = self.create_welcome_frame()
        self.download_frame = self.create_download_frame()
        
        # Initially show welcome screen
        self.show_welcome_screen()

    def create_welcome_frame(self) -> ctk.CTkFrame:
        """Create the welcome screen frame"""
        frame = ctk.CTkFrame(self.main_container)
        
        # Welcome message
        welcome_label = ctk.CTkLabel(
            frame,
            text="Welcome to Music Downloader",
            font=("Helvetica", 24, "bold")
        )
        welcome_label.pack(pady=20)
        
        # Platform selection
        platform_frame = ctk.CTkFrame(frame)
        platform_frame.pack(pady=20)
        
        ctk.CTkLabel(
            platform_frame,
            text="Select your music platform:",
            font=("Helvetica", 16)
        ).pack(pady=10)
        
        # Platform buttons
        ctk.CTkButton(
            platform_frame,
            text="Yandex Music",
            command=lambda: self.select_platform("yandex")
        ).pack(pady=5)
        
        ctk.CTkButton(
            platform_frame,
            text="Spotify",
            command=lambda: self.select_platform("spotify")
        ).pack(pady=5)
        
        return frame
        
    def create_download_frame(self) -> ctk.CTkFrame:
        """Create the download interface frame"""
        frame = ctk.CTkFrame(self.main_container)
        
        # URL input
        self.url_var = tk.StringVar()
        url_frame = ctk.CTkFrame(frame)
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(url_frame, text="Song URL:").pack(side=tk.LEFT, padx=5)
        ctk.CTkEntry(url_frame, textvariable=self.url_var, width=300).pack(side=tk.LEFT, padx=5)
        
        # Token input
        self.token_var = tk.StringVar()
        token_frame = ctk.CTkFrame(frame)
        token_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(token_frame, text="API Token:").pack(side=tk.LEFT, padx=5)
        self.token_entry = ctk.CTkEntry(token_frame, textvariable=self.token_var, width=300, show="*")
        self.token_entry.pack(side=tk.LEFT, padx=5)
        
        # Status label
        ctk.CTkLabel(frame, textvariable=self.status_var).pack(pady=5)
        
        # Downloaded songs list
        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.songs_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#1f538d",
            height=15
        )
        self.songs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.songs_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.songs_listbox.yview)
        
        # Control buttons
        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkButton(button_frame, text="Download", command=self.start_download).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(button_frame, text="Convert", command=self.show_convert_dialog).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(button_frame, text="Clear List", command=self.clear_list).pack(side=tk.LEFT, padx=5)
        
        return frame

    async def initialize_yandex_client(self, token: str):
        """Initialize Yandex Music client"""
        try:
            self.yandex_client = await ClientAsync(token).init()
            logger.info("Yandex Music client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Yandex Music client: {e}", exc_info=True)
            messagebox.showerror("Error", "Failed to initialize Yandex Music client")
            raise

    def download_spotify_track(self, url: str) -> Optional[str]:
        """Download a track from Spotify using spotdl command line"""
        try:
            output_dir = Path(self.config["output_dir"])
            output_dir.mkdir(exist_ok=True)
            
            logger.info(f"Starting Spotify download for URL: {url}")
            
            # Check if spotdl is installed
            try:
                subprocess.run(["spotdl", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                error_msg = "spotdl is not installed. Please install it using: pip install spotdl"
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)
                return None
            
            # Prepare spotdl command
            command = [
                "spotdl",
                "download",
                url,
                "--format", "mp3",
                "--bitrate", self.config["spotify_bitrate"],
                "--output", str(output_dir),
                "--preload",
                "--threads", str(self.config["spotify_threads"])
            ]
            
            logger.debug(f"Executing command: {' '.join(command)}")
            
            # Run spotdl command and capture output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Update status while downloading
            self.status_var.set("Downloading from Spotify...")
            
            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    logger.info(f"spotdl output: {output.strip()}")
                    self.status_var.set(f"Download progress: {output.strip()}")
            
            # Get the return code
            return_code = process.wait()
            
            if return_code == 0:
                logger.info("Spotify download completed successfully")
                self.status_var.set("Download completed")
                # Append the downloaded file path to downloaded_songs
                downloaded_files = list(output_dir.glob("*.mp3"))
                if downloaded_files:
                    filepath = str(downloaded_files[-1])
                    self.downloaded_songs.append(filepath)
                    return filepath
            else:
                error = process.stderr.read()
                logger.error(f"Spotify download failed with code {return_code}: {error}")
                self.status_var.set("Download failed")
                messagebox.showerror("Error", f"Failed to download: {error}")
                
            return None
            
        except Exception as e:
            logger.error(f"Error downloading Spotify track: {e}", exc_info=True)
            self.status_var.set("Download failed")
            messagebox.showerror("Error", f"Failed to download: {str(e)}")
            return None

    async def download_yandex_track(self, track_id: str) -> Optional[str]:
        """Download a track from Yandex Music"""
        try:
            logger.info(f"Starting Yandex download for track ID: {track_id}")
            self.status_var.set("Downloading from Yandex Music...")
            
            track = await self.yandex_client.tracks(track_id)[0]
            full_track = await track.fetch_track_async()
            
            # Create output directory if it doesn't exist
            os.makedirs(self.config["output_dir"], exist_ok=True)
            
            # Generate filename
            filename = f"{full_track.artists[0].name} - {full_track.title}.mp3"
            filepath = os.path.join(self.config["output_dir"], filename)
            
            await full_track.download_async(filepath)
            logger.info(f"Successfully downloaded: {filename}")
            self.status_var.set("Download completed")
            # Append the downloaded file path to downloaded_songs
            self.downloaded_songs.append(filepath)
            return filepath
        except Exception as e:
            logger.error(f"Error downloading Yandex track: {e}", exc_info=True)
            self.status_var.set("Download failed")
            return None

    def start_download(self):
        """Start the download process in a separate thread"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return
            
        def download_thread():
            if self.current_platform == "yandex":
                token = self.token_var.get().strip()
                if not token:
                    messagebox.showwarning("Warning", "Please enter your Yandex Music token")
                    return
                    
                async def async_download():
                    try:
                        if not self.yandex_client:
                            await self.initialize_yandex_client(token)
                        filepath = await self.download_yandex_track(url)
                        if filepath:
                            self.window.after(0, self.refresh_file_list)
                    except Exception as e:
                        logger.error(f"Error in async download: {e}", exc_info=True)
                        self.window.after(0, messagebox.showerror, "Error", str(e))
                
                self.loop.run_until_complete(async_download())
            else:
                filepath = self.download_spotify_track(url)
                if filepath:
                    self.window.after(0, self.refresh_file_list)
        
        # Start download in separate thread
        threading.Thread(target=download_thread, daemon=True).start()

    def convert_audio(self, input_path: str, output_format: str) -> Optional[str]:
        """Convert audio file to specified format using ffmpeg with robust error handling."""
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            messagebox.showerror("Error", f"File not found: {os.path.basename(input_path)}")
            return None
        
        input_extension = os.path.splitext(input_path)[1].lstrip('.').lower()
        if input_extension == output_format.lower():
            logger.warning(f"Input and output formats are the same. Skipping conversion.")
            return input_path
        
        # Create converted directory if it doesn't exist
        converted_dir = Path(self.config["converted_dir"])
        converted_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output path in converted_dir
        output_filename = f"{os.path.basename(input_path).rsplit('.', 1)[0]}.{output_format}"
        output_path = converted_dir / output_filename
        
        try:
            command = ["ffmpeg", "-y", "-i", input_path, "-vn", str(output_path)]
            logger.debug(f"Executing ffmpeg command: {' '.join(command)}")
            
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False
            )
            
            if process.returncode == 0:
                logger.info(f"Successfully converted: {output_path}")
                self.downloaded_songs.append(str(output_path))
                self.songs_listbox.insert(tk.END, output_filename)
                return str(output_path)
            else:
                error_output = process.stderr.decode('utf-8', errors='replace')
                logger.error(f"FFmpeg error for {input_path}: {error_output}")
                messagebox.showerror("Error", f"FFmpeg conversion failed: {error_output}")
                return None
        except Exception as e:
            logger.error(f"Error converting {input_path} to {output_format}: {e}", exc_info=True)
            messagebox.showerror("Error", f"Unexpected error during conversion: {str(e)}")
            return None

    def show_convert_dialog(self):
        """Show dialog for selecting conversion format"""
        if not self.songs_listbox.curselection():
            messagebox.showwarning("Warning", "Please select songs to convert")
            return
        
        # Create a new toplevel window
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Audio Converter")
        dialog.geometry("500x600")
        
        # Make dialog modal
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Ensure dialog appears on top
        dialog.focus_set()
        dialog.lift()
        
        # Create main container
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_label = ctk.CTkLabel(
            main_frame,
            text="Convert Audio Files",
            font=("Helvetica", 20, "bold")
        )
        header_label.pack(pady=(0, 20))
        
        # Selected files section
        files_frame = ctk.CTkFrame(main_frame)
        files_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        files_label = ctk.CTkLabel(
            files_frame,
            text="Selected Files:",
            font=("Helvetica", 14, "bold")
        )
        files_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Create listbox for selected files
        files_listbox = tk.Listbox(
            files_frame,
            selectmode=tk.MULTIPLE,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#1f538d",
            height=8
        )
        files_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Add scrollbar to listbox
        scrollbar = ttk.Scrollbar(files_listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        files_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=files_listbox.yview)
        
        # Add selected files to listbox
        selected_indices = self.songs_listbox.curselection()
        for index in selected_indices:
            filename = os.path.basename(self.downloaded_songs[index])
            files_listbox.insert(tk.END, filename)
        
        # Format selection section
        format_frame = ctk.CTkFrame(main_frame)
        format_frame.pack(fill=tk.X, pady=(0, 20))
        
        format_label = ctk.CTkLabel(
            format_frame,
            text="Output Format:",
            font=("Helvetica", 14, "bold")
        )
        format_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Format selection
        format_var = tk.StringVar(value=self.config["default_format"])
        formats_container = ctk.CTkFrame(format_frame)
        formats_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        for fmt in self.config["supported_formats"]:
            ctk.CTkRadioButton(
                formats_container,
                text=fmt.upper(),
                variable=format_var,
                value=fmt,
                font=("Helvetica", 12)
            ).pack(side=tk.LEFT, padx=10)
        
        # Progress section
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        progress_var = tk.StringVar(value="")
        progress_label = ctk.CTkLabel(
            progress_frame,
            textvariable=progress_var,
            font=("Helvetica", 12)
        )
        progress_label.pack(pady=10)
        
        # Progress bar
        progress_bar = ctk.CTkProgressBar(progress_frame)
        progress_bar.pack(fill=tk.X, padx=10, pady=(0, 10))
        progress_bar.set(0)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        def cancel_conversion():
            self.conversion_cancelled = True
            dialog.destroy()
        
        def start_conversion():
            output_format = format_var.get()
            self.convert_selected_songs(output_format, dialog, progress_var, progress_bar)
        
        # Add buttons
        ctk.CTkButton(
            buttons_frame,
            text="Convert",
            command=start_conversion,
            width=120
        ).pack(side=tk.RIGHT, padx=5)
        
        ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=cancel_conversion,
            width=120
        ).pack(side=tk.RIGHT, padx=5)

    def convert_selected_songs(self, output_format: str, dialog: ctk.CTkToplevel, 
                            progress_var: tk.StringVar, progress_bar: ctk.CTkProgressBar):
        """Convert selected songs to specified format with progress tracking"""
        selected_indices = self.songs_listbox.curselection()
        total_files = len(selected_indices)
        converted_files = []
        failed_conversions = []
        self.conversion_cancelled = False  # Reset cancellation flag
        
        def conversion_task():
            try:
                for i, index in enumerate(selected_indices, 1):
                    if self.conversion_cancelled:
                        break
                    input_path = self.downloaded_songs[index]
                    if not os.path.exists(input_path):
                        logger.error(f"File not found: {input_path}")
                        self.window.after(0, lambda: progress_var.set(f"Error: File not found - {os.path.basename(input_path)}"))
                        failed_conversions.append(input_path)
                        continue
                    
                    # Update progress
                    progress = i / total_files
                    self.window.after(0, lambda p=progress: progress_bar.set(p))
                    self.window.after(0, lambda: progress_var.set(f"Converting file {i}/{total_files}: {os.path.basename(input_path)}"))
                    
                    # Convert audio
                    output_path = self.convert_audio(input_path, output_format)
                    if output_path:
                        converted_files.append(output_path)
                        self.window.after(0, lambda: self.downloaded_songs.append(output_path))
                        self.window.after(0, lambda: self.songs_listbox.insert(tk.END, os.path.basename(output_path)))
                    else:
                        failed_conversions.append(input_path)
                    
                # Show completion message
                if not self.conversion_cancelled:
                    if converted_files:
                        self.window.after(0, lambda: progress_var.set("Conversion completed successfully!"))
                        self.window.after(0, lambda: progress_bar.set(1.0))
                        self.window.after(0, lambda: messagebox.showinfo("Success", f"Successfully converted {len(converted_files)} files"))
                    if failed_conversions:
                        self.window.after(0, lambda: messagebox.showwarning("Warning", f"Failed to convert {len(failed_conversions)} files"))
                    # Optionally, close the dialog manually
                    # self.window.after(0, dialog.destroy)
            except Exception as e:
                logger.error(f"Error during conversion: {e}", exc_info=True)
                self.window.after(0, lambda: progress_var.set(f"Error: {str(e)}"))
                self.window.after(0, lambda: messagebox.showerror("Error", f"Conversion failed: {str(e)}"))
                self.window.after(0, dialog.destroy)
        
        threading.Thread(target=conversion_task).start()

    def clear_list(self):
        """Clear the downloaded songs list"""
        self.songs_listbox.delete(0, tk.END)
        self.downloaded_songs = []

    def show_welcome_screen(self):
        """Show the welcome screen"""
        self.download_frame.pack_forget()
        self.welcome_frame.pack(fill=tk.BOTH, expand=True)

    def select_platform(self, platform: str):
        """Handle platform selection"""
        self.current_platform = platform
        self.welcome_frame.pack_forget()
        self.download_frame.pack(fill=tk.BOTH, expand=True)
        
        # Update UI based on platform
        if platform == "yandex":
            self.token_entry.pack()
        else:
            self.token_entry.pack_forget()

    def cleanup(self):
        """Clean up resources before closing"""
        try:
            # Close asyncio loop
            if self.loop and self.loop.is_running():
                self.loop.stop()
                self.loop.close()
            
            # Save config
            config_path = Path("config.json")
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

    def run(self):
        """Start the application"""
        try:
            self.window.mainloop()
        finally:
            self.cleanup()

    def refresh_file_list(self):
        """Update the listbox with files from the output and converted directories and preserve selection."""
        # Save selected file names
        selected_files = [self.songs_listbox.get(i) for i in self.songs_listbox.curselection()]
        
        output_dir = Path(self.config.get("output_dir", "downloads"))
        converted_dir = Path(self.config.get("converted_dir", "converted"))
        output_dir.mkdir(exist_ok=True)
        converted_dir.mkdir(exist_ok=True)
        
        # Get current files in both directories
        downloaded_files = list(output_dir.glob("*"))
        converted_files = list(converted_dir.glob("*"))
        all_files = downloaded_files + converted_files
        file_names = [file.name for file in all_files]
        self.downloaded_songs = [str(file) for file in all_files]
        
        # Update the listbox
        self.songs_listbox.delete(0, tk.END)
        if file_names:
            for name in file_names:
                self.songs_listbox.insert(tk.END, name)
        else:
            self.songs_listbox.insert(tk.END, "No files found.")
        
        # Restore selection
        if file_names:
            for file_name in selected_files:
                if file_name in file_names:
                    index = self.songs_listbox.get(0, tk.END).index(file_name)
                    self.songs_listbox.select_set(index)
        else:
            self.songs_listbox.selection_clear(0, tk.END)

if __name__ == "__main__":
    app = MusicDownloaderApp()
    app.run()