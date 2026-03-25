import sys
import os
import math
import numpy as np
import moderngl
import moderngl_window as mglw
from moderngl_window import settings

from fractals.koch import generate_koch


def load_shader(filename):
    # Works both normally and when frozen by PyInstaller
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(__file__)
    with open(os.path.join(base, "fractals", filename)) as f:
        return f.read()


# ── Fractal registry ──────────────────────────────────────────────────────────

FRACTALS = [
    {
        "name":   "Mandelbrot Set",
        "type":   "shader",
        "file":   "mandelbrot.glsl",
        "center": [-0.5,  0.0],
        "zoom":    3.0,
    },
    {
        "name":   "Julia Set",
        "type":   "shader",
        "file":   "julia.glsl",
        "center": [ 0.0,  0.0],
        "zoom":    3.0,
    },
    {
        "name":   "Burning Ship",
        "type":   "shader",
        "file":   "burningship.glsl",
        "center": [-0.5,  0.5],
        "zoom":    3.5,
    },
    {
        "name":    "Koch Snowflake",
        "type":    "geometry",
        "generate": lambda: generate_koch(depth=5),
        "mode":    "LINE_LOOP",
        "center":  [0.0,  0.0],
        "zoom":    3.2,
        "color":   (0.2, 0.7, 1.0),
    },
    {
        "name":   "Sierpinski Triangle",
        "type":   "shader",
        "file":   "sierpinski.glsl",
        "center": [ 0.0,  0.0],
        "zoom":    3.0,
    },
]

# ── Screensaver animation sequence ────────────────────────────────────────────
# Each step zooms toward `target` starting from `start_zoom` down to `end_zoom`,
# then cross-fades to the next step.

ANIM_SEQUENCE = [
    {"fractal": "Mandelbrot Set",      "target": [-0.74878,  0.06508], "start_zoom": 3.0,  "end_zoom": 3e-6},
    {"fractal": "Sierpinski Triangle", "target": [ 0.0,      1.0    ], "start_zoom": 3.0,  "end_zoom": 5e-7},
    {"fractal": "Julia Set",           "target": [ 0.0,      0.0    ], "start_zoom": 3.0,  "end_zoom": 2e-5},
    {"fractal": "Mandelbrot Set",      "target": [-0.1592,  -1.0317 ], "start_zoom": 3.0,  "end_zoom": 5e-6},
    {"fractal": "Burning Ship",        "target": [-0.5,      0.5    ], "start_zoom": 3.5,  "end_zoom": 8e-4},
    {"fractal": "Sierpinski Triangle", "target": [-0.43301,  0.25   ], "start_zoom": 3.0,  "end_zoom": 5e-7},
    {"fractal": "Julia Set",           "target": [ 0.5,      0.0    ], "start_zoom": 3.0,  "end_zoom": 5e-5},
    {"fractal": "Mandelbrot Set",      "target": [ 0.3023,   0.01885], "start_zoom": 3.0,  "end_zoom": 3e-6},
]

ZOOM_SPEED   = 0.22   # zoom halves every ~3 s
CENTER_LERP  = 1.0    # how fast center tracks target (exponential, per second)
FADE_SPEED   = 1.2    # fade alpha units per second

# Detect screensaver mode from command line (/s flag)
SCREENSAVER_MODE = any(a.lower() == "/s" for a in sys.argv[1:])


# ── Main window class ─────────────────────────────────────────────────────────

class FractalVisualizer(mglw.WindowConfig):
    title     = "Fractal Visualizer"
    window_size = (1280, 720)
    aspect_ratio = None
    resizable = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ctx.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # ── Fullscreen quad (shared) ──────────────────────────────────────────
        quad = np.array([-1,-1, 1,-1, -1,1, 1,-1, 1,1, -1,1], dtype="f4")
        quad_vbo = self.ctx.buffer(quad)
        vert_src  = load_shader("vertex.glsl")

        # One compiled program + VAO per shader fractal
        self._shader_renders = {}
        for f in FRACTALS:
            if f["type"] == "shader":
                prog = self.ctx.program(
                    vertex_shader=vert_src,
                    fragment_shader=load_shader(f["file"]),
                )
                vao = self.ctx.vertex_array(prog, [(quad_vbo, "2f", "in_position")])
                self._shader_renders[f["name"]] = (prog, vao)

        # Shared program for geometry fractals
        self._geo_prog = self.ctx.program(
            vertex_shader=load_shader("geometry_vertex.glsl"),
            fragment_shader=load_shader("geometry_fragment.glsl"),
        )
        self._geo_renders = {}
        for f in FRACTALS:
            if f["type"] == "geometry":
                print(f"Generating {f['name']}…")
                verts = f["generate"]()
                vbo = self.ctx.buffer(verts)
                vao = self.ctx.vertex_array(self._geo_prog, [(vbo, "2f", "in_position")])
                self._geo_renders[f["name"]] = (vao, getattr(moderngl, f["mode"]))

        # Fade-to-black overlay
        self._fade_prog = self.ctx.program(
            vertex_shader=vert_src,
            fragment_shader=load_shader("fade.glsl"),
        )
        self._fade_vao = self.ctx.vertex_array(
            self._fade_prog, [(quad_vbo, "2f", "in_position")]
        )

        # ── View state ────────────────────────────────────────────────────────
        self._current   = 0
        self._dragging  = False
        self._animating = False         # must be set before _switch_to calls _update_title
        self._switch_to(0)

        # ── Animation / screensaver state ────────────────────────────────────
        self._anim_idx    = 0
        self._anim_state  = "zooming"   # 'zooming' | 'fade_out' | 'fade_in'
        self._fade_alpha  = 0.0
        self._anim_target = [0.0, 0.0]
        self._anim_end_zoom = 1.0
        self._mouse_moved = 0           # cumulative px moved (screensaver exit)

        if SCREENSAVER_MODE:
            self._start_step(0)

    # ── Fractal switching ─────────────────────────────────────────────────────

    def _switch_to(self, idx):
        self._current = idx
        f = FRACTALS[idx]
        self.center   = list(f["center"])
        self.zoom     = f["zoom"]
        self.max_iter = 256
        if not SCREENSAVER_MODE:
            self._update_title()

    def _update_title(self):
        f = FRACTALS[self._current]
        n = len(FRACTALS)
        if self._animating:
            self.wnd.title = (
                f"Fractal Visualizer  —  {f['name']}  [ A: stop animation ]"
            )
        else:
            self.wnd.title = (
                f"Fractal Visualizer  —  {f['name']}  "
                f"[ 1-{n}: switch | drag: pan | scroll: zoom | R: reset | A: animate ]"
            )

    def _start_step(self, idx):
        self._anim_idx = idx % len(ANIM_SEQUENCE)
        step = ANIM_SEQUENCE[self._anim_idx]

        fractal_idx = next(
            i for i, f in enumerate(FRACTALS) if f["name"] == step["fractal"]
        )
        self._switch_to(fractal_idx)
        self.zoom = step["start_zoom"]
        self._anim_target   = list(step["target"])
        self._anim_end_zoom = step["end_zoom"]
        self._anim_state    = "zooming"

    # ── Rendering ─────────────────────────────────────────────────────────────

    def on_render(self, time, frame_time):
        dt = min(frame_time, 0.1)   # clamp to avoid jump after pause/resize

        if SCREENSAVER_MODE or self._animating:
            self._update_animation(dt)

        self.ctx.clear(0.05, 0.05, 0.08)
        w, h = self.wnd.size
        self._draw_fractal(w, h)

        # Fade overlay
        if self._fade_alpha > 0.001:
            self._fade_prog["u_alpha"].value = self._fade_alpha
            self._fade_vao.render(moderngl.TRIANGLES)

    def _draw_fractal(self, w, h):
        f = FRACTALS[self._current]
        if f["type"] == "shader":
            prog, vao = self._shader_renders[f["name"]]
            prog["u_resolution"].value = (w, h)
            prog["u_center"].value     = tuple(self.center)
            prog["u_zoom"].value       = self.zoom
            prog["u_max_iter"].value   = self.max_iter
            vao.render(moderngl.TRIANGLES)
        else:
            vao, mode = self._geo_renders[f["name"]]
            self._geo_prog["u_resolution"].value = (w, h)
            self._geo_prog["u_center"].value     = tuple(self.center)
            self._geo_prog["u_zoom"].value       = self.zoom
            self._geo_prog["u_color"].value      = f["color"]
            vao.render(mode)

    # ── Animation ─────────────────────────────────────────────────────────────

    def _update_animation(self, dt):
        if self._anim_state == "zooming":
            # Zoom in exponentially
            self.zoom *= math.exp(-ZOOM_SPEED * dt)

            # Slide center toward target
            t = 1.0 - math.exp(-CENTER_LERP * dt)
            self.center[0] += (self._anim_target[0] - self.center[0]) * t
            self.center[1] += (self._anim_target[1] - self.center[1]) * t

            # Auto-scale iterations so detail stays sharp at depth
            depth_factor = math.log2(max(3.0 / self.zoom, 2.0))
            self.max_iter = min(2048, max(256, int(120 * depth_factor)))

            if self.zoom <= self._anim_end_zoom:
                self._anim_state = "fade_out"

        elif self._anim_state == "fade_out":
            self._fade_alpha = min(1.0, self._fade_alpha + FADE_SPEED * dt)
            if self._fade_alpha >= 1.0:
                self._start_step(self._anim_idx + 1)
                self._anim_state = "fade_in"   # _start_step sets state, override

        elif self._anim_state == "fade_in":
            self._fade_alpha = max(0.0, self._fade_alpha - FADE_SPEED * dt)
            if self._fade_alpha <= 0.0:
                self._anim_state = "zooming"

    # ── Input — mouse ─────────────────────────────────────────────────────────

    def on_mouse_position_event(self, x, y, dx, dy):
        if SCREENSAVER_MODE:
            self._mouse_moved += abs(dx) + abs(dy)
            if self._mouse_moved > 10:
                self.wnd.close()

    def on_mouse_press_event(self, x, y, button):
        if SCREENSAVER_MODE:
            self.wnd.close()
        elif button == 1:
            self._dragging = True

    def on_mouse_release_event(self, x, y, button):
        if button == 1:
            self._dragging = False

    def on_mouse_drag_event(self, x, y, dx, dy):
        if SCREENSAVER_MODE or self._animating or not self._dragging:
            return
        _, h = self.wnd.size
        scale = self.zoom / h
        self.center[0] -= dx * scale
        self.center[1] += dy * scale

    def on_mouse_scroll_event(self, x_offset, y_offset):
        if not SCREENSAVER_MODE and not self._animating:
            self.zoom *= 0.85 if y_offset > 0 else 1.15

    # ── Input — keyboard ──────────────────────────────────────────────────────

    def on_key_event(self, key, action, modifiers):
        keys = self.wnd.keys
        if action != keys.ACTION_PRESS:
            return

        if SCREENSAVER_MODE:
            self.wnd.close()
            return

        if ord("1") <= key <= ord("9"):
            idx = key - ord("1")
            if idx < len(FRACTALS):
                self._switch_to(idx)
            return

        if key in (ord("a"), ord("A")):
            self._animating = not self._animating
            if self._animating:
                self._start_step(self._anim_idx)   # resume from current position
            else:
                self._fade_alpha = 0.0             # clear any fade overlay
            self._update_title()
            return

        if self._animating:
            return  # ignore other keys while animating

        if key == keys.UP:
            self.max_iter = min(self.max_iter + 64, 2048)
        elif key == keys.DOWN:
            self.max_iter = max(self.max_iter - 64, 64)
        elif key in (ord("r"), ord("R")):
            self._switch_to(self._current)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    argv_lower = " ".join(sys.argv[1:]).lower()

    # /c  →  configuration dialog (Windows only)
    if "/c" in argv_lower:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                "Fractal Screensaver\n\n"
                "No configurable settings.\n\n"
                "During normal (interactive) use:\n"
                "  1-5  Switch fractal\n"
                "  Scroll  Zoom in / out\n"
                "  Drag    Pan\n"
                "  ↑ / ↓  More / less detail\n"
                "  R       Reset view",
                "Fractal Screensaver",
                0x40,  # MB_ICONINFORMATION
            )
        except Exception:
            pass
        sys.exit(0)

    # /p <hwnd>  →  preview pane inside Screen Saver Settings — exit cleanly
    if "/p" in argv_lower:
        sys.exit(0)

    # Strip our custom args so moderngl-window's argparse doesn't choke on them
    sys.argv = [sys.argv[0]]

    # /s  →  screensaver (fullscreen, animated, exits on any input)
    settings.WINDOW["class"] = "moderngl_window.context.pyglet.Window"
    if SCREENSAVER_MODE:
        settings.WINDOW["fullscreen"] = True

    mglw.run_window_config(FractalVisualizer)
