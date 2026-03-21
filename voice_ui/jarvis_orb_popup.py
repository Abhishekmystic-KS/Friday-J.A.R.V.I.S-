import math
import random
import time
import tkinter as tk

GRID = 20
W = 460
CX = W / 2
CY = W / 2
RADIUS = 182
BPM = 36
BEAT_INTERVAL = 60 / BPM


def build_dots():
    dots = []
    row = 0
    while True:
        y = row * GRID
        if y - CY > RADIUS + GRID:
            break

        col = 0
        while True:
            x = col * GRID
            if x - CX > RADIUS + GRID:
                break

            dx = x - CX
            dy = y - CY
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < RADIUS:
                dots.append(
                    {
                        "x": x,
                        "y": y,
                        "normDist": dist / RADIUS,
                        "idleFreq": 5 + random.random() * 4,
                        "idlePhase": random.random() * math.pi * 2,
                        "idleAmp": 0.35 + random.random() * 0.3,
                    }
                )
            col += 1
        row += 1
    return dots


DOTS = build_dots()


class JarvisOrbApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS Orb")
        self.root.configure(bg="black")
        self.root.resizable(False, False)

        # Popup-style window behavior
        self.root.attributes("-topmost", True)

        self.canvas = tk.Canvas(
            root,
            width=W,
            height=W,
            bg="black",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.breath_phase = 0.0
        self.last_ts = time.perf_counter()
        self.time_since_beat = BEAT_INTERVAL
        self.time_total = 0.0
        self.beat_t = 999.0

        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.animate()

    @staticmethod
    def alpha_to_gray(alpha):
        # White over black with alpha -> grayscale intensity
        a = max(0.0, min(1.0, alpha))
        v = int(255 * a)
        return f"#{v:02x}{v:02x}{v:02x}"

    def animate(self):
        now = time.perf_counter()
        dt = min(now - self.last_ts, 0.05)
        self.last_ts = now

        self.time_total += dt
        self.beat_t += dt
        self.time_since_beat += dt

        if self.time_since_beat >= BEAT_INTERVAL:
            self.beat_t = 0.0
            self.time_since_beat = 0.0

        self.breath_phase += dt * (math.pi / 6)
        breath = math.sin(self.breath_phase) * 0.5 + 0.5

        wave_dur = 1.2
        wave_speed = 1.0 / wave_dur

        wave_front = -1.0
        wave_amp = 0.0

        if self.beat_t < wave_dur:
            wave_front = self.beat_t * wave_speed
            wave_amp = 1.0 - (self.beat_t / wave_dur) * 0.5

        self.canvas.delete("all")

        for dot in DOTS:
            x = dot["x"]
            y = dot["y"]
            norm_dist = dot["normDist"]

            rest_r = 2.8 + (1 - norm_dist) * 1.0
            idle_wiggle = math.sin(self.time_total * dot["idleFreq"] + dot["idlePhase"]) * dot[
                "idleAmp"
            ]

            wave_grow = 0.0
            wave_alpha = 0.0

            if wave_front >= 0:
                d = norm_dist - wave_front
                bell = math.exp(-(d * d) / 0.012) * wave_amp
                wave_grow = bell * 9.5
                wave_alpha = bell * 0.72

            br_r = breath * 0.6
            r = max(1.4, rest_r + idle_wiggle + wave_grow + br_r)

            base_alpha = 0.26 + breath * 0.05
            alpha = min(0.97, base_alpha + wave_alpha)

            color = self.alpha_to_gray(alpha)
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=color)

        self.root.after(16, self.animate)  # ~60 FPS


def main():
    root = tk.Tk()

    # Center popup on screen
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - W) // 2
    root.geometry(f"{W}x{W}+{x}+{y}")

    JarvisOrbApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
