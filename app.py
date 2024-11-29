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

# Are you importing stuff, or is it importing you.
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.FileHandler('music_downloader.log'), logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

class MusicDownloaderApp:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Shadow Wizard Kitten Gang")
        self.window.geometry("800x600")
        
        # Because dark mode is cooler, obviously.
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.config = self.load_config()
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.status_var = tk.StringVar(value="Ready")
        
        self.downloaded_songs = []
        
        self.setup_ui()
        
        # Is FFmpeg installed? Or are we just pretending it's installed?
        self.check_ffmpeg()

    def check_ffmpeg(self):
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            logger.info("FFmpeg is available.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            messagebox.showerror("Error", "FFmpeg is not installed or not found in PATH.")
            logger.error("FFmpeg is not installed or not found in PATH.")
            self.window.destroy()

    def load_config(self) -> dict:
        config_path = Path("config.json")
        default_config = {
            "output_dir": "downloads",
            "converted_dir": "converted",
            "supported_formats": ["mp3", "wav", "m4a", "flac"],
            "default_format": "mp3",
            "max_concurrent_downloads": 3,
            "spotify_bitrate": "128k",
            "spotify_threads": 7
        }
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                # Updating config with default_config, because mixing old and new is fun!
                config = {**default_config, **config}
                return config
            return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            return default_config

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.window)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.welcome_frame = self.create_welcome_frame()
        self.download_frame = self.create_download_frame()

        # Built by Chun - because who else would build it?
        fine_print = ctk.CTkLabel(
            self.window,
            text="Built by Chun",
            font=("Helvetica", 10),
            anchor="se"
        )
        fine_print.place(relx=1.0, rely=1.0, anchor="se")

        self.show_welcome_screen()

    def create_welcome_frame(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container)
        
        welcome_label = ctk.CTkLabel(
            frame,
            text="Welcome to Music Downloader",
            font=("Helvetica", 24, "bold")
        )
        welcome_label.pack(pady=20)
        
        platform_frame = ctk.CTkFrame(frame)
        platform_frame.pack(pady=20)
        
        ctk.CTkLabel(
            platform_frame,
            text="Select your music platform:",
            font=("Helvetica", 16)
        ).pack(pady=10)
        
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
        frame = ctk.CTkFrame(self.main_container)
        
        self.url_var = tk.StringVar()
        url_frame = ctk.CTkFrame(frame)
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(url_frame, text="Song URL:").pack(side=tk.LEFT, padx=5)
        ctk.CTkEntry(url_frame, textvariable=self.url_var, width=300).pack(side=tk.LEFT, padx=5)
        
        self.token_var = tk.StringVar()
        token_frame = ctk.CTkFrame(frame)
        token_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkLabel(token_frame, text="API Token:").pack(side=tk.LEFT, padx=5)
        self.token_entry = ctk.CTkEntry(token_frame, textvariable=self.token_var, width=300, show="*")
        self.token_entry.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(frame, textvariable=self.status_var).pack(pady=5)
        
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
        
        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ctk.CTkButton(button_frame, text="Download", command=self.start_download).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(button_frame, text="Convert", command=self.show_convert_dialog).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(button_frame, text="Clear List", command=self.clear_list).pack(side=tk.LEFT, padx=5)
        
        return frame

    async def initialize_yandex_client(self, token: str):
        try:
            self.yandex_client = await ClientAsync(token).init()
            logger.info("Yandex Music client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Yandex Music client: {e}", exc_info=True)
            messagebox.showerror("Error", "Failed to initialize Yandex Music client")
            raise

    def download_spotify_track(self, url: str) -> Optional[str]:
        try:
            output_dir = Path(self.config["output_dir"])
            output_dir.mkdir(exist_ok=True)
            
            logger.info(f"Starting Spotify download for URL: {url}")
            
            # Is spotdl installed? Or are we just pretending it's installed?
            try:
                subprocess.run(["spotdl", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                error_msg = "spotdl is not installed. Please install it using: pip install spotdl"
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)
                return None
            
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
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.status_var.set("Downloading from Spotify...")
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    logger.info(f"spotdl output: {output.strip()}")
                    self.status_var.set(f"Download progress: {output.strip()}")
            
            return_code = process.wait()
            
            if return_code == 0:
                logger.info("Spotify download completed successfully")
                self.status_var.set("Download completed")
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
        try:
            logger.info(f"Starting Yandex download for track ID: {track_id}")
            self.status_var.set("Downloading from Yandex Music...")
            
            track = await self.yandex_client.tracks(track_id)[0]
            full_track = await track.fetch_track_async()
            
            os.makedirs(self.config["output_dir"], exist_ok=True)
            
            filename = f"{full_track.artists[0].name} - {full_track.title}.mp3"
            filepath = os.path.join(self.config["output_dir"], filename)
            
            await full_track.download_async(filepath)
            logger.info(f"Successfully downloaded: {filename}")
            self.status_var.set("Download completed")
            self.downloaded_songs.append(filepath)
            return filepath
        except Exception as e:
            logger.error(f"Error downloading Yandex track: {e}", exc_info=True)
            self.status_var.set("Download failed")
            return None

    def start_download(self):
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
        
        # Threads: because one function at a time is for squares.
        threading.Thread(target=download_thread, daemon=True).start()

    def convert_audio(self, input_path: str, output_format: str) -> Optional[str]:
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            messagebox.showerror("Error", f"File not found: {os.path.basename(input_path)}")
            return None
        
        input_extension = os.path.splitext(input_path)[1].lstrip('.').lower()
        if input_extension == output_format.lower():
            logger.warning(f"Input and output formats are the same. Skipping conversion.")
            return input_path
        
        converted_dir = Path(self.config["converted_dir"])
        converted_dir.mkdir(parents=True, exist_ok=True)
        
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
        if not self.songs_listbox.curselection():
            messagebox.showwarning("Warning", "Please select songs to convert")
            return
        
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Audio Converter")
        dialog.geometry("500x600")
        
        dialog.transient(self.window)
        dialog.grab_set()
        
        dialog.focus_set()
        dialog.lift()
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        header_label = ctk.CTkLabel(
            main_frame,
            text="Convert Audio Files",
            font=("Helvetica", 20, "bold")
        )
        header_label.pack(pady=(0, 20))
        
        files_frame = ctk.CTkFrame(main_frame)
        files_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        files_label = ctk.CTkLabel(
            files_frame,
            text="Selected Files:",
            font=("Helvetica", 14, "bold")
        )
        files_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        files_listbox = tk.Listbox(
            files_frame,
            selectmode=tk.MULTIPLE,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#1f538d",
            height=8
        )
        files_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(files_listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        files_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=files_listbox.yview)
        
        selected_indices = self.songs_listbox.curselection()
        for index in selected_indices:
            filename = os.path.basename(self.downloaded_songs[index])
            files_listbox.insert(tk.END, filename)
        
        format_frame = ctk.CTkFrame(main_frame)
        format_frame.pack(fill=tk.X, pady=(0, 20))
        
        format_label = ctk.CTkLabel(
            format_frame,
            text="Output Format:",
            font=("Helvetica", 14, "bold")
        )
        format_label.pack(anchor="w", padx=10, pady=(10, 5))
        
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
        
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        progress_var = tk.StringVar(value="")
        progress_label = ctk.CTkLabel(
            progress_frame,
            textvariable=progress_var,
            font=("Helvetica", 12)
        )
        progress_label.pack(pady=10)
        
        progress_bar = ctk.CTkProgressBar(progress_frame)
        progress_bar.pack(fill=tk.X, padx=10, pady=(0, 10))
        progress_bar.set(0)
        
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        def cancel_conversion():
            self.conversion_cancelled = True
            dialog.destroy()
        
        def start_conversion():
            output_format = format_var.get()
            self.convert_selected_songs(output_format, dialog, progress_var, progress_bar)
        
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
        selected_indices = self.songs_listbox.curselection()
        total_files = len(selected_indices)
        converted_files = []
        failed_conversions = []
        self.conversion_cancelled = False
        
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
                    
                    progress = i / total_files
                    self.window.after(0, lambda p=progress: progress_bar.set(p))
                    self.window.after(0, lambda: progress_var.set(f"Converting file {i}/{total_files}: {os.path.basename(input_path)}"))
                    
                    output_path = self.convert_audio(input_path, output_format)
                    if output_path:
                        converted_files.append(output_path)
                        self.window.after(0, lambda: self.downloaded_songs.append(output_path))
                        self.window.after(0, lambda: self.songs_listbox.insert(tk.END, os.path.basename(output_path)))
                    else:
                        failed_conversions.append(input_path)
                    
                if not self.conversion_cancelled:
                    if converted_files:
                        self.window.after(0, lambda: progress_var.set("Conversion completed successfully!"))
                        self.window.after(0, lambda: progress_bar.set(1.0))
                        self.window.after(0, lambda: messagebox.showinfo("Success", f"Successfully converted {len(converted_files)} files"))
                    if failed_conversions:
                        self.window.after(0, lambda: messagebox.showwarning("Warning", f"Failed to convert {len(failed_conversions)} files"))
            except Exception as e:
                logger.error(f"Error during conversion: {e}", exc_info=True)
                self.window.after(0, lambda: progress_var.set(f"Error: {str(e)}"))
                self.window.after(0, lambda: messagebox.showerror("Error", f"Conversion failed: {str(e)}"))
                self.window.after(0, dialog.destroy)
        
        # Because why not add some excitement to conversion?
        threading.Thread(target=conversion_task).start()

    def clear_list(self):
        self.songs_listbox.delete(0, tk.END)
        self.downloaded_songs = []

    def show_welcome_screen(self):
        self.download_frame.pack_forget()
        self.welcome_frame.pack(fill=tk.BOTH, expand=True)

    def select_platform(self, platform: str):
        self.current_platform = platform
        self.welcome_frame.pack_forget()
        self.download_frame.pack(fill=tk.BOTH, expand=True)
        
        if platform == "yandex":
            self.token_entry.pack()
        else:
            self.token_entry.pack_forget()

    def cleanup(self):
        try:
            if self.loop and self.loop.is_running():
                self.loop.stop()
                self.loop.close()
            
            config_path = Path("config.json")
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

    def run(self):
        try:
            self.window.mainloop()
        finally:
            self.cleanup()

    def refresh_file_list(self):
        selected_files = [self.songs_listbox.get(i) for i in self.songs_listbox.curselection()]
        
        output_dir = Path(self.config.get("output_dir", "downloads"))
        converted_dir = Path(self.config.get("converted_dir", "converted"))
        output_dir.mkdir(exist_ok=True)
        converted_dir.mkdir(exist_ok=True)
        
        downloaded_files = list(output_dir.glob("*"))
        converted_files = list(converted_dir.glob("*"))
        all_files = downloaded_files + converted_files
        file_names = [file.name for file in all_files]
        self.downloaded_songs = [str(file) for file in all_files]
        
        self.songs_listbox.delete(0, tk.END)
        if file_names:
            for name in file_names:
                self.songs_listbox.insert(tk.END, name)
        else:
            self.songs_listbox.insert(tk.END, "No files found.")
        
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
