import json
import math
import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox

WIDTH, HEIGHT = 960, 540
GROUND_Y = HEIGHT - 85
FPS_MS = 1000 // 120

GRAVITY = 0.62
JUMP_VELOCITY = -10.5
TERMINAL_VELOCITY = 15
APEX_THRESHOLD = 2.2
APEX_GRAVITY_SCALE = 0.5

PLAYER_SIZE = 38
PLAYER_START_X = 120
BASE_SPEED = 5.0

JUMP_APEX_HEIGHT = (JUMP_VELOCITY ** 2) / (2 * GRAVITY)

CUBE = 30

FINISH_WIDTH = 26
FINISH_MARGIN = 250

BG_TOP = "#0b1021"
BG_BOTTOM = "#182042"
GROUND_COLOR = "#23263d"
GRID_COLOR = "#202742"
ACCENT_COLOR = "#34d7ff"
PLAYER_COLOR = "#39e6ff"
SPIKE_COLOR = "#ff4d6d"
BLOCK_COLOR = "#8a4dff"
DECOR_COLOR = "#ffd166"
TEXT_COLOR = "#f7fbff"
PANEL_COLOR = "#10162b"
BUTTON_COLOR = "#1a2342"
BUTTON_HOVER = "#26345f"
EDITOR_COLOR = "#16203b"

DEFAULT_FILL = {
    "spike": SPIKE_COLOR,
    "block": BLOCK_COLOR,
    "decor": DECOR_COLOR,
    "teleport1": "#06d6a0",
    "teleport2": "#f72585"
}

FILL_PALETTE = [
    "#8a4dff",
    "#ff4d6d",
    "#34d7ff",
    "#ffd166",
    "#06d6a0",
    "#f72585",
    "#ffffff",
    "#495371"
]

OUTLINE_PALETTE = [
    "#f7fbff",
    "#000000",
    "#34d7ff",
    "#ff4d6d",
    "#06d6a0"
]

BG_PRESETS = [
    ("#0b1021", "#182042"),
    ("#1a0b21", "#3a1550"),
    ("#0b211a", "#144d34"),
    ("#211a0b", "#4d3414"),
    ("#0b1621", "#0f3a63"),
    ("#210b1a", "#4d1440"),
]

LEVELS_DIR = "levels"
CUSTOM_LEVELS_FILE = os.path.join(LEVELS_DIR, "custom_levels.json")

EDITOR_VIEW_X0 = 240
EDITOR_VIEW_X1 = WIDTH - 20

EDITOR_VIEW_Y0 = 60
EDITOR_VIEW_Y1 = GROUND_Y

EDITOR_LEVEL_WIDTH = 4000
EDITOR_LEVEL_HEIGHT = 2500

EDITOR_PAN_STEP = 150
EDITOR_ZOOM = 1.6

SPAWN_ZONE_WIDTH = 180
SPAWN_ZONE_HEIGHT = 150


class GeometryDash:
    def __init__(self, root):
        self.root = root
        self.root.title("Geometry Dash - Tkinter Edition")
        self.root.resizable(False, False)

        os.makedirs(LEVELS_DIR, exist_ok=True)

        self.canvas = tk.Canvas(
            root,
            width=WIDTH,
            height=HEIGHT,
            bg=BG_TOP,
            highlightthickness=0
        )
        self.canvas.pack()

        self.root.bind("<space>", self.on_jump)
        self.root.bind("<Up>", self.on_jump)
        self.root.bind("<Button-1>", self.on_left_click)
        self.root.bind("<r>", self.on_restart)
        self.root.bind("<R>", self.on_restart)
        self.root.bind("<Escape>", self.show_menu)
        self.root.bind("<Delete>", self.editor_delete_selected)

        self.canvas.bind("<ButtonPress-3>", self.editor_pan_start)
        self.canvas.bind("<B3-Motion>", self.editor_pan_drag)
        self.canvas.bind("<ButtonRelease-3>", self.editor_pan_end)

        self.root.bind("<Left>", self.editor_pan_key)
        self.root.bind("<Right>", self.editor_pan_key)
        self.root.bind("<Up>", self.editor_vertical_key, add="+")
        self.root.bind("<Down>", self.editor_vertical_key, add="+")

        self.canvas.bind("<MouseWheel>", self.editor_pan_wheel)
        self.canvas.bind("<Button-4>", self.editor_pan_wheel)
        self.canvas.bind("<Button-5>", self.editor_pan_wheel)

        self.canvas.bind("<B1-Motion>", self.editor_move_drag)
        self.canvas.bind("<ButtonRelease-1>", self.editor_move_release)

        self.levels = self.load_builtin_levels()
        self.custom_levels = self.load_custom_levels()
        self.levels.extend(self.custom_levels)

        self.selected_level_index = 0
        self.mode = "menu"
        self.after_id = None
        self.menu_buttons = []
        self.preview_running = False

        self.editor_tool = "place"
        self.editor_block = "spike"
        self.editor_fill_color = None
        self.editor_outline_color = None
        self.editor_bg_index = 0

        self.editor_level = {
            "name": "New Level",
            "speed": 1.0,
            "objects": [],
            "bg_top": BG_PRESETS[0][0],
            "bg_bottom": BG_PRESETS[0][1]
        }

        self.editor_selected_item = None
        self.editor_camera_x = 0
        self.editor_camera_y = 0

        self._pan_last_x = None
        self._pan_last_y = None

        self.editor_move_index = None
        self.editor_move_offset_x = 0
        self.editor_move_offset_y = 0

        self.bg_top = BG_TOP
        self.bg_bottom = BG_BOTTOM

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
    # LEVEL DATA
    # ------------------------------------------------------------------

    def load_builtin_levels(self):
        return [
            {
                "name": "Starter",
                "speed": 1.0,
                "objects": [
                    {
                        "type": "spike",
                        "x": 520,
                        "y": GROUND_Y - 30,
                        "w": 30,
                        "h": 30
                    },
                    {
                        "type": "spike",
                        "x": 650,
                        "y": GROUND_Y - 30,
                        "w": 30,
                        "h": 30
                    },
                    {
                        "type": "block",
                        "x": 800,
                        "y": GROUND_Y - 60,
                        "w": 30,
                        "h": 60
                    }
                ]
            },
            {
                "name": "Rhythm",
                "speed": 1.05,
                "objects": [
                    {
                        "type": "spike",
                        "x": 480,
                        "y": GROUND_Y - 30,
                        "w": 30,
                        "h": 30
                    },
                    {
                        "type": "spike",
                        "x": 640,
                        "y": GROUND_Y - 30,
                        "w": 30,
                        "h": 30
                    },
                    {
                        "type": "spike",
                        "x": 675,
                        "y": GROUND_Y - 30,
                        "w": 30,
                        "h": 30
                    },
                    {
                        "type": "block",
                        "x": 820,
                        "y": GROUND_Y - 60,
                        "w": 30,
                        "h": 60
                    },
                    {
                        "type": "spike",
                        "x": 950,
                        "y": GROUND_Y - 30,
                        "w": 30,
                        "h": 30
                    }
                ]
            }
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
        custom = [
            lvl for lvl in self.levels
            if lvl.get("custom")
        ]

        with open(CUSTOM_LEVELS_FILE, "w", encoding="utf-8") as f:
            json.dump(custom, f, indent=2)

    # ------------------------------------------------------------------
    # GENERAL
    # ------------------------------------------------------------------

    def clear_canvas_state(self):
        self.canvas.delete("all")
        self.menu_buttons = []
        self.editor_selected_item = None

    def reset_game_state(self):
        self.player_x = PLAYER_START_X
        self.player_y = GROUND_Y - PLAYER_SIZE
        self.vel_y = 0
        self.on_ground = True
        self.rotation = 0

        self.obstacles = []
        self.particles = []

        self.level = self.levels[self.selected_level_index]

        self.speed = BASE_SPEED * self.level.get("speed", 1.0)

        self.bg_top = self.level.get("bg_top", BG_TOP)
        self.bg_bottom = self.level.get("bg_bottom", BG_BOTTOM)

        self.score = 0
        self.distance = 0

        self.game_over = False
        self.won = False
        self.started = False

        self.bg_offset = 0

        self.teleport_cooldown = 0

        self.clouds = self.make_clouds()
        self.stars = self.make_stars()

    def make_stars(self):
        return [
            {
                "x": random.randint(0, WIDTH),
                "y": random.randint(20, GROUND_Y - 160),
                "r": random.randint(1, 2),
                "s": random.uniform(0.2, 0.8)
            }
            for _ in range(60)
        ]

    def make_clouds(self):
        return [
            {
                "x": random.randint(0, WIDTH),
                "y": random.randint(30, 180),
                "w": random.randint(60, 130),
                "h": random.randint(18, 38),
                "s": random.uniform(0.2, 0.5)
            }
            for _ in range(7)
        ]

    def blend(self, a, b, t):
        a = a.lstrip("#")
        b = b.lstrip("#")

        ar = int(a[0:2], 16)
        ag = int(a[2:4], 16)
        ab = int(a[4:6], 16)

        br = int(b[0:2], 16)
        bg = int(b[2:4], 16)
        bb = int(b[4:6], 16)

        r = int(ar + (br - ar) * t)
        g = int(ag + (bg - ag) * t)
        bl = int(ab + (bb - ab) * t)

        return f"#{r:02x}{g:02x}{bl:02x}"

    def draw_background(self):
        self.canvas.delete("bg")

        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            c = self.blend(self.bg_top, self.bg_bottom, t)

            self.canvas.create_rectangle(
                0,
                y,
                WIDTH,
                y + 4,
                outline="",
                fill=c,
                tags="bg"
            )

        for star in self.stars:
            star["x"] -= star["s"]

            if star["x"] < 0:
                star["x"] = WIDTH
                star["y"] = random.randint(20, GROUND_Y - 160)

            self.canvas.create_oval(
                star["x"],
                star["y"],
                star["x"] + star["r"],
                star["y"] + star["r"],
                fill="#ffffff",
                outline="",
                tags="bg"
            )

        for cloud in self.clouds:
            cloud["x"] -= cloud["s"]

            if cloud["x"] + cloud["w"] < 0:
                cloud["x"] = WIDTH + random.randint(20, 120)
                cloud["y"] = random.randint(30, 180)

            x = cloud["x"]
            y = cloud["y"]
            w = cloud["w"]
            h = cloud["h"]

            self.canvas.create_oval(
                x,
                y,
                x + w * 0.55,
                y + h,
                fill="#2a355f",
                outline="",
                tags="bg"
            )

            self.canvas.create_oval(
                x + w * 0.22,
                y - h * 0.3,
                x + w * 0.72,
                y + h * 1.05,
                fill="#2f3a67",
                outline="",
                tags="bg"
            )

            self.canvas.create_oval(
                x + w * 0.46,
                y,
                x + w,
                y + h,
                fill="#2a355f",
                outline="",
                tags="bg"
            )

        self.canvas.create_rectangle(
            0,
            GROUND_Y,
            WIDTH,
            HEIGHT,
            fill=GROUND_COLOR,
            outline="",
            tags="bg"
        )

        self.canvas.create_line(
            0,
            GROUND_Y,
            WIDTH,
            GROUND_Y,
            fill=ACCENT_COLOR,
            width=3,
            tags="bg"
        )

        for x in range(-int(self.bg_offset) % 40, WIDTH, 40):
            self.canvas.create_line(
                x,
                0,
                x,
                GROUND_Y,
                fill=GRID_COLOR,
                tags="bg"
            )

        self.canvas.create_rectangle(
            0,
            0,
            WIDTH,
            HEIGHT,
            outline="#2c3764",
            width=2,
            tags="bg"
        )

    # ------------------------------------------------------------------
    # PLAYER
    # ------------------------------------------------------------------

    def player_points(self):
        cx = self.player_x + PLAYER_SIZE / 2
        cy = self.player_y + PLAYER_SIZE / 2

        stretch = 1.0
        squish = 1.0

        if not self.on_ground:
            t = max(-1.0, min(1.0, self.vel_y / 12.0))
            stretch = 1.0 + 0.14 * abs(t)
            squish = 1.0 - 0.10 * abs(t)

        half_w = (PLAYER_SIZE / 2) * squish
        half_h = (PLAYER_SIZE / 2) * stretch

        corners = [
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h)
        ]

        rad = math.radians(self.rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        pts = []

        for dx, dy in corners:
            rx = dx * cos_r - dy * sin_r
            ry = dx * sin_r + dy * cos_r

            pts.extend([
                cx + rx,
                cy + ry
            ])

        return pts

    # ------------------------------------------------------------------
    # BUTTONS
    # ------------------------------------------------------------------

    def make_button(
        self,
        x,
        y,
        w,
        h,
        text,
        command,
        tags="ui",
        font=("Consolas", 16, "bold")
    ):
        rect = self.canvas.create_rectangle(
            x,
            y,
            x + w,
            y + h,
            fill=BUTTON_COLOR,
            outline="#3d4b7a",
            width=2,
            tags=(tags, "button")
        )

        label = self.canvas.create_text(
            x + w / 2,
            y + h / 2,
            text=text,
            fill=TEXT_COLOR,
            font=font,
            tags=(tags, "button")
        )

        def on_enter(event, r=rect):
            self.canvas.itemconfig(
                r,
                fill=BUTTON_HOVER,
                outline=ACCENT_COLOR
            )

        def on_leave(event, r=rect):
            self.canvas.itemconfig(
                r,
                fill=BUTTON_COLOR,
                outline="#3d4b7a"
            )

        self.canvas.tag_bind(rect, "<Enter>", on_enter)
        self.canvas.tag_bind(rect, "<Leave>", on_leave)

        self.canvas.tag_bind(label, "<Enter>", on_enter)
        self.canvas.tag_bind(label, "<Leave>", on_leave)

        self.menu_buttons.append(
            (
                rect,
                label,
                command,
                x,
                y,
                x + w,
                y + h
            )
        )

        return rect, label

    # ------------------------------------------------------------------
    # MENU
    # ------------------------------------------------------------------

    def show_menu(self, event=None):
        self.mode = "menu"

        self.clear_canvas_state()
        self.reset_game_state()

        self.bg_top = BG_TOP
        self.bg_bottom = BG_BOTTOM

        self.draw_background()

        self.canvas.create_text(
            WIDTH / 2,
            95,
            text="GEOMETRY DASH",
            fill=TEXT_COLOR,
            font=("Consolas", 32, "bold"),
            tags="ui"
        )

        self.canvas.create_text(
            WIDTH / 2,
            132,
            text="Tkinter Edition",
            fill=ACCENT_COLOR,
            font=("Consolas", 14, "bold"),
            tags="ui"
        )

        self.make_button(
            WIDTH / 2 - 130,
            200,
            260,
            48,
            "Start Game",
            self.start_selected_level
        )

        self.make_button(
            WIDTH / 2 - 130,
            260,
            260,
            48,
            "Level Select",
            self.show_level_select
        )

        self.make_button(
            WIDTH / 2 - 130,
            320,
            260,
            48,
            "Level Editor",
            self.open_editor
        )

        self.make_button(
            WIDTH / 2 - 130,
            380,
            260,
            48,
            "Quit",
            self.root.destroy
        )

        self.canvas.create_text(
            WIDTH / 2,
            485,
            text="SPACE / CLICK = Jump    ESC = Menu",
            fill="#c7d4ff",
            font=("Consolas", 11),
            tags="ui"
        )

    def show_level_select(self, event=None):
        self.mode = "select"

        self.clear_canvas_state()
        self.draw_background()

        self.canvas.create_text(
            WIDTH / 2,
            55,
            text="LEVEL SELECT",
            fill=TEXT_COLOR,
            font=("Consolas", 28, "bold"),
            tags="ui"
        )

        y = 110

        for i, lvl in enumerate(self.levels):
            self.make_button(
                180,
                y,
                600,
                42,
                f"{i + 1}. {lvl['name']}",
                lambda idx=i: self.select_level(idx),
                tags="ui",
                font=("Consolas", 14, "bold")
            )

            y += 52

        self.make_button(
            20,
            20,
            120,
            34,
            "Back",
            self.show_menu,
            tags="ui",
            font=("Consolas", 12, "bold")
        )

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

        self.player = self.canvas.create_polygon(
            self.player_points(),
            fill=PLAYER_COLOR,
            outline=TEXT_COLOR,
            width=2,
            tags="game"
        )

        self.score_text = self.canvas.create_text(
            18,
            16,
            anchor="nw",
            fill=TEXT_COLOR,
            font=("Consolas", 14, "bold"),
            text="Score: 0",
            tags="ui"
        )

        self.level_text = self.canvas.create_text(
            18,
            38,
            anchor="nw",
            fill="#c6d7ff",
            font=("Consolas", 11),
            text=f"Level: {self.level['name']}",
            tags="ui"
        )

        self.msg_text = self.canvas.create_text(
            WIDTH / 2,
            HEIGHT / 2 - 25,
            fill=TEXT_COLOR,
            font=("Consolas", 20, "bold"),
            text="Press SPACE / click to start",
            tags="ui"
        )

        self.load_level_objects()

        self.canvas.create_text(
            WIDTH - 16,
            16,
            anchor="ne",
            fill="#c6d7ff",
            font=("Consolas", 11),
            text="ESC = Menu",
            tags="ui"
        )

    # ------------------------------------------------------------------
    # GAME OBJECTS
    # ------------------------------------------------------------------

    def load_level_objects(self):
        self.obstacles = []

        for obj in self.level.get("objects", []):
            self.add_obstacle_from_data(obj)

        self.add_finish_wall()

    def add_finish_wall(self):
        objs = [
            o for o in self.level.get("objects", [])
            if o["type"] not in ("teleport1", "teleport2")
        ]

        if objs:
            end_x = max(
                o["x"] + o["w"]
                for o in objs
            ) + FINISH_MARGIN
        else:
            end_x = 900

        finish = {
            "type": "finish",
            "x": end_x,
            "y": 8,
            "w": FINISH_WIDTH,
            "h": GROUND_Y - 8
        }

        self.add_obstacle_from_data(finish)

        self.level_end_x = end_x

    def add_obstacle_from_data(self, obj):
        t = obj["type"]

        x = obj["x"]
        y = obj["y"]
        w = obj["w"]
        h = obj["h"]

        fill = obj.get("fill") or DEFAULT_FILL.get(
            t,
            BLOCK_COLOR
        )

        outline = obj.get("outline") or TEXT_COLOR

        if t == "spike":
            pts = [
                x,
                y + h,
                x + w / 2,
                y,
                x + w,
                y + h
            ]

            item = self.canvas.create_polygon(
                pts,
                fill=fill,
                outline=outline,
                width=2,
                tags="game"
            )

        elif t == "decor":
            pts = [
                x + w / 2,
                y,
                x + w,
                y + h / 2,
                x + w / 2,
                y + h,
                x,
                y + h / 2
            ]

            item = self.canvas.create_polygon(
                pts,
                fill=fill,
                outline=outline,
                width=2,
                tags="game"
            )

        elif t in ("teleport1", "teleport2"):
            item = self.canvas.create_rectangle(
                x,
                y,
                x + w,
                y + h,
                fill=fill,
                outline=outline,
                width=3,
                tags="game"
            )

            self.canvas.create_text(
                x + w / 2,
                y + h / 2,
                text="1" if t == "teleport1" else "2",
                fill=TEXT_COLOR,
                font=("Consolas", 12, "bold"),
                tags="game"
            )

        elif t == "finish":
            item = self.canvas.create_rectangle(
                x,
                y,
                x + w,
                y + h,
                fill=GROUND_COLOR,
                outline=ACCENT_COLOR,
                width=4,
                tags="game"
            )

        else:
            item = self.canvas.create_rectangle(
                x,
                y,
                x + w,
                y + h,
                fill=fill,
                outline=outline,
                width=2,
                tags="game"
            )

        self.obstacles.append(
            {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "type": t,
                "id": item
            }
        )

    # ------------------------------------------------------------------
    # INPUT
    # ------------------------------------------------------------------

    def on_left_click(self, event):
        if self.mode in ("menu", "select"):
            self.handle_menu_click(event.x, event.y)
            return

        if self.mode == "editor":
            if self.handle_menu_click(event.x, event.y):
                return

            if event.x >= EDITOR_VIEW_X0:
                self.handle_editor_click(event.x, event.y)

            return

        self.on_jump()

    def handle_menu_click(self, x, y):
        for (
            rect,
            label,
            command,
            x1,
            y1,
            x2,
            y2
        ) in self.menu_buttons:

            if x1 <= x <= x2 and y1 <= y <= y2:
                command()
                return True

        return False

    def on_jump(self, event=None):
        if self.mode != "game" or self.game_over:
            return

        if not self.started:
            self.started = True
            self.canvas.itemconfig(
                self.msg_text,
                text=""
            )

        if self.on_ground:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False
            self.spawn_jump_particles()

    # ------------------------------------------------------------------
    # PARTICLES
    # ------------------------------------------------------------------

    def spawn_jump_particles(self):
        for _ in range(6):
            px = self.player_x + PLAYER_SIZE / 2
            py = self.player_y + PLAYER_SIZE

            vx = random.uniform(-3, 3)
            vy = random.uniform(-4, -1)

            p = self.canvas.create_oval(
                px,
                py,
                px + 4,
                py + 4,
                fill=ACCENT_COLOR,
                outline="",
                tags="fx"
            )

            self.particles.append(
                {
                    "id": p,
                    "x": px,
                    "y": py,
                    "vx": vx,
                    "vy": vy,
                    "life": 30
                }
            )

    def update_particles(self):
        keep = []

        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]

            p["vy"] += 0.18
            p["life"] -= 1

            self.canvas.move(
                p["id"],
                p["vx"],
                p["vy"]
            )

            if p["life"] > 0:
                keep.append(p)
            else:
                self.canvas.delete(p["id"])

        self.particles = keep

    # ------------------------------------------------------------------
    # GAME PHYSICS
    # ------------------------------------------------------------------

    def update_obstacles(self):
        remove = []

        for obs in self.obstacles:
            obs["x"] -= self.speed

            self.canvas.move(
                obs["id"],
                -self.speed,
                0
            )

            if obs["x"] + obs["w"] < 0:
                remove.append(obs)

        for obs in remove:
            self.canvas.delete(obs["id"])

            self.obstacles.remove(obs)

    def resolve_block_landing(self, prev_bottom, new_bottom):
        landed = False

        px1 = self.player_x + 5
        px2 = self.player_x + PLAYER_SIZE - 5

        for obs in self.obstacles:
            if obs["type"] != "block":
                continue

            ox1 = obs["x"]
            ox2 = obs["x"] + obs["w"]
            oy1 = obs["y"]

            if px2 > ox1 and px1 < ox2:
                if (
                    self.vel_y >= 0
                    and prev_bottom <= oy1 + 1
                    and new_bottom >= oy1
                ):
                    self.player_y = oy1 - PLAYER_SIZE
                    self.vel_y = 0
                    landed = True

        return landed

    def check_teleports(self):
        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= 1
            return False

        px1 = self.player_x + 5
        py1 = self.player_y + 5
        px2 = self.player_x + PLAYER_SIZE - 5
        py2 = self.player_y + PLAYER_SIZE - 5

        tp1 = None
        tp2 = None

        for obs in self.obstacles:
            if obs["type"] == "teleport1":
                tp1 = obs

            elif obs["type"] == "teleport2":
                tp2 = obs

        if tp1 is None or tp2 is None:
            return False

        ox1 = tp1["x"]
        oy1 = tp1["y"]
        ox2 = ox1 + tp1["w"]
        oy2 = oy1 + tp1["h"]

        if (
            px1 < ox2
            and px2 > ox1
            and py1 < oy2
            and py2 > oy1
        ):
            self.player_x = (
                tp2["x"] + tp2["w"] / 2 - PLAYER_SIZE / 2
            )

            self.player_y = (
                tp2["y"] + tp2["h"] / 2 - PLAYER_SIZE / 2
            )

            self.teleport_cooldown = 30

            return True

        return False

    def check_collision(self):
        pad = 5

        px1 = self.player_x + pad
        py1 = self.player_y + pad
        px2 = self.player_x + PLAYER_SIZE - pad
        py2 = self.player_y + PLAYER_SIZE - pad

        for obs in self.obstacles:
            if obs["type"] in (
                "decor",
                "teleport1",
                "teleport2"
            ):
                continue

            ox1 = obs["x"]
            oy1 = obs["y"]

            ox2 = obs["x"] + obs["w"]
            oy2 = obs["y"] + obs["h"]

            if (
                px1 < ox2
                and px2 > ox1
                and py1 < oy2
                and py2 > oy1
            ):
                if obs["type"] == "finish":
                    return "finish"

                if obs["type"] == "block":
                    if (
                        self.on_ground
                        and abs(
                            (self.player_y + PLAYER_SIZE) - oy1
                        ) <= 2
                    ):
                        continue

                    return "death"

                return "death"

        return None

    def end_game(self, win=False):
        self.game_over = True
        self.won = win

        if win:
            self.canvas.itemconfig(
                self.msg_text,
                text=(
                    f"Level Complete!\n"
                    f"Score: {self.score}\n"
                    f"Press R or ESC"
                )
            )
        else:
            self.canvas.itemconfig(
                self.msg_text,
                text=(
                    f"Game Over!\n"
                    f"Score: {self.score}\n"
                    f"Press R or ESC"
                )
            )

    def on_restart(self, event=None):
        if self.mode == "game":
            self.start_selected_level()

    # ------------------------------------------------------------------
    # EDITOR COORDINATES
    # ------------------------------------------------------------------

    def editor_screen_x(self, level_x):
        return (
            EDITOR_VIEW_X0
            + (level_x - self.editor_camera_x) * EDITOR_ZOOM
        )

    def editor_screen_y(self, level_y):
        return (
            EDITOR_VIEW_Y0
            + (level_y - self.editor_camera_y) * EDITOR_ZOOM
        )

    def editor_level_x(self, screen_x):
        return (
            (screen_x - EDITOR_VIEW_X0)
            / EDITOR_ZOOM
            + self.editor_camera_x
        )

    def editor_level_y(self, screen_y):
        return (
            (screen_y - EDITOR_VIEW_Y0)
            / EDITOR_ZOOM
            + self.editor_camera_y
        )

    # ------------------------------------------------------------------
    # EDITOR UI
    # ------------------------------------------------------------------

    def editor_button(self, x, y, w, h, text, command):
        self.make_button(
            x,
            y,
            w,
            h,
            text,
            command,
            tags="ui",
            font=("Consolas", 11, "bold")
        )

    def open_editor(self, event=None):
        self.mode = "editor"

        self.clear_canvas_state()

        self.editor_level = {
            "name": "New Level",
            "speed": 1.0,
            "objects": [],
            "bg_top": BG_PRESETS[0][0],
            "bg_bottom": BG_PRESETS[0][1]
        }

        self.editor_tool = "place"
        self.editor_block = "spike"

        self.editor_fill_color = None
        self.editor_outline_color = None
        self.editor_bg_index = 0

        self.editor_selected_item = None

        self.editor_camera_x = 0
        self.editor_camera_y = 0

        self.editor_move_index = None

        self.bg_top, self.bg_bottom = BG_PRESETS[0]

        self.draw_background()
        self.draw_editor_ui()

    def draw_editor_ui(self):
        self.canvas.delete("ui")
        self.canvas.delete("editor_obj")
        self.canvas.delete("selection")
        self.canvas.delete("editor_grid")
        self.canvas.delete("spawn_marker")

        self.menu_buttons = []

        self.canvas.create_text(
            20,
            12,
            anchor="nw",
            text="LEVEL EDITOR",
            fill=TEXT_COLOR,
            font=("Consolas", 18, "bold"),
            tags="ui"
        )

        self.canvas.create_text(
            20,
            38,
            anchor="nw",
            text="Place: click | Move: drag | Delete: click",
            fill="#c7d4ff",
            font=("Consolas", 9),
            tags="ui"
        )

        self.canvas.create_text(
            20,
            50,
            anchor="nw",
            text="Right-drag / arrows / wheel = camera",
            fill="#c7d4ff",
            font=("Consolas", 9),
            tags="ui"
        )

        # TOOLS
        self.canvas.create_rectangle(
            20,
            68,
            220,
            208,
            fill=PANEL_COLOR,
            outline="#34406b",
            width=2,
            tags="ui"
        )

        self.canvas.create_text(
            120,
            82,
            text="TOOLS",
            fill=ACCENT_COLOR,
            font=("Consolas", 12, "bold"),
            tags="ui"
        )

        self.make_button(
            40,
            100,
            160,
            26,
            "Place",
            lambda: self.set_tool("place"),
            tags="ui",
            font=("Consolas", 10, "bold")
        )

        self.make_button(
            40,
            132,
            160,
            26,
            "Move",
            lambda: self.set_tool("move"),
            tags="ui",
            font=("Consolas", 10, "bold")
        )

        self.make_button(
            40,
            164,
            160,
            26,
            "Delete",
            lambda: self.set_tool("delete"),
            tags="ui",
            font=("Consolas", 10, "bold")
        )

        # BLOCKS
        self.canvas.create_rectangle(
            20,
            218,
            220,
            400,
            fill=PANEL_COLOR,
            outline="#34406b",
            width=2,
            tags="ui"
        )

        self.canvas.create_text(
            120,
            232,
            text="BLOCKS",
            fill=ACCENT_COLOR,
            font=("Consolas", 12, "bold"),
            tags="ui"
        )

        blocks = [
            ("Cube", "block"),
            ("Spike", "spike"),
            ("Decor", "decor"),
            ("Teleport 1", "teleport1"),
            ("Teleport 2", "teleport2")
        ]

        y = 252

        for text, block_type in blocks:
            self.make_button(
                40,
                y,
                160,
                26,
                text,
                lambda t=block_type: self.set_block(t),
                tags="ui",
                font=("Consolas", 10, "bold")
            )

            y += 29

        # COLORS
        self.canvas.create_text(
            24,
            416,
            anchor="nw",
            text="Fill",
            fill=ACCENT_COLOR,
            font=("Consolas", 10, "bold"),
            tags="ui"
        )

        self.draw_color_swatches(
            FILL_PALETTE,
            432,
            self.set_fill_color
        )

        self.canvas.create_text(
            24,
            456,
            anchor="nw",
            text="Outline",
            fill=ACCENT_COLOR,
            font=("Consolas", 10, "bold"),
            tags="ui"
        )

        self.draw_color_swatches(
            OUTLINE_PALETTE,
            472,
            self.set_outline_color
        )

        # BOTTOM CONTROLS
        self.editor_button(
            660,
            500,
            90,
            28,
            "Play",
            self.play_editor_level
        )

        self.editor_button(
            758,
            500,
            90,
            28,
            "Save",
            self.save_editor_level
        )

        self.editor_button(
            856,
            500,
            80,
            28,
            "Back",
            self.show_menu
        )

        self.canvas.create_rectangle(
            EDITOR_VIEW_X0,
            EDITOR_VIEW_Y0,
            EDITOR_VIEW_X1,
            EDITOR_VIEW_Y1,
            fill="#0e1430",
            outline="#34406b",
            width=2,
            tags="ui"
        )

        self.canvas.create_line(
            EDITOR_VIEW_X0,
            self.editor_screen_y(GROUND_Y),
            EDITOR_VIEW_X1,
            self.editor_screen_y(GROUND_Y),
            fill=ACCENT_COLOR,
            width=2,
            tags="ui"
        )

        self.editor_tool_text = self.canvas.create_text(
            WIDTH - 30,
            16,
            anchor="ne",
            text=f"Tool: {self.editor_tool}",
            fill=TEXT_COLOR,
            font=("Consolas", 12, "bold"),
            tags="ui"
        )

        self.editor_block_text = self.canvas.create_text(
            WIDTH - 30,
            36,
            anchor="ne",
            text=f"Block: {self.editor_block}",
            fill="#9fb0e0",
            font=("Consolas", 10),
            tags="ui"
        )

        self.editor_pos_text = self.canvas.create_text(
            WIDTH - 30,
            52,
            anchor="ne",
            text="",
            fill="#9fb0e0",
            font=("Consolas", 9),
            tags="ui"
        )

        self.draw_editor_grid()
        self.draw_editor_objects()
        self.draw_editor_spawn_marker()
        self.update_editor_pos_text()

    def draw_color_swatches(self, palette, y, callback):
        sx = 40

        for color in palette:
            rect = self.canvas.create_rectangle(
                sx,
                y,
                sx + 16,
                y + 16,
                fill=color,
                outline="#9fb0e0",
                width=1,
                tags="ui"
            )

            self.canvas.tag_bind(
                rect,
                "<Button-1>",
                lambda e, c=color: callback(c)
            )

            sx += 20

    def set_tool(self, tool):
        self.editor_tool = tool

        if hasattr(self, "editor_tool_text"):
            self.canvas.itemconfig(
                self.editor_tool_text,
                text=f"Tool: {self.editor_tool}"
            )

        self.editor_move_index = None

    def set_block(self, block):
        self.editor_block = block

        if hasattr(self, "editor_block_text"):
            self.canvas.itemconfig(
                self.editor_block_text,
                text=f"Block: {self.editor_block}"
            )

    def set_fill_color(self, color):
        self.editor_fill_color = color

        if (
            self.editor_selected_item is not None
            and 0 <= self.editor_selected_item
            < len(self.editor_level["objects"])
        ):
            self.editor_level["objects"][
                self.editor_selected_item
            ]["fill"] = color

        self.draw_editor_objects()

    def set_outline_color(self, color):
        self.editor_outline_color = color

        if (
            self.editor_selected_item is not None
            and 0 <= self.editor_selected_item
            < len(self.editor_level["objects"])
        ):
            self.editor_level["objects"][
                self.editor_selected_item
            ]["outline"] = color

        self.draw_editor_objects()

    def cycle_bg_color(self):
        self.editor_bg_index = (
            self.editor_bg_index + 1
        ) % len(BG_PRESETS)

        top, bottom = BG_PRESETS[self.editor_bg_index]

        self.editor_level["bg_top"] = top
        self.editor_level["bg_bottom"] = bottom

        self.bg_top = top
        self.bg_bottom = bottom

        self.draw_background()
        self.draw_editor_grid()
        self.draw_editor_objects()
        self.draw_editor_spawn_marker()

    # ------------------------------------------------------------------
    # EDITOR CAMERA
    # ------------------------------------------------------------------

    def get_editor_max_camera(self):
        view_w_level = (
            EDITOR_VIEW_X1 - EDITOR_VIEW_X0
        ) / EDITOR_ZOOM

        view_h_level = (
            EDITOR_VIEW_Y1 - EDITOR_VIEW_Y0
        ) / EDITOR_ZOOM

        max_x = max(
            0,
            EDITOR_LEVEL_WIDTH - view_w_level
        )

        max_y = max(
            0,
            EDITOR_LEVEL_HEIGHT - view_h_level
        )

        return max_x, max_y

    def update_editor_pos_text(self):
        max_x, max_y = self.get_editor_max_camera()

        if hasattr(self, "editor_pos_text"):
            self.canvas.itemconfig(
                self.editor_pos_text,
                text=(
                    f"X: {int(self.editor_camera_x)} / {int(max_x)}   "
                    f"Y: {int(self.editor_camera_y)} / {int(max_y)}"
                )
            )

    def draw_editor_grid(self):
        self.canvas.delete("editor_grid")

        view_w_level = (
            EDITOR_VIEW_X1 - EDITOR_VIEW_X0
        ) / EDITOR_ZOOM

        view_h_level = (
            EDITOR_VIEW_Y1 - EDITOR_VIEW_Y0
        ) / EDITOR_ZOOM

        first_x = (
            math.floor(self.editor_camera_x / CUBE)
            * CUBE
        )

        last_x = (
            self.editor_camera_x
            + view_w_level
            + CUBE
        )

        x = first_x

        while x <= last_x:
            sx = self.editor_screen_x(x)

            if (
                EDITOR_VIEW_X0 <= sx <= EDITOR_VIEW_X1
            ):
                self.canvas.create_line(
                    sx,
                    EDITOR_VIEW_Y0,
                    sx,
                    EDITOR_VIEW_Y1,
                    fill="#1c2748",
                    tags="editor_grid"
                )

            x += CUBE

        first_y = (
            math.floor(self.editor_camera_y / CUBE)
            * CUBE
        )

        last_y = (
            self.editor_camera_y
            + view_h_level
            + CUBE
        )

        y = first_y

        while y <= last_y:
            sy = self.editor_screen_y(y)

            if (
                EDITOR_VIEW_Y0 <= sy <= EDITOR_VIEW_Y1
            ):
                self.canvas.create_line(
                    EDITOR_VIEW_X0,
                    sy,
                    EDITOR_VIEW_X1,
                    sy,
                    fill="#1c2748",
                    tags="editor_grid"
                )

            y += CUBE

        self.canvas.tag_lower("editor_grid")

    def editor_pan(self, dx=0, dy=0):
        if self.mode != "editor":
            return

        max_x, max_y = self.get_editor_max_camera()

        self.editor_camera_x = max(
            0,
            min(
                max_x,
                self.editor_camera_x + dx
            )
        )

        self.editor_camera_y = max(
            0,
            min(
                max_y,
                self.editor_camera_y + dy
            )
        )

        self.draw_editor_grid()
        self.draw_editor_objects()
        self.draw_editor_spawn_marker()
        self.update_editor_pos_text()

    def editor_pan_start(self, event):
        if self.mode != "editor":
            return

        self._pan_last_x = event.x
        self._pan_last_y = event.y

    def editor_pan_drag(self, event):
        if (
            self.mode != "editor"
            or self._pan_last_x is None
            or self._pan_last_y is None
        ):
            return

        dx = (
            self._pan_last_x - event.x
        ) / EDITOR_ZOOM

        dy = (
            self._pan_last_y - event.y
        ) / EDITOR_ZOOM

        self._pan_last_x = event.x
        self._pan_last_y = event.y

        self.editor_pan(dx, dy)

    def editor_pan_end(self, event):
        self._pan_last_x = None
        self._pan_last_y = None

    def editor_pan_key(self, event):
        if self.mode != "editor":
            return

        if event.keysym == "Left":
            self.editor_pan(-EDITOR_PAN_STEP, 0)

        elif event.keysym == "Right":
            self.editor_pan(EDITOR_PAN_STEP, 0)

    def editor_vertical_key(self, event):
        if self.mode != "editor":
            return

        if event.keysym == "Up":
            self.editor_pan(0, -EDITOR_PAN_STEP)

        elif event.keysym == "Down":
            self.editor_pan(0, EDITOR_PAN_STEP)

    def editor_pan_wheel(self, event):
        if self.mode != "editor":
            return

        if hasattr(event, "num") and event.num in (4, 5):
            if event.num == 4:
                self.editor_pan(0, -EDITOR_PAN_STEP)

            else:
                self.editor_pan(0, EDITOR_PAN_STEP)

            return

        if getattr(event, "delta", 0):
            if event.delta > 0:
                self.editor_pan(0, -EDITOR_PAN_STEP)

            else:
                self.editor_pan(0, EDITOR_PAN_STEP)

    # ------------------------------------------------------------------
    # EDITOR OBJECTS
    # ------------------------------------------------------------------

    def draw_editor_objects(self):
        self.canvas.delete("editor_obj")

        for i, obj in enumerate(
            self.editor_level["objects"]
        ):
            sx = self.editor_screen_x(obj["x"])
            sy = self.editor_screen_y(obj["y"])

            w = obj["w"] * EDITOR_ZOOM
            h = obj["h"] * EDITOR_ZOOM

            if (
                sx + w < EDITOR_VIEW_X0
                or sx > EDITOR_VIEW_X1
                or sy + h < EDITOR_VIEW_Y0
                or sy > EDITOR_VIEW_Y1
            ):
                continue

            fill = (
                obj.get("fill")
                or DEFAULT_FILL.get(
                    obj["type"],
                    BLOCK_COLOR
                )
            )

            outline = (
                obj.get("outline")
                or TEXT_COLOR
            )

            if obj["type"] == "spike":
                pts = [
                    sx,
                    sy + h,
                    sx + w / 2,
                    sy,
                    sx + w,
                    sy + h
                ]

                item = self.canvas.create_polygon(
                    pts,
                    fill=fill,
                    outline=outline,
                    width=2,
                    tags=("editor_obj", f"obj{i}")
                )

            elif obj["type"] == "decor":
                pts = [
                    sx + w / 2,
                    sy,
                    sx + w,
                    sy + h / 2,
                    sx + w / 2,
                    sy + h,
                    sx,
                    sy + h / 2
                ]

                item = self.canvas.create_polygon(
                    pts,
                    fill=fill,
                    outline=outline,
                    width=2,
                    tags=("editor_obj", f"obj{i}")
                )

            elif obj["type"] in (
                "teleport1",
                "teleport2"
            ):
                item = self.canvas.create_rectangle(
                    sx,
                    sy,
                    sx + w,
                    sy + h,
                    fill=fill,
                    outline=outline,
                    width=3,
                    tags=("editor_obj", f"obj{i}")
                )

                self.canvas.create_text(
                    sx + w / 2,
                    sy + h / 2,
                    text=(
                        "1"
                        if obj["type"] == "teleport1"
                        else "2"
                    ),
                    fill=TEXT_COLOR,
                    font=("Consolas", 12, "bold"),
                    tags=("editor_obj", f"obj{i}")
                )

            else:
                item = self.canvas.create_rectangle(
                    sx,
                    sy,
                    sx + w,
                    sy + h,
                    fill=fill,
                    outline=outline,
                    width=2,
                    tags=("editor_obj", f"obj{i}")
                )

            self.canvas.tag_bind(
                item,
                "<Button-1>",
                lambda e, idx=i:
                self.on_object_click(idx)
            )

        if (
            self.editor_selected_item is not None
            and self.editor_selected_item
            < len(self.editor_level["objects"])
        ):
            self.draw_selection_box(
                self.editor_selected_item
            )

    def draw_selection_box(self, idx):
        self.canvas.delete("selection")

        obj = self.editor_level["objects"][idx]

        sx = self.editor_screen_x(obj["x"])
        sy = self.editor_screen_y(obj["y"])

        w = obj["w"] * EDITOR_ZOOM
        h = obj["h"] * EDITOR_ZOOM

        self.canvas.create_rectangle(
            sx - 3,
            sy - 3,
            sx + w + 3,
            sy + h + 3,
            outline="#ffe066",
            width=3,
            tags="selection"
        )

    def draw_editor_spawn_marker(self):
        self.canvas.delete("spawn_marker")

        sx = self.editor_screen_x(
            PLAYER_START_X
        )

        sy = self.editor_screen_y(
            GROUND_Y - PLAYER_SIZE
        )

        w = SPAWN_ZONE_WIDTH * EDITOR_ZOOM
        h = SPAWN_ZONE_HEIGHT * EDITOR_ZOOM

        if (
            sx + w < EDITOR_VIEW_X0
            or sx > EDITOR_VIEW_X1
            or sy + h < EDITOR_VIEW_Y0
            or sy > EDITOR_VIEW_Y1
        ):
            return

        self.canvas.create_rectangle(
            sx,
            sy,
            sx + w,
            sy + h,
            outline="#39e6ff",
            width=2,
            dash=(5, 3),
            tags="spawn_marker"
        )

        self.canvas.create_text(
            sx + w / 2,
            sy - 10,
            text="PLAYER SPAWN",
            fill="#9fb0e0",
            font=("Consolas", 9, "bold"),
            tags="spawn_marker"
        )

    # ------------------------------------------------------------------
    # EDITOR SELECTION / MOVE
    # ------------------------------------------------------------------

    def on_object_click(self, idx):
        if self.editor_tool == "delete":
            self.delete_object(idx)
            return

        if self.editor_tool == "move":
            self.start_object_move(idx)
            return

        self.select_editor_object(idx)

    def select_editor_object(self, idx):
        self.editor_selected_item = idx
        self.draw_selection_box(idx)

    def start_object_move(self, idx):
        if not (
            0 <= idx
            < len(self.editor_level["objects"])
        ):
            return

        obj = self.editor_level["objects"][idx]

        self.editor_selected_item = idx
        self.editor_move_index = idx

        mouse_x = self.root.winfo_pointerx()
        mouse_y = self.root.winfo_pointery()

        canvas_x = (
            mouse_x
            - self.root.winfo_rootx()
        )

        canvas_y = (
            mouse_y
            - self.root.winfo_rooty()
        )

        level_x = self.editor_level_x(
            canvas_x
        )

        level_y = self.editor_level_y(
            canvas_y
        )

        self.editor_move_offset_x = (
            level_x - obj["x"]
        )

        self.editor_move_offset_y = (
            level_y - obj["y"]
        )

        self.draw_selection_box(idx)

    def editor_move_drag(self, event):
        if (
            self.mode != "editor"
            or self.editor_tool != "move"
            or self.editor_move_index is None
        ):
            return

        idx = self.editor_move_index

        if not (
            0 <= idx
            < len(self.editor_level["objects"])
        ):
            return

        obj = self.editor_level["objects"][idx]

        level_x = (
            self.editor_level_x(event.x)
            - self.editor_move_offset_x
        )

        level_y = (
            self.editor_level_y(event.y)
            - self.editor_move_offset_y
        )

        gx = (
            math.floor(level_x / CUBE)
            * CUBE
        )

        gy = (
            math.floor(level_y / CUBE)
            * CUBE
        )

        gx = max(
            0,
            min(
                EDITOR_LEVEL_WIDTH - obj["w"],
                gx
            )
        )

        gy = max(
            0,
            min(
                EDITOR_LEVEL_HEIGHT - obj["h"],
                gy
            )
        )

        old_x = obj["x"]
        old_y = obj["y"]

        obj["x"] = gx
        obj["y"] = gy

        if self.object_inside_spawn(obj):
            obj["x"] = old_x
            obj["y"] = old_y

        elif self.object_overlaps_other(
            idx,
            obj
        ):
            obj["x"] = old_x
            obj["y"] = old_y

        self.draw_editor_objects()

    def editor_move_release(self, event):
        if self.mode != "editor":
            return

        self.editor_move_index = None

    def delete_object(self, idx):
        if not (
            0 <= idx
            < len(self.editor_level["objects"])
        ):
            return

        self.editor_level["objects"].pop(idx)

        self.editor_selected_item = None
        self.editor_move_index = None

        self.canvas.delete("selection")

        self.draw_editor_objects()

    def editor_delete_selected(self, event=None):
        if self.mode != "editor":
            return

        if self.editor_selected_item is not None:
            self.delete_object(
                self.editor_selected_item
            )

    # ------------------------------------------------------------------
    # EDITOR PLACEMENT
    # ------------------------------------------------------------------

    def object_inside_spawn(self, obj):
        spawn_x1 = PLAYER_START_X
        spawn_x2 = (
            PLAYER_START_X
            + SPAWN_ZONE_WIDTH
        )

        spawn_y2 = GROUND_Y
        spawn_y1 = (
            GROUND_Y
            - SPAWN_ZONE_HEIGHT
        )

        ox1 = obj["x"]
        ox2 = obj["x"] + obj["w"]

        oy1 = obj["y"]
        oy2 = obj["y"] + obj["h"]

        return (
            ox1 < spawn_x2
            and ox2 > spawn_x1
            and oy1 < spawn_y2
            and oy2 > spawn_y1
        )

    def object_overlaps_other(self, index, obj):
        for i, existing in enumerate(
            self.editor_level["objects"]
        ):
            if i == index:
                continue

            if (
                existing["x"] < obj["x"] + obj["w"]
                and existing["x"] + existing["w"]
                > obj["x"]
                and existing["y"] < obj["y"] + obj["h"]
                and existing["y"] + existing["h"]
                > obj["y"]
            ):
                return True

        return False

    def has_unpaired_tp1(self):
        tp1_count = sum(
            1
            for obj in self.editor_level["objects"]
            if obj["type"] == "teleport1"
        )

        tp2_count = sum(
            1
            for obj in self.editor_level["objects"]
            if obj["type"] == "teleport2"
        )

        return tp1_count > tp2_count

    def handle_editor_click(self, x, y):
        if self.editor_tool != "place":
            return

        if (
            x < EDITOR_VIEW_X0
            or x > EDITOR_VIEW_X1
            or y < EDITOR_VIEW_Y0
            or y > EDITOR_VIEW_Y1
        ):
            return

        level_x = self.editor_level_x(x)
        level_y = self.editor_level_y(y)

        gx = (
            math.floor(level_x / CUBE)
            * CUBE
        )

        gy = (
            math.floor(level_y / CUBE)
            * CUBE
        )

        gx = max(
            0,
            min(
                EDITOR_LEVEL_WIDTH - CUBE,
                gx
            )
        )

        gy = max(
            0,
            min(
                EDITOR_LEVEL_HEIGHT - CUBE,
                gy
            )
        )

        block_type = self.editor_block

        if (
            block_type == "teleport1"
            and self.has_unpaired_tp1()
        ):
            messagebox.showwarning(
                "Teleport",
                "Place Teleport 2 before placing another Teleport 1."
            )
            return

        obj = {
            "type": block_type,
            "x": gx,
            "y": gy,
            "w": CUBE,
            "h": CUBE
        }

        if self.object_inside_spawn(obj):
            return

        if self.object_overlaps_other(
            -1,
            obj
        ):
            return

        if self.editor_fill_color:
            obj["fill"] = self.editor_fill_color

        if self.editor_outline_color:
            obj["outline"] = self.editor_outline_color

        self.editor_level["objects"].append(obj)

        self.editor_selected_item = None

        self.draw_editor_objects()

    # ------------------------------------------------------------------
    # EDITOR CLEAR / SAVE / LOAD
    # ------------------------------------------------------------------

    def clear_editor(self):
        self.editor_level["objects"] = []
        self.editor_selected_item = None
        self.editor_move_index = None

        self.draw_editor_objects()

    def save_editor_level(self):
        name = self.prompt_text(
            "Level name",
            "Custom Level"
        )

        if not name:
            return

        level = {
            "name": name,
            "speed": 1.0,
            "objects": list(
                self.editor_level["objects"]
            ),
            "custom": True,
            "bg_top": self.editor_level.get(
                "bg_top",
                BG_TOP
            ),
            "bg_bottom": self.editor_level.get(
                "bg_bottom",
                BG_BOTTOM
            )
        }

        self.levels.append(level)

        self.save_custom_levels()

        messagebox.showinfo(
            "Saved",
            f"Saved level '{name}' to {CUSTOM_LEVELS_FILE}"
        )

    def prompt_text(self, title, default=""):
        win = tk.Toplevel(self.root)

        win.title(title)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(
            win,
            text=title,
            font=("Consolas", 12, "bold")
        ).pack(
            padx=14,
            pady=(14, 6)
        )

        entry = tk.Entry(
            win,
            width=30
        )

        entry.insert(0, default)

        entry.pack(
            padx=14,
            pady=6
        )

        result = {
            "value": None
        }

        def ok():
            result["value"] = entry.get().strip()
            win.destroy()

        tk.Button(
            win,
            text="OK",
            command=ok
        ).pack(
            pady=(6, 12)
        )

        entry.focus_set()

        win.wait_window()

        return result["value"]

    def load_level_from_file(self):
        path = filedialog.askopenfilename(
            initialdir=LEVELS_DIR,
            title="Open level JSON",
            filetypes=[
                ("JSON files", "*.json")
            ]
        )

        if not path:
            return

        try:
            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:
                level = json.load(f)

            if "objects" not in level:
                raise ValueError(
                    "Invalid level file"
                )

            level["custom"] = True

            self.levels.append(level)

            self.save_custom_levels()

            messagebox.showinfo(
                "Loaded",
                f"Loaded '{level.get('name', 'Unnamed')}'"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                str(e)
            )

    def play_editor_level(self):
        level = {
            "name": self.editor_level.get(
                "name",
                "Editor Level"
            ),
            "speed": 1.0,
            "objects": list(
                self.editor_level["objects"]
            ),
            "custom": True,
            "bg_top": self.editor_level.get(
                "bg_top",
                BG_TOP
            ),
            "bg_bottom": self.editor_level.get(
                "bg_bottom",
                BG_BOTTOM
            )
        }

        self.levels.append(level)

        self.selected_level_index = (
            len(self.levels) - 1
        )

        self.start_selected_level()

    # ------------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------------

    def loop(self):
        if (
            self.mode == "game"
            and not self.game_over
        ):
            if self.started:
                gravity = GRAVITY

                if (
                    abs(self.vel_y)
                    < APEX_THRESHOLD
                ):
                    gravity *= APEX_GRAVITY_SCALE

                self.vel_y += gravity

                if (
                    self.vel_y
                    > TERMINAL_VELOCITY
                ):
                    self.vel_y = TERMINAL_VELOCITY

                prev_bottom = (
                    self.player_y
                    + PLAYER_SIZE
                )

                self.player_y += self.vel_y

                new_bottom = (
                    self.player_y
                    + PLAYER_SIZE
                )

                landed_on_block = (
                    self.resolve_block_landing(
                        prev_bottom,
                        new_bottom
                    )
                )

                if (
                    self.player_y
                    >= GROUND_Y - PLAYER_SIZE
                ):
                    self.player_y = (
                        GROUND_Y - PLAYER_SIZE
                    )

                    self.vel_y = 0
                    self.on_ground = True

                elif landed_on_block:
                    self.on_ground = True

                else:
                    self.on_ground = False

                if self.on_ground:
                    self.rotation = 0
                else:
                    self.rotation = (
                        self.rotation + 9
                    ) % 360

                self.bg_offset += self.speed

                self.canvas.coords(
                    self.player,
                    *self.player_points()
                )

                self.update_obstacles()
                self.update_particles()

                self.distance += self.speed

                self.score = int(
                    self.distance // 10
                )

                self.canvas.itemconfig(
                    self.score_text,
                    text=f"Score: {self.score}"
                )

                self.check_teleports()

                result = self.check_collision()

                if result == "death":
                    self.end_game(False)

                elif result == "finish":
                    self.end_game(True)

            else:
                self.canvas.coords(
                    self.player,
                    *self.player_points()
                )

            if not self.game_over:
                self.draw_background()

                self.canvas.tag_raise("game")
                self.canvas.tag_raise("ui")
                self.canvas.tag_raise(
                    self.player
                )

                self.canvas.coords(
                    self.player,
                    *self.player_points()
                )

                self.canvas.itemconfig(
                    self.level_text,
                    text=f"Level: {self.level['name']}"
                )

        elif self.mode == "editor":
            self.draw_background()

            self.canvas.tag_raise("ui")
            self.canvas.tag_raise(
                "editor_grid"
            )
            self.canvas.tag_raise(
                "editor_obj"
            )
            self.canvas.tag_raise(
                "spawn_marker"
            )
            self.canvas.tag_raise(
                "selection"
            )

        else:
            self.draw_background()
            self.canvas.tag_raise("ui")

        self.schedule_loop()


if __name__ == "__main__":
    root = tk.Tk()
    GeometryDash(root)
    root.mainloop()
