#!/usr/bin/env python3
"""
Slideshow Manager with GUI - Manage, preview, and create slideshows from images.
Features: thumbnails, sort, search, rename, add, hide, remove images.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
import json
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import threading
import logging
import traceback
from io import StringIO

# Setup logging to both file and console
log_file = Path.cwd() / "slideshow_manager.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ErrorDialog(tk.Toplevel):
    """Custom error dialog with copy-paste capability."""

    def __init__(self, parent, title, message, error_type="error"):
        super().__init__(parent)
        self.title(title)
        self.geometry("600x400")
        self.resizable(True, True)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Icon and title
        icon_map = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
        icon = icon_map.get(error_type, "❌")

        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(title_frame, text=f"{icon} {title}", font=("Arial", 12, "bold")).pack(anchor=tk.W)

        # Message text area (selectable)
        text_frame = ttk.LabelFrame(self, text="Error Details (Selectable & Copyable)", padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text_widget = scrolledtext.ScrolledText(
            text_frame,
            height=15,
            width=70,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="gray20",
            fg="white"
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        self.text_widget.insert(tk.END, message)
        self.text_widget.config(state=tk.DISABLED)  # Read-only

        # Add context menu for copy
        self.text_widget.bind("<Button-3>", self._show_context_menu)

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="📋 Copy All", command=self._copy_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📁 View Log File", command=self._open_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✅ Close", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _show_context_menu(self, event):
        """Show context menu for copy."""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy", command=self._copy_selected)
        menu.add_command(label="Copy All", command=self._copy_all)
        menu.post(event.x_root, event.y_root)

    def _copy_selected(self):
        """Copy selected text to clipboard."""
        try:
            selected = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected)
            logger.info("Text copied to clipboard")
        except tk.TclError:
            pass

    def _copy_all(self):
        """Copy all text to clipboard."""
        try:
            all_text = self.text_widget.get(1.0, tk.END)
            self.clipboard_clear()
            self.clipboard_append(all_text)
            messagebox.showinfo("Success", "✅ All error details copied to clipboard!")
            logger.info("All error details copied to clipboard")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")

    def _open_log(self):
        """Open log file in default editor."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(log_file)])
            elif sys.platform == "linux":
                subprocess.run(["xdg-open", str(log_file)])
            elif sys.platform == "win32":
                subprocess.run(["notepad", str(log_file)])
            logger.info(f"Opened log file: {log_file}")
        except Exception as e:
            logger.error(f"Failed to open log file: {e}")
            messagebox.showerror("Error", f"Could not open log file:\n{e}")


class SlideshowManager:
    """Manage slideshow images and creation."""
    
    CONFIG_FILE = ".slideshow_config.json"

    # Video player priority list (in order of preference)
    PREFERRED_PLAYERS = [
        "vlc",           # VLC media player (most compatible)
        "mpv",           # MPV (lightweight, excellent quality)
        "celluloid",     # Celluloid (modern GTK video player)
        "shotcut",       # Shotcut (video editor, can play videos)
        "ffplay",        # FFplay (comes with ffmpeg)
        "totem",         # GNOME Videos
        "smplayer",      # SMPlayer
        "mplayer",       # MPlayer
        "xine",          # Xine
        "gxine",         # Xine GUI
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Slideshow Manager - Image Organizer")
        self.root.geometry("1400x900")
        self.root.minsize(800, 600)

        self.images = []  # List of image paths
        self.hidden_images = set()  # Hidden image paths
        self.thumbnails = {}  # Cache for thumbnails
        self.current_dir = Path.cwd()
        self.is_creating = False  # Flag to prevent multiple slideshow creations
        self.error_count = 0  # Track errors
        self.warning_count = 0  # Track warnings
        self.available_players = []  # Detected video players
        self.preferred_player = None  # Best available player
        self.output_directory = Path.cwd()  # Output directory for slideshows
        self.preferred_player_setting = "auto"  # User's preferred player setting
        self.last_slideshow_path = None  # Track last created slideshow for quick play

        logger.info("=" * 80)
        logger.info("Slideshow Manager Started")
        logger.info(f"Working Directory: {self.current_dir}")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        logger.info("=" * 80)

        self.load_config()
        self.check_ffmpeg()
        self.detect_video_players()
        self.setup_ui()
        self.load_images()

        # Update play button state based on existing videos
        self._update_play_button_state()

        # Refresh error log display after UI is set up
        self.root.after(100, self._refresh_error_log_display)

        # Start auto-refresh of error log display (every 500ms)
        self._schedule_log_refresh()

        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def show_error_log(self):
        """Show error log viewer window."""
        try:
            if not log_file.exists():
                messagebox.showinfo("No Logs", "No error log file found yet.")
                return

            with open(log_file, 'r') as f:
                log_content = f.read()

            # Create log viewer window
            log_window = tk.Toplevel(self.root)
            log_window.title("Error Log Viewer")
            log_window.geometry("800x600")

            # Title
            title_frame = ttk.Frame(log_window)
            title_frame.pack(fill=tk.X, padx=10, pady=10)
            ttk.Label(title_frame, text="📋 Error Log", font=("Arial", 12, "bold")).pack(anchor=tk.W)
            ttk.Label(title_frame, text=f"File: {log_file}", font=("Arial", 9), foreground="gray").pack(anchor=tk.W)

            # Log text area
            text_frame = ttk.Frame(log_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            log_text = scrolledtext.ScrolledText(
                text_frame,
                wrap=tk.WORD,
                font=("Courier", 9),
                bg="gray20",
                fg="white"
            )
            log_text.pack(fill=tk.BOTH, expand=True)
            log_text.insert(tk.END, log_content)
            log_text.config(state=tk.DISABLED)

            # Buttons
            btn_frame = ttk.Frame(log_window)
            btn_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Button(btn_frame, text="📋 Copy All", command=lambda: self._copy_log_text(log_text)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="🗑️ Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="✅ Close", command=log_window.destroy).pack(side=tk.RIGHT, padx=5)

            logger.info("Error log viewer opened")
        except Exception as e:
            self._show_error("Error", f"Failed to open error log:\n{str(e)}", "error")

    def _copy_log_text(self, text_widget):
        """Copy log text to clipboard."""
        try:
            all_text = text_widget.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(all_text)
            messagebox.showinfo("Success", "✅ Log copied to clipboard!")
            logger.info("Log copied to clipboard")
        except Exception as e:
            logger.error(f"Failed to copy log: {e}")

    def _clear_log(self):
        """Clear the error log file."""
        if messagebox.askyesno("Confirm", "Clear all error logs? This cannot be undone."):
            try:
                log_file.write_text("")
                messagebox.showinfo("Success", "✅ Error log cleared!")
                logger.info("Error log cleared by user")
                self._refresh_error_log_display()
            except Exception as e:
                self._show_error("Error", f"Failed to clear log:\n{str(e)}", "error")

    def _schedule_log_refresh(self):
        """Schedule automatic refresh of error log display."""
        try:
            self._refresh_error_log_display()
        except Exception as e:
            logger.debug(f"Error in scheduled log refresh: {e}")
        finally:
            # Schedule next refresh in 500ms
            if hasattr(self, 'root'):
                self.root.after(500, self._schedule_log_refresh)

    def _refresh_error_log_display(self):
        """Refresh the embedded error log display with last 10 entries."""
        try:
            if not hasattr(self, 'error_log_display'):
                return

            if log_file.exists():
                log_content = log_file.read_text()
                lines = log_content.strip().split('\n')
                # Show last 10 lines
                last_lines = '\n'.join(lines[-10:]) if lines else "No errors logged yet"
            else:
                last_lines = "No errors logged yet"

            # Get current scroll position to preserve user's scroll location
            current_scroll = self.error_log_display.yview()

            self.error_log_display.config(state=tk.NORMAL)
            self.error_log_display.delete(1.0, tk.END)
            self.error_log_display.insert(tk.END, last_lines)
            self.error_log_display.config(state=tk.DISABLED)

            # Only auto-scroll to end if user was already at the bottom
            # Otherwise preserve their scroll position
            if current_scroll[1] >= 0.95:  # If scrolled to bottom (95%+)
                self.error_log_display.see(tk.END)
            else:
                # Restore previous scroll position
                self.error_log_display.yview_moveto(current_scroll[0])
        except Exception as e:
            logger.debug(f"Error refreshing log display: {e}")

    def show_settings_dialog(self):
        """Show settings dialog with elegant UX."""
        try:
            settings_window = tk.Toplevel(self.root)
            settings_window.title("⚙️ Settings")
            settings_window.geometry("600x500")
            settings_window.resizable(False, False)

            # Center on parent
            settings_window.transient(self.root)
            settings_window.grab_set()

            # Main frame with padding
            main_frame = ttk.Frame(settings_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Title
            title_label = ttk.Label(main_frame, text="⚙️ Application Settings", font=("Arial", 14, "bold"))
            title_label.pack(anchor=tk.W, pady=(0, 20))

            # Create notebook for organized sections
            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

            # ===== TAB 1: Output Settings =====
            output_frame = ttk.Frame(notebook, padding=15)
            notebook.add(output_frame, text="📁 Output")

            # Output Directory Section
            ttk.Label(output_frame, text="Output Directory", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
            ttk.Label(output_frame, text="Where to save slideshow videos:", foreground="gray", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 10))

            # Current directory display
            dir_display_frame = ttk.Frame(output_frame)
            dir_display_frame.pack(fill=tk.X, pady=(0, 10))

            self.output_dir_label = ttk.Label(
                dir_display_frame,
                text=str(self.output_directory),
                font=("Courier", 9),
                foreground="blue",
                background="gray95",
                relief=tk.SUNKEN,
                padding=10
            )
            self.output_dir_label.pack(fill=tk.X, side=tk.LEFT, expand=True)

            # Browse button
            ttk.Button(
                dir_display_frame,
                text="📂 Browse",
                command=self._browse_output_directory
            ).pack(side=tk.LEFT, padx=(10, 0))

            # Reset to current directory button
            ttk.Button(
                output_frame,
                text="↺ Reset to Current Directory",
                command=self._reset_output_directory
            ).pack(fill=tk.X, pady=(0, 20))

            # Info box
            info_text = "💡 Tip: Slideshows will be saved to the selected directory.\nYou can organize them in different folders."
            ttk.Label(output_frame, text=info_text, foreground="gray", font=("Arial", 9), justify=tk.LEFT).pack(anchor=tk.W, pady=(10, 0))

            # ===== TAB 2: Playback Settings =====
            playback_frame = ttk.Frame(notebook, padding=15)
            notebook.add(playback_frame, text="▶️ Playback")

            # Player Selection Section
            ttk.Label(playback_frame, text="Video Player", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
            ttk.Label(playback_frame, text="Choose your preferred video player:", foreground="gray", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 10))

            # Player dropdown
            player_options = ["auto"] + self.available_players
            self.settings_player_var = tk.StringVar(value=self.preferred_player_setting)

            player_combo = ttk.Combobox(
                playback_frame,
                textvariable=self.settings_player_var,
                values=player_options,
                state="readonly",
                width=30
            )
            player_combo.pack(fill=tk.X, pady=(0, 10))

            # Player info
            player_info = "• auto: Uses best available player\n• mpv: Lightweight, excellent quality\n• vlc: Most compatible, feature-rich"
            ttk.Label(playback_frame, text=player_info, foreground="gray", font=("Arial", 9), justify=tk.LEFT).pack(anchor=tk.W, pady=(10, 0))

            # ===== TAB 3: About =====
            about_frame = ttk.Frame(notebook, padding=15)
            notebook.add(about_frame, text="ℹ️ About")

            about_text = """📸 Slideshow Manager v1.1

Create beautiful slideshows from your images with:
• Thumbnail preview
• Image sorting and searching
• Video player selection
• Customizable output directory
• Error logging and monitoring

Features:
✓ Support for PNG, JPG formats
✓ Multiple video player support
✓ Real-time error logging
✓ Automatic player fallback
✓ Professional video encoding

© 2025 - All rights reserved"""

            ttk.Label(about_frame, text=about_text, font=("Arial", 10), justify=tk.LEFT).pack(anchor=tk.W, pady=10)

            # ===== Buttons =====
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, side=tk.BOTTOM)

            ttk.Button(
                button_frame,
                text="✅ Save & Close",
                command=lambda: self._save_settings(settings_window)
            ).pack(side=tk.RIGHT, padx=(5, 0))

            ttk.Button(
                button_frame,
                text="❌ Cancel",
                command=settings_window.destroy
            ).pack(side=tk.RIGHT, padx=5)

            logger.info("Settings dialog opened")

        except Exception as e:
            self._show_error("Error", f"Failed to open settings:\n{str(e)}", "error")

    def _browse_output_directory(self):
        """Browse for output directory."""
        try:
            directory = filedialog.askdirectory(
                title="Select Output Directory for Slideshows",
                initialdir=str(self.output_directory)
            )
            if directory:
                self.output_directory = Path(directory)
                self.output_dir_label.config(text=str(self.output_directory))
                logger.info(f"Output directory changed to: {self.output_directory}")
        except Exception as e:
            logger.error(f"Error browsing directory: {e}")

    def _reset_output_directory(self):
        """Reset output directory to current working directory."""
        try:
            self.output_directory = Path.cwd()
            self.output_dir_label.config(text=str(self.output_directory))
            logger.info(f"Output directory reset to: {self.output_directory}")
        except Exception as e:
            logger.error(f"Error resetting directory: {e}")

    def _save_settings(self, window):
        """Save settings and close dialog."""
        try:
            # Save player preference
            self.preferred_player_setting = self.settings_player_var.get()
            self.player_var.set(self.preferred_player_setting)

            # Save to config file
            self.save_config()

            messagebox.showinfo("Success", "✅ Settings saved successfully!")
            logger.info("Settings saved")
            window.destroy()
        except Exception as e:
            self._show_error("Error", f"Failed to save settings:\n{str(e)}", "error")

    def _show_error(self, title, message, error_type="error"):
        """Show error dialog with copy-paste capability."""
        self.error_count += 1
        logger.error(f"{title}: {message}")

        # Print to terminal
        print(f"\n{'='*80}")
        print(f"❌ {title}")
        print(f"{'='*80}")
        print(message)
        print(f"{'='*80}\n")

        # Refresh embedded error log display
        self._refresh_error_log_display()

        # Show custom error dialog
        ErrorDialog(self.root, title, message, error_type)

    def _show_warning(self, title, message):
        """Show warning dialog with copy-paste capability."""
        self.warning_count += 1
        logger.warning(f"{title}: {message}")

        # Print to terminal
        print(f"\n{'='*80}")
        print(f"⚠️ {title}")
        print(f"{'='*80}")
        print(message)
        print(f"{'='*80}\n")

        # Refresh embedded error log display
        self._refresh_error_log_display()

        # Show custom warning dialog
        ErrorDialog(self.root, title, message, "warning")

    def check_ffmpeg(self):
        """Check and install ffmpeg if needed."""
        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg not found")
            if messagebox.askyesno("ffmpeg Missing", "ffmpeg not found. Install now?"):
                self.install_ffmpeg()
            else:
                self._show_error("Error", "ffmpeg is required to create slideshows", "error")
    
    def install_ffmpeg(self):
        """Install ffmpeg based on OS."""
        try:
            logger.info("Attempting to install ffmpeg...")
            if sys.platform == "darwin":
                if shutil.which("brew"):
                    logger.info("Installing ffmpeg via Homebrew...")
                    subprocess.run(["brew", "install", "ffmpeg"], check=True)
                else:
                    self._show_error("Error", "Homebrew not found. Please install ffmpeg manually.", "error")
                    return
            elif sys.platform == "linux":
                if shutil.which("apt-get"):
                    logger.info("Installing ffmpeg via apt-get...")
                    subprocess.run(["sudo", "apt-get", "update"], check=False)
                    subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], check=True)
                else:
                    self._show_error("Error", "Could not find package manager. Please install ffmpeg manually.", "error")
                    return
            elif sys.platform == "win32":
                if shutil.which("choco"):
                    logger.info("Installing ffmpeg via Chocolatey...")
                    subprocess.run(["choco", "install", "-y", "ffmpeg"], check=True)
                else:
                    self._show_error("Error", "Chocolatey not found. Please install ffmpeg manually.", "error")
                    return
            messagebox.showinfo("Success", "✅ ffmpeg installed successfully")
            logger.info("ffmpeg installed successfully")
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg installation failed:\n\nCommand: {' '.join(e.cmd)}\nReturn code: {e.returncode}"
            self._show_error("Installation Error", error_msg, "error")
        except Exception as e:
            error_msg = f"Failed to install ffmpeg:\n\n{str(e)}\n\n{traceback.format_exc()}"
            self._show_error("Error", error_msg, "error")

    def detect_video_players(self):
        """Detect available video players on the system."""
        try:
            logger.info("Detecting available video players...")
            self.available_players = []

            for player in self.PREFERRED_PLAYERS:
                if shutil.which(player):
                    self.available_players.append(player)
                    logger.debug(f"Found video player: {player}")

            if self.available_players:
                self.preferred_player = self.available_players[0]
                logger.info(f"Available players: {', '.join(self.available_players)}")
                logger.info(f"Preferred player: {self.preferred_player}")
            else:
                logger.warning("No video players detected on system")
                self.preferred_player = None

        except Exception as e:
            logger.error(f"Error detecting video players: {str(e)}")
            self.available_players = []
            self.preferred_player = None

    def play_video(self, video_path):
        """Play video using selected or best available player."""
        try:
            video_path = Path(video_path)
            if not video_path.exists():
                self._show_error("Error", f"Video file not found:\n{video_path}", "error")
                logger.error(f"Video file not found: {video_path}")
                return

            if not self.available_players:
                self._show_error(
                    "No Player Found",
                    "No video player detected on your system.\n\n"
                    "Please install one of these players:\n"
                    "• VLC (vlc)\n"
                    "• MPV (mpv)\n"
                    "• Cinelerra (cinelerra)\n"
                    "• FFplay (ffplay)\n\n"
                    "On Linux: sudo apt-get install vlc\n"
                    "On macOS: brew install vlc\n"
                    "On Windows: Download from videolan.org",
                    "error"
                )
                logger.error("No video players available")
                return

            # Get selected player from dropdown
            selected_player = self.player_var.get()
            if selected_player == "auto":
                player = self.preferred_player
                players_to_try = self.available_players
            else:
                player = selected_player
                players_to_try = [selected_player] + [p for p in self.available_players if p != selected_player]

            logger.info(f"Playing video with {player}: {video_path}")

            try:
                # Use subprocess.Popen to run player in background
                subprocess.Popen([player, str(video_path)])
                self.status_bar.config(text=f"▶️ Playing: {video_path.name}")
                logger.info(f"Video playback started: {video_path.name}")
            except Exception as e:
                logger.error(f"Failed to play with {player}: {str(e)}")
                # Try next available player
                for alt_player in players_to_try[1:]:
                    try:
                        logger.info(f"Trying alternative player: {alt_player}")
                        subprocess.Popen([alt_player, str(video_path)])
                        self.status_bar.config(text=f"▶️ Playing: {video_path.name}")
                        logger.info(f"Video playback started with {alt_player}: {video_path.name}")
                        return
                    except Exception as alt_e:
                        logger.debug(f"Failed with {alt_player}: {str(alt_e)}")
                        continue

                # All players failed
                error_msg = f"Failed to play video with any available player:\n\n{str(e)}"
                self._show_error("Playback Error", error_msg, "error")

        except Exception as e:
            error_msg = f"Error playing video:\n\n{str(e)}\n\n{traceback.format_exc()}"
            logger.error(f"Error playing video: {error_msg}")
            self._show_error("Error", error_msg, "error")

    def _get_available_videos(self):
        """Get list of available MP4 videos in output directory."""
        try:
            if not self.output_directory.exists():
                return []
            videos = sorted(self.output_directory.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
            return videos
        except Exception as e:
            logger.debug(f"Error getting available videos: {e}")
            return []

    def _update_play_button_state(self):
        """Update play button state based on available videos."""
        try:
            videos = self._get_available_videos()
            if videos and not self.last_slideshow_path:
                # Set to most recent video
                self.last_slideshow_path = str(videos[0])
                self.play_last_btn.config(state=tk.NORMAL)
            elif not videos:
                self.last_slideshow_path = None
                self.play_last_btn.config(state=tk.DISABLED)
        except Exception as e:
            logger.debug(f"Error updating play button state: {e}")

    def _play_last_slideshow(self):
        """Play the last created slideshow or show video selection panel."""
        try:
            videos = self._get_available_videos()

            if not videos:
                messagebox.showwarning("No Videos", "No slideshow videos found in output directory.")
                return

            # If only one video, play it
            if len(videos) == 1:
                self.play_video(str(videos[0]))
                return

            # If multiple videos, show selection panel in main window
            self._show_video_selection_panel(videos)
        except Exception as e:
            logger.error(f"Error playing last slideshow: {e}")
            messagebox.showerror("Error", f"Error playing video:\n{str(e)}")

    def _show_video_selection_panel(self, videos):
        """Show video selection panel in main window."""
        try:
            # If panel already exists, clear it
            if hasattr(self, 'video_panel_frame') and self.video_panel_frame.winfo_exists():
                self.video_panel_frame.destroy()

            # Create video selection panel
            self.video_panel_frame = ttk.LabelFrame(self.root, text="📹 Select Video to Play", padding=10)
            self.video_panel_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=10, pady=5, after=self.control_frame)

            # Frame for listbox and scrollbar
            list_frame = ttk.Frame(self.video_panel_frame)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.video_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Courier", 9), height=6)
            self.video_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=self.video_listbox.yview)

            # Populate listbox with videos
            for i, video in enumerate(videos):
                try:
                    size_mb = video.stat().st_size / (1024 * 1024)
                    mtime = video.stat().st_mtime
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    display_text = f"{video.name} ({size_mb:.1f} MB) - {date_str}"
                    self.video_listbox.insert(tk.END, display_text)
                except Exception as e:
                    self.video_listbox.insert(tk.END, video.name)

            # Select first item by default
            if videos:
                self.video_listbox.selection_set(0)
                self.video_listbox.see(0)

            # Store videos reference for button callbacks
            self.available_videos_for_selection = videos

            # Buttons frame
            btn_frame = ttk.Frame(self.video_panel_frame)
            btn_frame.pack(fill=tk.X, padx=5, pady=5)

            def play_selected():
                selection = self.video_listbox.curselection()
                if selection:
                    selected_video = self.available_videos_for_selection[selection[0]]
                    self.play_video(str(selected_video))
                    self.last_slideshow_path = str(selected_video)
                    # Hide panel after playing
                    self.video_panel_frame.destroy()

            def open_folder():
                self._open_folder(self.available_videos_for_selection[0])

            def close_panel():
                self.video_panel_frame.destroy()

            ttk.Button(btn_frame, text="▶️ Play Selected", command=play_selected).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_frame, text="📁 Open Folder", command=open_folder).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_frame, text="❌ Close", command=close_panel).pack(side=tk.RIGHT, padx=3)

        except Exception as e:
            logger.error(f"Error showing video selection panel: {e}")
            messagebox.showerror("Error", f"Error showing video list:\n{str(e)}")

    def setup_ui(self):
        """Setup the user interface with improved layout."""
        # Title bar
        title_frame = ttk.Frame(self.root)
        title_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        ttk.Label(title_frame, text="📸 Slideshow Manager", font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        # Control panel - organized in sections
        self.control_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        self.control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Left section - File operations
        left_section = ttk.Frame(self.control_frame)
        left_section.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(left_section, text="➕ Add Images", command=self.add_images).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_section, text="🔄 Refresh", command=self.load_images).pack(side=tk.LEFT, padx=5)

        # Middle section - Sort and Search
        middle_section = ttk.Frame(self.control_frame)
        middle_section.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)

        ttk.Label(middle_section, text="Sort by:").pack(side=tk.LEFT, padx=5)
        self.sort_var = tk.StringVar(value="name")
        sort_menu = ttk.Combobox(middle_section, textvariable=self.sort_var,
                                  values=["name", "date modified", "file size"], state="readonly", width=15)
        sort_menu.pack(side=tk.LEFT, padx=5)
        sort_menu.bind("<<ComboboxSelected>>", lambda e: self.load_images())

        ttk.Label(middle_section, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(middle_section, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self.load_images())

        # Right section - Player selection, Create slideshow, settings and error log
        right_section = ttk.Frame(self.control_frame)
        right_section.pack(side=tk.RIGHT)

        # Player selection dropdown
        ttk.Label(right_section, text="Player:").pack(side=tk.LEFT, padx=5)
        self.player_var = tk.StringVar(value=self.preferred_player or "auto")
        player_options = ["auto"] + self.available_players
        player_menu = ttk.Combobox(right_section, textvariable=self.player_var,
                                    values=player_options, state="readonly", width=12)
        player_menu.pack(side=tk.LEFT, padx=5)

        ttk.Button(right_section, text="🎬 Create Slideshow", command=self.create_slideshow).pack(side=tk.LEFT, padx=5)
        self.play_last_btn = ttk.Button(right_section, text="▶️ Play Video", command=self._play_last_slideshow, state=tk.DISABLED)
        self.play_last_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(right_section, text="⚙️ Settings", command=self.show_settings_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_section, text="📋 Error Log", command=self.show_error_log).pack(side=tk.LEFT, padx=5)

        # Stats bar
        self.stats_frame = ttk.LabelFrame(self.root, text="Statistics", padding=10)
        self.stats_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.stats_label = ttk.Label(self.stats_frame, text="Loading...", font=("Arial", 10))
        self.stats_label.pack(side=tk.LEFT)

        # Error Log Display Panel (embedded in main window, resizable)
        log_panel_frame = ttk.LabelFrame(self.root, text="📋 Error Log (Last 10 entries) - Resizable", padding=5)
        log_panel_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Error log text display (resizable)
        log_display_frame = ttk.Frame(log_panel_frame)
        log_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_scrollbar = ttk.Scrollbar(log_display_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.error_log_display = scrolledtext.ScrolledText(
            log_display_frame,
            height=8,
            wrap=tk.WORD,
            font=("Courier", 8),
            bg="gray20",
            fg="white",
            yscrollcommand=log_scrollbar.set
        )
        self.error_log_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.error_log_display.yview)
        self.error_log_display.config(state=tk.DISABLED)

        # Log control buttons
        log_btn_frame = ttk.Frame(log_panel_frame)
        log_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(log_btn_frame, text="🔄 Refresh Log", command=self._refresh_error_log_display).pack(side=tk.LEFT, padx=3)
        ttk.Button(log_btn_frame, text="🗑️ Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=3)
        ttk.Button(log_btn_frame, text="📋 Copy All", command=lambda: self._copy_log_text(self.error_log_display)).pack(side=tk.LEFT, padx=3)

        # Main canvas with scrollbar
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(canvas_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(canvas_frame, yscrollcommand=scrollbar.set, bg="gray20", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.canvas.yview)

        self.frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.frame, anchor="nw")

        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)

        # Status bar at bottom
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
    
    def load_config(self):
        """Load configuration from file."""
        if Path(self.CONFIG_FILE).exists():
            try:
                logger.info(f"Loading configuration from {self.CONFIG_FILE}")
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.hidden_images = set(config.get("hidden", []))
                    # Load settings
                    self.output_directory = Path(config.get("output_directory", str(Path.cwd())))
                    self.preferred_player_setting = config.get("preferred_player", "auto")
                logger.info(f"Loaded {len(self.hidden_images)} hidden images from config")
                logger.info(f"Output directory: {self.output_directory}")
            except json.JSONDecodeError as e:
                error_msg = f"Configuration file is corrupted:\n\n{str(e)}\n\nDeleting corrupted config..."
                logger.error(f"JSON decode error loading config: {error_msg}")
                try:
                    Path(self.CONFIG_FILE).unlink()
                    logger.info("Deleted corrupted config file")
                except Exception as delete_err:
                    logger.error(f"Failed to delete corrupted config: {delete_err}")
            except Exception as e:
                error_msg = f"Failed to load configuration:\n\n{str(e)}\n\n{traceback.format_exc()}"
                logger.error(f"Error loading config: {error_msg}")

    def save_config(self):
        """Save configuration to file."""
        try:
            config = {
                "hidden": list(self.hidden_images),
                "output_directory": str(self.output_directory),
                "preferred_player": self.preferred_player_setting
            }
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            logger.debug(f"Saved configuration with {len(self.hidden_images)} hidden images")
            logger.debug(f"Saved output directory: {self.output_directory}")
        except Exception as e:
            error_msg = f"Failed to save configuration:\n\n{str(e)}\n\n{traceback.format_exc()}"
            logger.error(f"Error saving config: {error_msg}")
    
    def load_images(self):
        """Load and display images with improved UX."""
        try:
            logger.debug("Loading images...")
            # Clear existing widgets
            for widget in self.frame.winfo_children():
                widget.destroy()

            # Get all image files
            all_images = list(Path.cwd().glob("*.jpg")) + list(Path.cwd().glob("*.JPG")) + \
                         list(Path.cwd().glob("*.png")) + list(Path.cwd().glob("*.PNG"))
            logger.debug(f"Found {len(all_images)} image files")

            # Filter by search
            search_term = self.search_var.get().lower()
            self.images = [img for img in all_images if search_term in img.name.lower()]

            # Sort
            sort_by = self.sort_var.get()
            if sort_by == "name":
                self.images.sort(key=lambda x: x.name)
            elif sort_by == "date modified":
                self.images.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            elif sort_by == "file size":
                self.images.sort(key=lambda x: x.stat().st_size, reverse=True)

            # Update statistics
            visible_count = len([img for img in self.images if str(img) not in self.hidden_images])
            hidden_count = len(self.hidden_images)
            total_size = sum(img.stat().st_size for img in self.images) / (1024 * 1024)

            stats_text = f"Total: {len(self.images)} images | Visible: {visible_count} | Hidden: {hidden_count} | Size: {total_size:.1f} MB"
            self.stats_label.config(text=stats_text)
            logger.debug(f"Statistics: {stats_text}")

            # Display images or empty state
            if not self.images:
                empty_frame = ttk.Frame(self.frame)
                empty_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=40)

                ttk.Label(empty_frame, text="📁 No images found", font=("Arial", 16, "bold")).pack(pady=10)
                ttk.Label(empty_frame, text="Click 'Add Images' to get started", font=("Arial", 12)).pack(pady=5)

                self.status_bar.config(text="No images in current directory")
                logger.info("No images found in current directory")
            else:
                for img_path in self.images:
                    self.create_image_widget(img_path)

                self.status_bar.config(text=f"Loaded {len(self.images)} image(s)")
                logger.info(f"Successfully loaded {len(self.images)} image(s)")
        except Exception as e:
            error_msg = f"Failed to load images:\n\n{str(e)}\n\n{traceback.format_exc()}"
            logger.error(f"Error loading images: {error_msg}")
            self._show_error("Error", error_msg, "error")
    
    def create_image_widget(self, img_path):
        """Create a widget for an image with improved UX."""
        is_hidden = str(img_path) in self.hidden_images

        # Image frame with better styling
        img_frame = tk.Frame(self.frame, bg="gray30", relief=tk.RAISED, borderwidth=1)
        img_frame.pack(fill=tk.X, padx=8, pady=6)

        # Thumbnail with border
        thumb = self.get_thumbnail(img_path)
        thumb_label = tk.Label(img_frame, image=thumb, bg="gray20", relief=tk.SUNKEN, borderwidth=2)
        thumb_label.image = thumb
        thumb_label.pack(side=tk.LEFT, padx=8, pady=8)

        # Info frame
        info_frame = tk.Frame(img_frame, bg="gray30")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Filename with better styling
        filename_frame = tk.Frame(info_frame, bg="gray30")
        filename_frame.pack(fill=tk.X, pady=4)
        ttk.Label(filename_frame, text="📄", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        filename_label = tk.Label(filename_frame, text=img_path.name, fg="cyan", bg="gray30",
                                   font=("Arial", 10, "bold"), wraplength=300, justify=tk.LEFT)
        filename_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # File info with better formatting
        stat = img_path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        date_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

        info_text = f"📊 {size_mb:.2f} MB  |  📅 {date_str}"
        ttk.Label(info_frame, text=info_text, foreground="gray80").pack(anchor=tk.W, pady=2)

        # Status badge
        status_text = "🚫 HIDDEN" if is_hidden else "✅ INCLUDED"
        status_color = "orange" if is_hidden else "green"
        status_label = tk.Label(info_frame, text=status_text, fg=status_color, bg="gray30",
                                font=("Arial", 9, "bold"))
        status_label.pack(anchor=tk.W, pady=2)

        # Buttons frame with better layout
        btn_frame = tk.Frame(img_frame, bg="gray30")
        btn_frame.pack(side=tk.RIGHT, padx=8, pady=8)

        ttk.Button(btn_frame, text="✏️ Rename",
                  command=lambda: self.rename_image(img_path)).pack(side=tk.LEFT, padx=3, pady=2)

        toggle_text = "👁️ Show" if is_hidden else "👁️‍🗨️ Hide"
        ttk.Button(btn_frame, text=toggle_text,
                  command=lambda: self.toggle_hide(img_path)).pack(side=tk.LEFT, padx=3, pady=2)

        ttk.Button(btn_frame, text="🗑️ Remove",
                  command=lambda: self.remove_image(img_path)).pack(side=tk.LEFT, padx=3, pady=2)
    
    def get_thumbnail(self, img_path, size=(100, 100)):
        """Get or create thumbnail."""
        key = str(img_path)
        if key not in self.thumbnails:
            try:
                logger.debug(f"Creating thumbnail for {img_path.name}")
                img = Image.open(img_path)
                img.thumbnail(size)
                self.thumbnails[key] = ImageTk.PhotoImage(img)
            except Exception as e:
                error_msg = f"Error loading thumbnail for {img_path.name}:\n\n{str(e)}"
                logger.warning(f"Thumbnail error: {error_msg}")
                # Return None instead of crashing
                self.thumbnails[key] = None
        return self.thumbnails.get(key)
    
    def add_images(self):
        """Add images from file dialog with improved feedback."""
        try:
            logger.info("Opening file dialog to add images")
            files = filedialog.askopenfilenames(
                title="Select images to add",
                filetypes=[("Image files", "*.jpg *.JPG *.png *.PNG"), ("All files", "*.*")]
            )
            if files:
                logger.info(f"Selected {len(files)} image(s) to add")

                # Copy selected images to current directory
                import shutil
                copied_count = 0
                skipped_count = 0

                for file_path in files:
                    try:
                        src = Path(file_path)
                        dst = Path.cwd() / src.name

                        # Check if file already exists in current directory
                        if dst.exists():
                            logger.debug(f"Image already exists: {dst.name}")
                            skipped_count += 1
                        else:
                            # Copy file to current directory
                            shutil.copy2(src, dst)
                            logger.info(f"Copied image: {dst.name}")
                            copied_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to copy {file_path}: {str(e)}")
                        skipped_count += 1

                # Update status
                total_added = copied_count + skipped_count
                if copied_count > 0:
                    msg = f"✅ Added {copied_count} image(s)"
                    if skipped_count > 0:
                        msg += f" ({skipped_count} already existed)"
                    self.status_bar.config(text=msg)
                    messagebox.showinfo("Success", msg)
                    logger.info(f"Successfully added {copied_count} image(s), skipped {skipped_count}")
                else:
                    msg = f"⚠️ All {skipped_count} image(s) already existed"
                    self.status_bar.config(text=msg)
                    messagebox.showwarning("Info", msg)
                    logger.info(f"All images already existed")

                # Reload images to display them
                self.load_images()
        except Exception as e:
            error_msg = f"Failed to add images:\n\n{str(e)}\n\n{traceback.format_exc()}"
            logger.error(f"Error adding images: {error_msg}")
            self._show_error("Error", error_msg, "error")

    def rename_image(self, img_path):
        """Rename an image with validation."""
        current_name = img_path.stem
        new_name = simpledialog.askstring(
            "Rename Image",
            f"Current name: {img_path.name}\n\nEnter new name (without extension):",
            initialvalue=current_name
        )
        if new_name and new_name != current_name:
            if not new_name.endswith(img_path.suffix):
                new_name += img_path.suffix
            new_path = img_path.parent / new_name

            # Check if file already exists
            if new_path.exists():
                logger.warning(f"File already exists: {new_name}")
                self._show_error("Error", f"File '{new_name}' already exists", "error")
                return

            try:
                logger.info(f"Renaming {img_path.name} to {new_name}")
                img_path.rename(new_path)
                self.load_images()
                messagebox.showinfo("Success", f"✅ Renamed to {new_name}")
                self.status_bar.config(text=f"Renamed: {new_name}")
                logger.info(f"Successfully renamed {img_path.name} to {new_name}")
            except PermissionError as e:
                error_msg = f"Permission denied when renaming:\n\n{str(e)}\n\nCheck file permissions."
                logger.error(f"Permission error renaming {img_path.name}: {e}")
                self._show_error("Permission Error", error_msg, "error")
            except Exception as e:
                error_msg = f"Failed to rename:\n\n{str(e)}\n\n{traceback.format_exc()}"
                logger.error(f"Failed to rename {img_path.name}: {error_msg}")
                self._show_error("Error", error_msg, "error")
    
    def toggle_hide(self, img_path):
        """Toggle hide status of an image with feedback."""
        key = str(img_path)
        if key in self.hidden_images:
            self.hidden_images.remove(key)
            action = "shown"
            emoji = "👁️"
        else:
            self.hidden_images.add(key)
            action = "hidden"
            emoji = "🚫"

        self.save_config()
        self.load_images()
        self.status_bar.config(text=f"{emoji} Image {action}: {img_path.name}")
        logging.info(f"Image {action}: {img_path.name}")

    def remove_image(self, img_path):
        """Remove an image with confirmation."""
        if messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete:\n\n{img_path.name}?\n\nThis cannot be undone."
        ):
            try:
                logger.info(f"Deleting image: {img_path.name}")
                img_path.unlink()
                self.load_images()
                messagebox.showinfo("Success", f"✅ Image deleted: {img_path.name}")
                self.status_bar.config(text=f"Deleted: {img_path.name}")
                logger.info(f"Successfully deleted image: {img_path.name}")
            except PermissionError as e:
                error_msg = f"Permission denied when deleting:\n\n{str(e)}\n\nCheck file permissions."
                logger.error(f"Permission error deleting {img_path.name}: {e}")
                self._show_error("Permission Error", error_msg, "error")
            except Exception as e:
                error_msg = f"Failed to delete:\n\n{str(e)}\n\n{traceback.format_exc()}"
                logger.error(f"Failed to delete {img_path.name}: {error_msg}")
                self._show_error("Error", error_msg, "error")
    
    def create_slideshow(self):
        """Create slideshow from visible images with improved UX."""
        if self.is_creating:
            logger.warning("Slideshow creation already in progress")
            self._show_warning(
                "In Progress",
                "A slideshow is already being created. Please wait.",
            )
            return

        visible_images = [img for img in self.images if str(img) not in self.hidden_images]

        if not visible_images:
            logger.warning("No visible images to create slideshow")
            self._show_warning(
                "No Visible Images",
                "All images are hidden. Please show some images first.\n\n"
                "Tip: Click 'Show' on hidden images to include them in the slideshow."
            )
            return

        if len(visible_images) < 2:
            logger.warning(f"Too few images: {len(visible_images)}")
            self._show_warning(
                "Too Few Images",
                f"You need at least 2 images to create a slideshow.\n"
                f"Currently visible: {len(visible_images)}"
            )
            return

        output_name = simpledialog.askstring(
            "Slideshow Name",
            f"Enter slideshow name:\n\n"
            f"(Using {len(visible_images)} visible image(s))\n"
            f"(Saving to: {self.output_directory})",
            initialvalue=f"slideshow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )

        if not output_name:
            return

        if not output_name.endswith(".mp4"):
            output_name += ".mp4"

        # Full path with output directory
        output_path = self.output_directory / output_name

        # Check if file already exists
        if output_path.exists():
            if not messagebox.askyesno("File Exists", f"{output_name} already exists. Overwrite?"):
                return

        # Run in thread to avoid freezing UI
        self.is_creating = True
        thread = threading.Thread(target=self._create_slideshow_thread, args=(str(output_path), visible_images))
        thread.daemon = True
        thread.start()

    def _show_slideshow_success(self, video_path, message):
        """Show success dialog with play button."""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("✅ Slideshow Created")
            dialog.geometry("500x300")
            dialog.resizable(False, False)

            # Center on parent
            dialog.transient(self.root)
            dialog.grab_set()

            # Message
            msg_frame = ttk.Frame(dialog)
            msg_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            ttk.Label(msg_frame, text=message, font=("Arial", 10), justify=tk.LEFT).pack(anchor=tk.W)

            # Buttons
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(fill=tk.X, padx=20, pady=10)

            # Play button (only if players available)
            if self.available_players:
                player_info = f"({self.preferred_player})"
                ttk.Button(
                    btn_frame,
                    text=f"▶️ Play {player_info}",
                    command=lambda: (self.play_video(video_path), dialog.destroy())
                ).pack(side=tk.LEFT, padx=5)

            ttk.Button(btn_frame, text="📁 Open Folder", command=lambda: self._open_folder(video_path)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="✅ Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

            logger.debug(f"Slideshow success dialog shown for: {video_path}")

        except Exception as e:
            logger.error(f"Error showing success dialog: {str(e)}")
            messagebox.showinfo("Success", message)

    def _open_folder(self, file_path):
        """Open folder containing the file."""
        try:
            file_path = Path(file_path)
            folder = file_path.parent

            if sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            elif sys.platform == "linux":
                subprocess.Popen(["xdg-open", str(folder)])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", str(folder)])

            logger.info(f"Opened folder: {folder}")
        except Exception as e:
            logger.error(f"Error opening folder: {str(e)}")
            self._show_error("Error", f"Failed to open folder:\n{str(e)}", "error")

    def _create_slideshow_thread(self, output_name, visible_images):
        """Create slideshow in background thread with progress feedback."""
        try:
            self.root.after(0, lambda: self.status_bar.config(text="🎬 Creating slideshow..."))
            logger.info(f"Starting slideshow creation: {output_name}")
            logger.info(f"Images: {len(visible_images)}, Output: {output_name}")

            # Create temporary directory with symlinks to visible images
            temp_dir = Path(".slideshow_temp")
            temp_dir.mkdir(exist_ok=True)
            logger.debug(f"Created temp directory: {temp_dir}")

            # Create numbered symlinks with consistent PNG extension for FFmpeg image2 demuxer
            # Convert all to PNG pattern so FFmpeg can find them with %04d.png
            for i, img_path in enumerate(visible_images):
                # Create symlink with simple numbered name and .png extension
                link_path = temp_dir / f"{i+1:04d}.png"
                if link_path.exists():
                    link_path.unlink()
                link_path.symlink_to(img_path.resolve())
            logger.debug(f"Created {len(visible_images)} symlinks in temp directory")

            # Use image2 demuxer with sequential numbering (original working method)
            # This avoids green artifacts from concat demuxer
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-framerate", "1/5",
                "-i", str(temp_dir / "%04d.png"),
                "-vf", (
                    "format=yuv420p,"
                    "scale='min(1920,iw*min(1920/iw\\,1080/ih))':'min(1080,ih*min(1920/iw\\,1080/ih))':force_original_aspect_ratio=decrease,"
                    "pad=1920:1080:(1920-iw)/2:(1080-ih)/2"
                ),
                "-c:v", "libx264",
                "-r", "30",
                "-pix_fmt", "yuv420p",
                output_name
            ]

            logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.debug(f"FFmpeg completed successfully")

            # Cleanup
            for file in temp_dir.glob("*"):
                file.unlink()
            temp_dir.rmdir()
            logger.debug("Cleaned up temporary directory")

            file_size = Path(output_name).stat().st_size / (1024 * 1024)
            success_msg = (
                f"✅ Slideshow created successfully!\n\n"
                f"File: {output_name}\n"
                f"Size: {file_size:.1f} MB\n"
                f"Images: {len(visible_images)}\n"
                f"Duration: ~{len(visible_images) * 5} seconds"
            )

            # Track last created slideshow for quick play
            self.last_slideshow_path = str(output_name)
            self.root.after(0, lambda: self.play_last_btn.config(state=tk.NORMAL))

            # Show success dialog with play option
            self.root.after(0, lambda: self._show_slideshow_success(output_name, success_msg))
            self.root.after(0, lambda: self.status_bar.config(text=f"✅ Slideshow created: {output_name}"))
            logger.info(f"Slideshow created successfully: {output_name} ({file_size:.1f} MB)")

        except subprocess.CalledProcessError as e:
            error_msg = (
                f"FFmpeg Error\n\n"
                f"Return Code: {e.returncode}\n"
                f"Command: {' '.join(e.cmd)}\n\n"
                f"STDOUT:\n{e.stdout}\n\n"
                f"STDERR:\n{e.stderr}"
            )
            logger.error(f"FFmpeg error: {error_msg}")
            self.root.after(0, lambda: self._show_error("FFmpeg Error", error_msg, "error"))
            self.root.after(0, lambda: self.status_bar.config(text="❌ Failed to create slideshow"))

        except Exception as e:
            error_msg = f"Failed to create slideshow:\n\n{str(e)}\n\n{traceback.format_exc()}"
            logger.error(f"Error creating slideshow: {error_msg}")
            self.root.after(0, lambda: self._show_error("Error", error_msg, "error"))
            self.root.after(0, lambda: self.status_bar.config(text="❌ Error creating slideshow"))

        finally:
            self.is_creating = False
            logger.info("Slideshow creation thread finished")


def main():
    """Main function."""
    root = tk.Tk()
    app = SlideshowManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()

