from pathlib import Path
import shutil
import subprocess
import sys
import tkinter as tk

# Add src to path for imports
SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.ui.chat_widget import ChatWidget

ROOT = Path(__file__).resolve().parents[3]
VIDEO_DIR = ROOT / "assets" / "media" / "animations"
MP4_PATH = VIDEO_DIR / "robo.mp4"
SIZE = 320
FPS = 24
CROP_SIZE = 640
FRAMES_DIR = VIDEO_DIR / f"robo_frames_{SIZE}_v1"
BG_KEY = "#06090f"
BUTTON_SIZE = 32


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

        # Container frame for entire layout (animation + button + chat)
        self.container = tk.Frame(root, bg=BG_KEY)
        self.container.pack(fill="both", expand=True)

        # Animation frame
        anim_frame = tk.Frame(self.container, bg=BG_KEY, width=SIZE, height=SIZE)
        anim_frame.pack(side="top", fill="both", expand=True)
        anim_frame.pack_propagate(False)

        self.label = tk.Label(anim_frame, bg=BG_KEY, bd=0, highlightthickness=0)
        self.label.pack(fill="both", expand=True)

        # Button frame (below animation)
        button_frame = tk.Frame(self.container, bg=BG_KEY, height=BUTTON_SIZE)
        button_frame.pack(side="top", fill="x", padx=5, pady=5)
        button_frame.pack_propagate(False)

        # Chat toggle button
        self.chat_btn = tk.Button(
            button_frame,
            text="💬",
            command=self.toggle_chat,
            bg="#0d0d0d",
            fg="#00ff00",
            font=("Mono", 14),
            relief="flat",
            bd=1,
            width=3,
            height=1,
        )
        self.chat_btn.pack(side="left", padx=2)

        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self._bind_drag(self.root)
        self._bind_drag(self.label)

        self.frames = []
        self.index = 0
        self.delay_ms = int(1000 / FPS)

        # Chat widget container
        self.chat_container = tk.Frame(self.container, bg=BG_KEY)
        # Initially don't pack - will be packed on toggle

        # Create chat widget inside container
        self.chat_widget = ChatWidget(self.chat_container, height=200)
        self.chat_widget_visible = False

        self.load_frames()
        self.position_window()
        self.animate()

    def position_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, sw - SIZE - 26)
        y = 72
        # Small window initially (animation + button)
        self.root.geometry(f"{SIZE}x{SIZE + BUTTON_SIZE + 10}+{x}+{y}")

    def _bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self.start_drag)
        widget.bind("<B1-Motion>", self.on_drag)

    def start_drag(self, event):
        self.drag_offset_x = event.x_root - self.root.winfo_x()
        self.drag_offset_y = event.y_root - self.root.winfo_y()

    def on_drag(self, event):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        x = event.x_root - self.drag_offset_x
        y = event.y_root - self.drag_offset_y

        max_x = max(0, sw - SIZE)
        max_y = max(0, sh - (SIZE + BUTTON_SIZE + 10))

        x = min(max(0, x), max_x)
        y = min(max(0, y), max_y)

        self.root.geometry(f"{SIZE}x{SIZE + BUTTON_SIZE + 10}+{x}+{y}")

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

    def toggle_chat(self):
        """Toggle chat panel visibility."""
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x_pos = max(0, sw - SIZE - 26)

        if self.chat_widget_visible:
            # Hide chat
            self.chat_container.pack_forget()
            self.root.geometry(f"{SIZE}x{SIZE + BUTTON_SIZE + 10}+{x_pos}+72")
            self.chat_widget_visible = False
        else:
            # Show chat
            self.chat_container.pack(side="top", fill="both", expand=True, padx=0, pady=0)
            # Expand window to show chat
            y_pos = max(0, sh - 450)
            self.root.geometry(f"{SIZE}x450+{x_pos}+{y_pos}")
            self.chat_widget_visible = True
            self.chat_widget.input_field.focus()


def main():
    root = tk.Tk()
    RoboPopupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
