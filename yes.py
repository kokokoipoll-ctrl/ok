"""
Geometry Dash - Tkinter Edition
--------------------------------
A single-file clone of Geometry Dash built with pure Python + tkinter.

Controls:
    SPACE / UP ARROW / LEFT CLICK - Jump
    R                             - Restart after Game Over

Run:
    python geometry_dash.py
"""

import math
import random
import tkinter as tk

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 400
GROUND_Y = HEIGHT - 50
FPS_MS = 16                 # ~60 FPS

GRAVITY = 0.9
JUMP_VELOCITY = -15
PLAYER_SIZE = 30

BASE_SPEED = 6
MAX_SPEED = 14

BG_COLOR = "#1e1e2f"
GROUND_COLOR = "#2c2c44"
GRID_COLOR = "#26263d"
ACCENT_COLOR = "#00e5ff"
PLAYER_COLOR = "#00e5ff"
SPIKE_COLOR = "#ff3860"
BLOCK_COLOR = "#7b2ff7"
TEXT_COLOR = "#ffffff"


class GeometryDash:
    def __init__(self, root):
        self.root = root
        self.root.title("Geometry Dash - Tkinter Edition")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root, width=WIDTH, height=HEIGHT, bg=BG_COLOR, highlightthickness=0
        )
        self.canvas.pack()

        # Input bindings
        self.root.bind("<space>", self.on_jump)
        self.root.bind("<Up>", self.on_jump)
        self.root.bind("<r>", self.on_restart)
        self.root.bind("<R>", self.on_restart)
        self.canvas.bind("<Button-1>", self.on_jump)
        self.root.focus_set()

        self.reset_state()
        self.loop()

    # -----------------------------------------------------------------
    # Setup / reset
    # -----------------------------------------------------------------
    def reset_state(self):
        self.canvas.delete("all")

        self.player_x = 100
        self.player_y = GROUND_Y - PLAYER_SIZE
        self.vel_y = 0
        self.on_ground = True
        self.rotation = 0

        self.obstacles = []
        self.speed = BASE_SPEED
        self.score = 0
        self.distance = 0
        self.next_spawn = 400

        self.game_over = False
        self.started = False

        self.draw_static_background()

        self.player = self.canvas.create_polygon(
            self.player_points(), fill=PLAYER_COLOR, outline=TEXT_COLOR, width=2
        )

        self.score_text = self.canvas.create_text(
            10, 10, anchor="nw", fill=TEXT_COLOR,
            font=("Consolas", 14, "bold"), text="Score: 0"
        )

        self.msg_text = self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 40, fill=TEXT_COLOR,
            font=("Consolas", 20, "bold"),
            text="Press SPACE / click to start"
        )

    def draw_static_background(self):
        for x in range(0, WIDTH, 40):
            self.canvas.create_line(x, 0, x, GROUND_Y, fill=GRID_COLOR)
        self.canvas.create_rectangle(
            0, GROUND_Y, WIDTH, HEIGHT, fill=GROUND_COLOR, outline=""
        )
        self.canvas.create_line(0, GROUND_Y, WIDTH, GROUND_Y, fill=ACCENT_COLOR, width=2)

    # -----------------------------------------------------------------
    # Player geometry
    # -----------------------------------------------------------------
    def player_points(self):
        cx = self.player_x + PLAYER_SIZE / 2
        cy = self.player_y + PLAYER_SIZE / 2
        half = PLAYER_SIZE / 2
        corners = [(-half, -half), (half, -half), (half, half), (-half, half)]
        rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        pts = []
        for dx, dy in corners:
            rx = dx * cos_r - dy * sin_r
            ry = dx * sin_r + dy * cos_r
            pts.extend([cx + rx, cy + ry])
        return pts

    # -----------------------------------------------------------------
    # Input
    # -----------------------------------------------------------------
    def on_jump(self, event=None):
        if self.game_over:
            return
        if not self.started:
            self.started = True
            self.canvas.itemconfig(self.msg_text, text="")
        if self.on_ground:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False

    def on_restart(self, event=None):
        if self.game_over:
            self.reset_state()

    # -----------------------------------------------------------------
    # Obstacles
    # -----------------------------------------------------------------
    def spawn_obstacle(self):
        kind = random.choice(["spike", "spike", "block", "double_spike"])
        x = WIDTH + 20
        base_y = GROUND_Y

        if kind == "spike":
            w, h = 30, 30
            pts = [x, base_y, x + w / 2, base_y - h, x + w, base_y]
            item = self.canvas.create_polygon(pts, fill=SPIKE_COLOR, outline=TEXT_COLOR, width=2)
            self.obstacles.append({"x": x, "y": base_y - h, "w": w, "h": h, "id": item})

        elif kind == "double_spike":
            w, h = 60, 30
            pts = [
                x, base_y,
                x + w / 4, base_y - h,
                x + w / 2, base_y,
                x + 3 * w / 4, base_y - h,
                x + w, base_y,
            ]
            item = self.canvas.create_polygon(pts, fill=SPIKE_COLOR, outline=TEXT_COLOR, width=2)
            self.obstacles.append({"x": x, "y": base_y - h, "w": w, "h": h, "id": item})

        else:  # block
            w = 30
            h = random.choice([30, 60, 90])
            y = base_y - h
            item = self.canvas.create_rectangle(
                x, y, x + w, y + h, fill=BLOCK_COLOR, outline=TEXT_COLOR, width=2
            )
            self.obstacles.append({"x": x, "y": y, "w": w, "h": h, "id": item})

    def update_obstacles(self):
        remove = []
        for obs in self.obstacles:
            obs["x"] -= self.speed
            self.canvas.move(obs["id"], -self.speed, 0)
            if obs["x"] + obs["w"] < 0:
                remove.append(obs)
        for obs in remove:
            self.canvas.delete(obs["id"])
            self.obstacles.remove(obs)

    # -----------------------------------------------------------------
    # Collision
    # -----------------------------------------------------------------
    def check_collision(self):
        # Slightly shrink the hitbox for a fairer feel
        pad = 4
        px1 = self.player_x + pad
        py1 = self.player_y + pad
        px2 = self.player_x + PLAYER_SIZE - pad
        py2 = self.player_y + PLAYER_SIZE - pad

        for obs in self.obstacles:
            ox1, oy1 = obs["x"], obs["y"]
            ox2, oy2 = obs["x"] + obs["w"], obs["y"] + obs["h"]
            if px1 < ox2 and px2 > ox1 and py1 < oy2 and py2 > oy1:
                return True
        return False

    def end_game(self):
        self.game_over = True
        self.canvas.itemconfig(
            self.msg_text,
            text=f"Game Over!  Score: {self.score}\nPress R to restart"
        )

    # -----------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------
    def loop(self):
        if not self.game_over and self.started:
            # --- physics ---
            self.vel_y += GRAVITY
            self.player_y += self.vel_y

            if self.player_y >= GROUND_Y - PLAYER_SIZE:
                self.player_y = GROUND_Y - PLAYER_SIZE
                self.vel_y = 0
                self.on_ground = True
            else:
                self.on_ground = False

            # rotate while airborne, snap upright on landing
            if self.on_ground:
                self.rotation = 0
            else:
                self.rotation = (self.rotation + 6) % 360

            self.canvas.coords(self.player, *self.player_points())

            # --- obstacle spawning & movement ---
            self.next_spawn -= self.speed
            if self.next_spawn <= 0:
                self.spawn_obstacle()
                self.next_spawn = random.randint(180, 320)

            self.update_obstacles()

            # --- scoring & difficulty ramp ---
            self.distance += self.speed
            self.score = int(self.distance // 10)
            self.canvas.itemconfig(self.score_text, text=f"Score: {self.score}")
            self.speed = min(BASE_SPEED + (self.score // 20) * 0.5, MAX_SPEED)

            # --- collision check ---
            if self.check_collision():
                self.end_game()

        self.root.after(FPS_MS, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    GeometryDash(root)
    root.mainloop()
