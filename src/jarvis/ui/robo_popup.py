from pathlib import Path
import shutil
import subprocess
import sys
import tkinter as tk

# Add src to path for imports
SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.ui.chat_window import launch_chat_window

ROOT = Path(__file__).resolve().parents[3]
VIDEO_DIR = ROOT / "assets" / "media" / "animations"
MP4_PATH = VIDEO_DIR / "robo.mp4"
SIZE = 320
FPS = 24
CROP_SIZE = 640
FRAMES_DIR = VIDEO_DIR / f"robo_frames_{SIZE}_v1"
BG_KEY = "#06090f"


def ensure_frames():
    if not MP4_PATH.exists():
        return False

    frame_pattern = "frame_*.png"
    has_frames = FRAMES_DIR.exists() and any(FRAMES_DIR.glob(frame_pattern))
    up_to_date = has_frames and FRAMES_DIR.stat().st_mtime >= MP4_PATH.stat().st_mtime
    if up_to_date:
        return True

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for png in FRAMES_DIR.glob("frame_*.png"):
        try:
            png.unlink()
        except Exception:
            pass

    try:
        frames_cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(MP4_PATH),
            "-vf",
            (
                f"fps={FPS},crop={CROP_SIZE}:{CROP_SIZE}:(iw-{CROP_SIZE})/2:(ih-{CROP_SIZE})/2,"
                f"scale={SIZE}:{SIZE}:flags=lanczos,"
                "eq=brightness=0.08:contrast=1.25:saturation=1.25,format=rgb24"
            ),
            str(FRAMES_DIR / "frame_%05d.png"),
        ]
        subprocess.run(frames_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return any(FRAMES_DIR.glob(frame_pattern))
    except Exception:
        return False


class RoboPopupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FRIDAY")
        self.root.configure(bg=BG_KEY)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Main container
        self.main_frame = tk.Frame(root, bg=BG_KEY)
        self.main_frame.pack(fill="both", expand=True)

        # Animation label
        self.label = tk.Label(self.main_frame, bg=BG_KEY, bd=0, highlightthickness=0)
        self.label.pack(fill="both", expand=True)

        # Button frame (below animation)
        button_frame = tk.Frame(self.main_frame, bg=BG_KEY, height=40)
        button_frame.pack(fill="x", padx=5, pady=5)
        button_frame.pack_propagate(False)

        # Chat button
        self.chat_btn = tk.Button(
            button_frame,
            text="✨ Chat",
            command=self.open_chat,
            bg="#89b4fa",
            fg="#11111b",
            activebackground="#b4befe",
            activeforeground="#11111b",
            font=("Helvetica", 10, "bold"),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            padx=15,
            pady=5,
        )
        self.chat_btn.pack(side="left", padx=5)

        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.is_dragging = False
        
        # Bind drag events to label (animation area only)
        self.label.bind("<ButtonPress-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.on_drag)
        self.label.bind("<ButtonRelease-1>", self.stop_drag)

        self.frames = []
        self.index = 0
        self.delay_ms = int(1000 / FPS)

        self.load_frames()
        self.position_window()
        self.animate()

    def position_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        x = max(0, sw - SIZE - 26)
        y = 72
        # Fixed size: animation (320x320) + button (40px) + padding
        self.root.geometry(f"{SIZE}x370+{x}+{y}")

    def start_drag(self, event):
        """Start dragging animation area."""
        self.drag_offset_x = event.x_root - self.root.winfo_x()
        self.drag_offset_y = event.y_root - self.root.winfo_y()
        self.is_dragging = True

    def on_drag(self, event):
        """Handle window dragging."""
        if not self.is_dragging:
            return
            
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        x = event.x_root - self.drag_offset_x
        y = event.y_root - self.drag_offset_y

        max_x = max(0, sw - SIZE)
        max_y = max(0, sh - 370)

        x = min(max(0, x), max_x)
        y = min(max(0, y), max_y)

        self.root.geometry(f"{SIZE}x370+{x}+{y}")

    def stop_drag(self, event):
        """Stop dragging."""
        self.is_dragging = False

    def load_frames(self):
        if not ensure_frames():
            self.label.configure(text="FRIDAY", fg="white", font=("Arial", 26, "bold"))
            return

        for frame_path in sorted(FRAMES_DIR.glob("frame_*.png")):
            try:
                frame = tk.PhotoImage(file=str(frame_path))
            except tk.TclError:
                continue
            self.frames.append(frame)

        if not self.frames:
            self.label.configure(text="FRIDAY", fg="white", font=("Arial", 26, "bold"))

    def animate(self):
        if self.frames:
            self.label.configure(image=self.frames[self.index], text="")
            self.index = (self.index + 1) % len(self.frames)
        self.root.after(self.delay_ms, self.animate)

    def open_chat(self):
        """Launch standalone chat window."""
        launch_chat_window()


def main():
    root = tk.Tk()
    RoboPopupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
