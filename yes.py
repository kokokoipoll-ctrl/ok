import json
import math
import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox

WIDTH, HEIGHT = 960, 540
GROUND_Y = HEIGHT - 85
FPS_MS = 1000 // 120

# --- Physics ---------------------------------------------------------------
# Tuned so the jump apex comfortably clears the tallest auto-generated
# obstacle (60px block) with margin, while still feeling snappy.
GRAVITY = 0.6
JUMP_VELOCITY = -13.0
PLAYER_SIZE = 32
BASE_SPEED = 6.5
MAX_SPEED = 15.0

# Jump apex height (used to sanity-check obstacle heights):
#   h = v^2 / (2*g)
JUMP_APEX_HEIGHT = (JUMP_VELOCITY ** 2) / (2 * GRAVITY)

CUBE = 30  # grid cell size used by the editor and auto-spawner

# --- Obstacle spawner (time-based, not distance-based) ---------------------
# Old code decremented a fixed pixel countdown by `speed` each frame, which
# meant the *time* between obstacles shrank as speed increased -> unfair /
# impossible late-game. We now count down in frames so the reaction time
# stays constant regardless of current speed; obstacles simply end up
# visually closer together at high speed, same as real Geometry Dash.
MIN_SPAWN_FRAMES = 70
MAX_SPAWN_FRAMES = 120

# Max height (px) for an obstacle that's part of the endless auto-generated
# stream. Kept comfortably under JUMP_APEX_HEIGHT so a single tap always
# clears it. Hand-built editor/builtin levels can still ignore this.
AUTO_BLOCK_HEIGHTS = [CUBE, CUBE * 2]  # 30 or 60

BG_TOP = "#0b1021"
BG_BOTTOM = "#182042"
GROUND_COLOR = "#23263d"
GRID_COLOR = "#202742"
ACCENT_COLOR = "#34d7ff"
PLAYER_COLOR = "#39e6ff"
SPIKE_COLOR = "#ff4d6d"
BLOCK_COLOR = "#8a4dff"
TEXT_COLOR = "#f7fbff"
PANEL_COLOR = "#10162b"
BUTTON_COLOR = "#1a2342"
BUTTON_HOVER = "#26345f"
EDITOR_COLOR = "#16203b"

LEVELS_DIR = "levels"
CUSTOM_LEVELS_FILE = os.path.join(LEVELS_DIR, "custom_levels.json")

# Editor viewport (the region of canvas that represents the level)
EDITOR_VIEW_X0 = 240
EDITOR_VIEW_X1 = WIDTH - 20
EDITOR_LEVEL_WIDTH = 4000
EDITOR_PAN_STEP = 150


class GeometryDash:
    def __init__(self, root):
        self.root = root
        self.root.title("Geometry Dash - Tkinter Edition")
        self.root.resizable(False, False)

        os.makedirs(LEVELS_DIR, exist_ok=True)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG_TOP, highlightthickness=0)
        self.canvas.pack()

        self.root.bind("<space>", self.on_jump)
        self.root.bind("<Up>", self.on_jump)
        self.root.bind("<Button-1>", self.on_left_click)
        self.root.bind("<r>", self.on_restart)
        self.root.bind("<R>", self.on_restart)
        self.root.bind("<Escape>", self.show_menu)
        self.root.bind("<Delete>", self.editor_delete_selected)

        # Editor panning: right-mouse drag, arrow keys, or mouse wheel
        self.canvas.bind("<ButtonPress-3>", self.editor_pan_start)
        self.canvas.bind("<B3-Motion>", self.editor_pan_drag)
        self.root.bind("<Left>", self.editor_pan_key)
        self.root.bind("<Right>", self.editor_pan_key)
        self.canvas.bind("<MouseWheel>", self.editor_pan_wheel)      # Windows/Mac
        self.canvas.bind("<Button-4>", self.editor_pan_wheel)        # Linux scroll up
        self.canvas.bind("<Button-5>", self.editor_pan_wheel)        # Linux scroll down

        self.levels = self.load_builtin_levels()
        self.custom_levels = self.load_custom_levels()
        self.levels.extend(self.custom_levels)

        self.selected_level_index = 0
        self.mode = "menu"
        self.after_id = None
        self.menu_buttons = []
        self.preview_running = False

        self.editor_tool = "spike"
        self.editor_level = {"name": "New Level", "speed": 1.0, "objects": []}
        self.editor_selected_item = None
        self.editor_camera_x = 0
        self._pan_last_x = None

        self.reset_game_state()
        self.show_menu()
        self.schedule_loop()

    def schedule_loop(self):
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
        self.after_id = self.root.after(FPS_MS, self.loop)

    # ------------------------------------------------------------------
    # Level data
    # ------------------------------------------------------------------
    def load_builtin_levels(self):
        return [
            {"name": "Starter", "speed": 1.0, "objects": [
                {"type": "spike", "x": 520, "y": GROUND_Y - 30, "w": 30, "h": 30},
                {"type": "spike", "x": 650, "y": GROUND_Y - 30, "w": 30, "h": 30},
                {"type": "block", "x": 800, "y": GROUND_Y - 60, "w": 30, "h": 60},
            ]},
            {"name": "Rhythm", "speed": 1.05, "objects": [
                {"type": "spike", "x": 480, "y": GROUND_Y - 30, "w": 30, "h": 30},
                {"type": "double_spike", "x": 640, "y": GROUND_Y - 30, "w": 60, "h": 30},
                {"type": "block", "x": 820, "y": GROUND_Y - 60, "w": 30, "h": 60},
                {"type": "spike", "x": 950, "y": GROUND_Y - 30, "w": 30, "h": 30},
            ]},
        ]

    def load_custom_levels(self):
        if not os.path.exists(CUSTOM_LEVELS_FILE):
            return []
        try:
            with open(CUSTOM_LEVELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_custom_levels(self):
        custom = [lvl for lvl in self.levels if lvl.get("custom")]
        with open(CUSTOM_LEVELS_FILE, "w", encoding="utf-8") as f:
            json.dump(custom, f, indent=2)

    # ------------------------------------------------------------------
    # Shared canvas helpers
    # ------------------------------------------------------------------
    def clear_canvas_state(self):
        self.canvas.delete("all")
        self.menu_buttons = []
        self.editor_selected_item = None

    def reset_game_state(self):
        self.player_x = 120
        self.player_y = GROUND_Y - PLAYER_SIZE
        self.vel_y = 0
        self.on_ground = True
        self.rotation = 0

        self.obstacles = []
        self.particles = []
        self.speed = BASE_SPEED
        self.score = 0
        self.distance = 0
        self.next_spawn_frames = MIN_SPAWN_FRAMES
        self.game_over = False
        self.started = False
        self.level = self.levels[self.selected_level_index]
        self.bg_offset = 0
        self.clouds = self.make_clouds()
        self.stars = self.make_stars()

    def make_stars(self):
        return [{"x": random.randint(0, WIDTH), "y": random.randint(20, GROUND_Y - 160),
                 "r": random.randint(1, 2), "s": random.uniform(0.2, 0.8)} for _ in range(60)]

    def make_clouds(self):
        return [{"x": random.randint(0, WIDTH), "y": random.randint(30, 180),
                 "w": random.randint(60, 130), "h": random.randint(18, 38),
                 "s": random.uniform(0.2, 0.5)} for _ in range(7)]

    def draw_background(self):
        self.canvas.delete("bg")
        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            c = self.blend(BG_TOP, BG_BOTTOM, t)
            self.canvas.create_rectangle(0, y, WIDTH, y + 4, outline="", fill=c, tags="bg")

        for star in self.stars:
            star["x"] -= star["s"]
            if star["x"] < 0:
                star["x"] = WIDTH
                star["y"] = random.randint(20, GROUND_Y - 160)
            self.canvas.create_oval(star["x"], star["y"], star["x"] + star["r"], star["y"] + star["r"],
                                     fill="#ffffff", outline="", tags="bg")

        for cloud in self.clouds:
            cloud["x"] -= cloud["s"]
            if cloud["x"] + cloud["w"] < 0:
                cloud["x"] = WIDTH + random.randint(20, 120)
                cloud["y"] = random.randint(30, 180)
            x, y, w, h = cloud["x"], cloud["y"], cloud["w"], cloud["h"]
            self.canvas.create_oval(x, y, x + w * 0.55, y + h, fill="#2a355f", outline="", tags="bg")
            self.canvas.create_oval(x + w * 0.22, y - h * 0.3, x + w * 0.72, y + h * 1.05, fill="#2f3a67", outline="", tags="bg")
            self.canvas.create_oval(x + w * 0.46, y, x + w, y + h, fill="#2a355f", outline="", tags="bg")

        self.canvas.create_rectangle(0, GROUND_Y, WIDTH, HEIGHT, fill=GROUND_COLOR, outline="", tags="bg")
        self.canvas.create_line(0, GROUND_Y, WIDTH, GROUND_Y, fill=ACCENT_COLOR, width=3, tags="bg")
        for x in range(-int(self.bg_offset) % 40, WIDTH, 40):
            self.canvas.create_line(x, 0, x, GROUND_Y, fill=GRID_COLOR, tags="bg")
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, outline="#2c3764", width=2, tags="bg")

    def blend(self, a, b, t):
        a = a.lstrip("#")
        b = b.lstrip("#")
        ar, ag, ab = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
        br, bg, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
        r = int(ar + (br - ar) * t)
        g = int(ag + (bg - ag) * t)
        bl = int(ab + (bb - ab) * t)
        return f"#{r:02x}{g:02x}{bl:02x}"

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

    def make_button(self, x, y, w, h, text, command, tags="ui", font=("Consolas", 16, "bold")):
        rect = self.canvas.create_rectangle(x, y, x + w, y + h, fill=BUTTON_COLOR, outline="#3d4b7a", width=2, tags=(tags, "button"))
        label = self.canvas.create_text(x + w / 2, y + h / 2, text=text, fill=TEXT_COLOR, font=font, tags=(tags, "button"))
        self.menu_buttons.append((rect, label, command, x, y, x + w, y + h))
        return rect, label

    # ------------------------------------------------------------------
    # Menu / level select
    # ------------------------------------------------------------------
    def show_menu(self, event=None):
        self.mode = "menu"
        self.clear_canvas_state()
        self.reset_game_state()
        self.draw_background()
        self.canvas.create_text(WIDTH / 2, 95, text="GEOMETRY DASH", fill=TEXT_COLOR, font=("Consolas", 32, "bold"), tags="ui")
        self.canvas.create_text(WIDTH / 2, 132, text="Tkinter Edition", fill=ACCENT_COLOR, font=("Consolas", 14, "bold"), tags="ui")
        self.make_button(WIDTH / 2 - 130, 200, 260, 48, "Start Game", self.start_selected_level)
        self.make_button(WIDTH / 2 - 130, 260, 260, 48, "Level Select", self.show_level_select)
        self.make_button(WIDTH / 2 - 130, 320, 260, 48, "Level Editor", self.open_editor)
        self.make_button(WIDTH / 2 - 130, 380, 260, 48, "Quit", self.root.destroy)
        self.canvas.create_text(WIDTH / 2, 485, text="SPACE / CLICK = Jump    ESC = Menu", fill="#c7d4ff", font=("Consolas", 11), tags="ui")

    def show_level_select(self, event=None):
        self.mode = "select"
        self.clear_canvas_state()
        self.draw_background()
        self.canvas.create_text(WIDTH / 2, 55, text="LEVEL SELECT", fill=TEXT_COLOR, font=("Consolas", 28, "bold"), tags="ui")
        y = 110
        for i, lvl in enumerate(self.levels):
            self.make_button(180, y, 600, 42, f"{i+1}. {lvl['name']}", lambda idx=i: self.select_level(idx), tags="ui", font=("Consolas", 14, "bold"))
            y += 52
        self.make_button(20, 20, 120, 34, "Back", self.show_menu, tags="ui", font=("Consolas", 12, "bold"))

    def select_level(self, idx):
        self.selected_level_index = idx
        self.start_selected_level()

    def start_selected_level(self, event=None):
        self.reset_game_state()
        self.mode = "game"
        self.clear_canvas_state()
        self.draw_game_static()

    def draw_game_static(self):
        self.canvas.delete("ui")
        self.draw_background()
        self.player = self.canvas.create_polygon(self.player_points(), fill=PLAYER_COLOR, outline=TEXT_COLOR, width=2, tags="game")
        self.score_text = self.canvas.create_text(18, 16, anchor="nw", fill=TEXT_COLOR, font=("Consolas", 14, "bold"), text="Score: 0", tags="ui")
        self.level_text = self.canvas.create_text(18, 38, anchor="nw", fill="#c6d7ff", font=("Consolas", 11), text=f"Level: {self.level['name']}", tags="ui")
        self.msg_text = self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 25, fill=TEXT_COLOR, font=("Consolas", 20, "bold"), text="Press SPACE / click to start", tags="ui")
        self.load_level_objects()
        self.canvas.create_text(WIDTH - 16, 16, anchor="ne", fill="#c6d7ff", font=("Consolas", 11), text="ESC = Menu", tags="ui")

    def load_level_objects(self):
        self.obstacles = []
        for obj in self.level.get("objects", []):
            self.add_obstacle_from_data(obj)

    def add_obstacle_from_data(self, obj):
        t = obj["type"]
        x, y, w, h = obj["x"], obj["y"], obj["w"], obj["h"]
        if t in ("spike", "double_spike"):
            if t == "spike":
                pts = [x, y + h, x + w / 2, y, x + w, y + h]
            else:
                pts = [x, y + h, x + w / 4, y, x + w / 2, y + h, x + 3 * w / 4, y, x + w, y + h]
            item = self.canvas.create_polygon(pts, fill=SPIKE_COLOR, outline=TEXT_COLOR, width=2, tags="game")
        else:
            item = self.canvas.create_rectangle(x, y, x + w, y + h, fill=BLOCK_COLOR, outline=TEXT_COLOR, width=2, tags="game")
        self.obstacles.append({"x": x, "y": y, "w": w, "h": h, "type": t, "id": item})

    # ------------------------------------------------------------------
    # Input dispatch
    # ------------------------------------------------------------------
    def on_left_click(self, event):
        if self.mode in ("menu", "select"):
            self.handle_menu_click(event.x, event.y)
            return
        if self.mode == "editor":
            # IMPORTANT: check UI buttons (tools, save, play, etc.) first.
            # Previously editor clicks skipped this check entirely, so the
            # tool/action buttons were dead and the tool never changed
            # from its default ("spike").
            if self.handle_menu_click(event.x, event.y):
                return
            self.handle_editor_click(event.x, event.y)
            return
        self.on_jump()

    def handle_menu_click(self, x, y):
        for rect, label, command, x1, y1, x2, y2 in self.menu_buttons:
            if x1 <= x <= x2 and y1 <= y <= y2:
                command()
                return True
        return False

    def on_jump(self, event=None):
        if self.mode != "game" or self.game_over:
            return
        if not self.started:
            self.started = True
            self.canvas.itemconfig(self.msg_text, text="")
        if self.on_ground:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False
            self.spawn_jump_particles()

    def spawn_jump_particles(self):
        for _ in range(6):
            px = self.player_x + PLAYER_SIZE / 2
            py = self.player_y + PLAYER_SIZE
            vx = random.uniform(-3, 3)
            vy = random.uniform(-4, -1)
            p = self.canvas.create_oval(px, py, px + 4, py + 4, fill=ACCENT_COLOR, outline="", tags="fx")
            self.particles.append({"id": p, "x": px, "y": py, "vx": vx, "vy": vy, "life": 30})

    # ------------------------------------------------------------------
    # Auto obstacle spawner (time-based spacing, jump-safe heights)
    # ------------------------------------------------------------------
    def spawn_obstacle(self):
        kind = random.choice(["spike", "spike", "block", "double_spike"])
        x = WIDTH + 30
        base_y = GROUND_Y
        if kind == "spike":
            obj = {"type": "spike", "x": x, "y": base_y - 30, "w": 30, "h": 30}
        elif kind == "double_spike":
            obj = {"type": "double_spike", "x": x, "y": base_y - 30, "w": 60, "h": 30}
        else:
            h = random.choice(AUTO_BLOCK_HEIGHTS)
            obj = {"type": "block", "x": x, "y": base_y - h, "w": 30, "h": h}
        self.add_obstacle_from_data(obj)

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

    def update_particles(self):
        keep = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.18
            p["life"] -= 1
            self.canvas.move(p["id"], p["vx"], p["vy"])
            if p["life"] > 0:
                keep.append(p)
            else:
                self.canvas.delete(p["id"])
        self.particles = keep

    def check_collision(self):
        pad = 5
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
        self.canvas.itemconfig(self.msg_text, text=f"Game Over!\nScore: {self.score}\nPress R or ESC")

    def on_restart(self, event=None):
        if self.mode == "game":
            self.start_selected_level()

    # ------------------------------------------------------------------
    # Level editor
    # ------------------------------------------------------------------
    def editor_button(self, x, y, w, h, text, command):
        self.make_button(x, y, w, h, text, command, tags="ui", font=("Consolas", 12, "bold"))

    def open_editor(self, event=None):
        self.mode = "editor"
        self.clear_canvas_state()
        self.draw_background()
        self.editor_level = {"name": "New Level", "speed": 1.0, "objects": []}
        self.editor_tool = "spike"
        self.editor_selected_item = None
        self.editor_camera_x = 0
        self.draw_editor_ui()

    def draw_editor_ui(self):
        self.canvas.delete("ui")
        self.canvas.delete("editor_obj")
        self.canvas.delete("selection")
        self.canvas.delete("editor_grid")
        self.menu_buttons = []

        self.canvas.create_text(20, 16, anchor="nw", text="LEVEL EDITOR", fill=TEXT_COLOR, font=("Consolas", 22, "bold"), tags="ui")
        self.canvas.create_text(20, 48, anchor="nw", text="Click to place / select. Del removes. Right-drag,", fill="#c7d4ff", font=("Consolas", 10), tags="ui")
        self.canvas.create_text(20, 62, anchor="nw", text="arrow keys or scroll wheel to pan the level.", fill="#c7d4ff", font=("Consolas", 10), tags="ui")

        self.canvas.create_rectangle(20, 84, 220, 214, fill=PANEL_COLOR, outline="#34406b", width=2, tags="ui")
        self.canvas.create_text(120, 100, text="TOOLS", fill=ACCENT_COLOR, font=("Consolas", 14, "bold"), tags="ui")
        self.make_button(40, 122, 160, 28, "Spike", lambda: self.set_tool("spike"), tags="ui", font=("Consolas", 11, "bold"))
        self.make_button(40, 154, 160, 28, "Block", lambda: self.set_tool("block"), tags="ui", font=("Consolas", 11, "bold"))
        self.make_button(40, 186, 160, 28, "Double Spike", lambda: self.set_tool("double_spike"), tags="ui", font=("Consolas", 11, "bold"))

        self.editor_button(20, 226, 88, 30, "Play", self.play_editor_level)
        self.editor_button(114, 226, 88, 30, "Save", self.save_editor_level)
        self.editor_button(20, 262, 88, 30, "Clear", self.clear_editor)
        self.editor_button(114, 262, 88, 30, "Back", self.show_menu)
        self.editor_button(20, 298, 88, 30, "< Pan", lambda: self.editor_pan(-EDITOR_PAN_STEP))
        self.editor_button(114, 298, 88, 30, "Pan >", lambda: self.editor_pan(EDITOR_PAN_STEP))
        self.editor_button(20, 334, 182, 30, "Load Level", self.load_level_from_file)

        self.canvas.create_rectangle(EDITOR_VIEW_X0, 60, EDITOR_VIEW_X1, GROUND_Y + 20, fill="#0e1430", outline="#34406b", width=2, tags="ui")
        self.canvas.create_line(EDITOR_VIEW_X0, GROUND_Y, EDITOR_VIEW_X1, GROUND_Y, fill=ACCENT_COLOR, width=2, tags="ui")

        self.editor_tool_text = self.canvas.create_text(WIDTH - 30, 20, anchor="ne", text=f"Tool: {self.editor_tool}", fill=TEXT_COLOR, font=("Consolas", 12, "bold"), tags="ui")
        self.editor_pos_text = self.canvas.create_text(WIDTH - 30, 40, anchor="ne", text="", fill="#9fb0e0", font=("Consolas", 10), tags="ui")

        self.draw_editor_grid()
        self.draw_editor_objects()
        self.update_editor_pos_text()

    def set_tool(self, tool):
        self.editor_tool = tool
        self.canvas.itemconfig(self.editor_tool_text, text=f"Tool: {self.editor_tool}")

    def update_editor_pos_text(self):
        max_cam = max(0, EDITOR_LEVEL_WIDTH - (EDITOR_VIEW_X1 - EDITOR_VIEW_X0))
        self.canvas.itemconfig(self.editor_pos_text, text=f"Camera: {int(self.editor_camera_x)} / {max_cam}")

    def draw_editor_grid(self):
        self.canvas.delete("editor_grid")
        view_w = EDITOR_VIEW_X1 - EDITOR_VIEW_X0
        start = -(self.editor_camera_x % CUBE)
        x = start
        while x < view_w:
            sx = EDITOR_VIEW_X0 + x
            self.canvas.create_line(sx, 60, sx, GROUND_Y, fill="#1c2748", tags=("editor_grid",))
            x += CUBE
        y = GROUND_Y
        while y > 60:
            self.canvas.create_line(EDITOR_VIEW_X0, y, EDITOR_VIEW_X1, y, fill="#1c2748", tags=("editor_grid",))
            y -= CUBE
        self.canvas.tag_lower("editor_grid")
        self.canvas.tag_raise("editor_grid", "ui")
        # keep grid below objects but above the dark panel background
        for item in self.canvas.find_withtag("editor_grid"):
            self.canvas.tag_raise(item)
        self.canvas.tag_lower("editor_grid")
        self.canvas.tag_raise("editor_grid")

    def editor_pan(self, dx):
        if self.mode != "editor":
            return
        view_w = EDITOR_VIEW_X1 - EDITOR_VIEW_X0
        max_cam = max(0, EDITOR_LEVEL_WIDTH - view_w)
        self.editor_camera_x = max(0, min(max_cam, self.editor_camera_x + dx))
        self.draw_editor_grid()
        self.draw_editor_objects()
        self.update_editor_pos_text()

    def editor_pan_start(self, event):
        if self.mode == "editor":
            self._pan_last_x = event.x

    def editor_pan_drag(self, event):
        if self.mode != "editor" or self._pan_last_x is None:
            return
        dx = self._pan_last_x - event.x
        self._pan_last_x = event.x
        self.editor_pan(dx)

    def editor_pan_key(self, event):
        if self.mode != "editor":
            return
        if event.keysym == "Left":
            self.editor_pan(-EDITOR_PAN_STEP)
        elif event.keysym == "Right":
            self.editor_pan(EDITOR_PAN_STEP)

    def editor_pan_wheel(self, event):
        if self.mode != "editor":
            return
        delta = 0
        if hasattr(event, "num") and event.num in (4, 5):
            delta = -EDITOR_PAN_STEP if event.num == 4 else EDITOR_PAN_STEP
        elif getattr(event, "delta", 0):
            delta = -EDITOR_PAN_STEP if event.delta > 0 else EDITOR_PAN_STEP
        if delta:
            self.editor_pan(delta)

    def draw_editor_objects(self):
        self.canvas.delete("editor_obj")
        view_w = EDITOR_VIEW_X1 - EDITOR_VIEW_X0
        for i, obj in enumerate(self.editor_level["objects"]):
            sx = obj["x"] - self.editor_camera_x + EDITOR_VIEW_X0
            # skip objects fully outside the visible viewport
            if sx + obj["w"] < EDITOR_VIEW_X0 or sx > EDITOR_VIEW_X1:
                continue
            x, y, w, h = sx, obj["y"], obj["w"], obj["h"]
            if obj["type"] == "spike":
                pts = [x, y + h, x + w / 2, y, x + w, y + h]
                item = self.canvas.create_polygon(pts, fill=SPIKE_COLOR, outline=TEXT_COLOR, width=2, tags=("editor_obj", f"obj{i}"))
            elif obj["type"] == "double_spike":
                pts = [x, y + h, x + w / 4, y, x + w / 2, y + h, x + 3 * w / 4, y, x + w, y + h]
                item = self.canvas.create_polygon(pts, fill=SPIKE_COLOR, outline=TEXT_COLOR, width=2, tags=("editor_obj", f"obj{i}"))
            else:
                item = self.canvas.create_rectangle(x, y, x + w, y + h, fill=BLOCK_COLOR, outline=TEXT_COLOR, width=2, tags=("editor_obj", f"obj{i}"))
            self.canvas.tag_bind(item, "<Button-1>", lambda e, idx=i: self.select_editor_object(idx))
        if self.editor_selected_item is not None and self.editor_selected_item < len(self.editor_level["objects"]):
            self.draw_selection_box(self.editor_selected_item)

    def draw_selection_box(self, idx):
        self.canvas.delete("selection")
        obj = self.editor_level["objects"][idx]
        sx = obj["x"] - self.editor_camera_x + EDITOR_VIEW_X0
        self.canvas.create_rectangle(sx - 3, obj["y"] - 3, sx + obj["w"] + 3, obj["y"] + obj["h"] + 3,
                                      outline="#ffe066", width=3, tags="selection")

    def handle_editor_click(self, x, y):
        if x < EDITOR_VIEW_X0 or x > EDITOR_VIEW_X1 or y > GROUND_Y or y < 60:
            return
        # Convert screen position -> level-space position, snapped to the
        # cube grid on BOTH axes (previously only X was snapped, and the
        # tool never changed so only spikes ever got placed).
        level_x = x - EDITOR_VIEW_X0 + self.editor_camera_x
        gx = round(level_x / CUBE) * CUBE
        gx = max(0, min(EDITOR_LEVEL_WIDTH - CUBE, gx))

        if self.editor_tool == "spike":
            gy = GROUND_Y - CUBE
            obj = {"type": "spike", "x": gx, "y": gy, "w": CUBE, "h": CUBE}
        elif self.editor_tool == "double_spike":
            obj = {"type": "double_spike", "x": gx, "y": GROUND_Y - CUBE, "w": CUBE * 2, "h": CUBE}
        else:
            # Blocks snap to the cube grid vertically too, so you can stack
            # them cube-by-cube instead of only getting a fixed height.
            gy = round(y / CUBE) * CUBE
            gy = min(gy, GROUND_Y - CUBE)
            h = GROUND_Y - gy
            obj = {"type": "block", "x": gx, "y": gy, "w": CUBE, "h": h}

        self.editor_level["objects"].append(obj)
        self.editor_selected_item = None
        self.draw_editor_objects()

    def select_editor_object(self, idx):
        self.editor_selected_item = idx
        self.draw_selection_box(idx)

    def editor_delete_selected(self, event=None):
        if self.mode != "editor":
            return
        if self.editor_selected_item is not None and 0 <= self.editor_selected_item < len(self.editor_level["objects"]):
            self.editor_level["objects"].pop(self.editor_selected_item)
            self.editor_selected_item = None
            self.canvas.delete("selection")
            self.draw_editor_objects()

    def clear_editor(self):
        self.editor_level["objects"] = []
        self.editor_selected_item = None
        self.draw_editor_objects()

    def save_editor_level(self):
        name = self.prompt_text("Level name", "Custom Level")
        if not name:
            return
        level = {"name": name, "speed": 1.0, "objects": list(self.editor_level["objects"]), "custom": True}
        self.levels.append(level)
        self.save_custom_levels()
        messagebox.showinfo("Saved", f"Saved level '{name}' to {CUSTOM_LEVELS_FILE}")

    def prompt_text(self, title, default=""):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.resizable(False, False)
        win.grab_set()
        tk.Label(win, text=title, font=("Consolas", 12, "bold")).pack(padx=14, pady=(14, 6))
        entry = tk.Entry(win, width=30)
        entry.insert(0, default)
        entry.pack(padx=14, pady=6)
        result = {"value": None}

        def ok():
            result["value"] = entry.get().strip()
            win.destroy()

        tk.Button(win, text="OK", command=ok).pack(pady=(6, 12))
        entry.focus_set()
        win.wait_window()
        return result["value"]

    def load_level_from_file(self):
        path = filedialog.askopenfilename(initialdir=LEVELS_DIR, title="Open level JSON", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                level = json.load(f)
            if "objects" not in level:
                raise ValueError("Invalid level file")
            level["custom"] = True
            self.levels.append(level)
            self.save_custom_levels()
            messagebox.showinfo("Loaded", f"Loaded '{level.get('name', 'Unnamed')}'")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def play_editor_level(self):
        self.levels.append({"name": self.editor_level.get("name", "Editor Level"), "speed": 1.0,
                             "objects": list(self.editor_level["objects"]), "custom": True})
        self.selected_level_index = len(self.levels) - 1
        self.start_selected_level()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def loop(self):
        if self.mode == "game" and not self.game_over:
            if self.started:
                self.vel_y += GRAVITY
                self.player_y += self.vel_y
                if self.player_y >= GROUND_Y - PLAYER_SIZE:
                    self.player_y = GROUND_Y - PLAYER_SIZE
                    self.vel_y = 0
                    self.on_ground = True
                else:
                    self.on_ground = False

                if self.on_ground:
                    self.rotation = 0
                else:
                    self.rotation = (self.rotation + 9) % 360

                self.bg_offset += self.speed
                self.canvas.coords(self.player, *self.player_points())

                # Time-based spawn countdown: reaction time stays constant
                # no matter how fast `speed` has ramped up.
                self.next_spawn_frames -= 1
                if self.next_spawn_frames <= 0:
                    self.spawn_obstacle()
                    self.next_spawn_frames = random.randint(MIN_SPAWN_FRAMES, MAX_SPAWN_FRAMES)

                self.speed = min(BASE_SPEED + (self.score // 25) * 0.25, MAX_SPEED)

                self.update_obstacles()
                self.update_particles()

                self.distance += self.speed
                self.score = int(self.distance // 10)
                self.canvas.itemconfig(self.score_text, text=f"Score: {self.score}")

                if self.check_collision():
                    self.end_game()
            else:
                self.canvas.coords(self.player, *self.player_points())
            if not self.game_over:
                self.draw_background()
                self.canvas.tag_raise("game")
                self.canvas.tag_raise("ui")
                self.canvas.tag_raise(self.player)
                self.canvas.coords(self.player, *self.player_points())
                self.canvas.itemconfig(self.level_text, text=f"Level: {self.level['name']}")
        elif self.mode == "editor":
            self.draw_background()
            self.canvas.tag_raise("ui")
            self.canvas.tag_raise("editor_grid")
            self.canvas.tag_raise("editor_obj")
            self.canvas.tag_raise("selection")
        else:
            self.draw_background()
            self.canvas.tag_raise("ui")

        self.schedule_loop()


if __name__ == "__main__":
    root = tk.Tk()
    GeometryDash(root)
    root.mainloop()
