"""AgentHome Pixel Art Asset Generator.

Run once to generate all PNG assets into resources/art/.
Uses Pillow for programmatic pixel art generation.

Usage:
    python tools/generate_assets.py
"""

import os
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ART_DIR = ROOT / "resources" / "art"

TILESET_DIR = ART_DIR / "tileset"
CHAR_DIR = ART_DIR / "characters"
ICON_DIR = ART_DIR / "icons"
UI_DIR = ART_DIR / "ui"
PARTICLE_DIR = ART_DIR / "particles"

FILE_COUNT = 0


def ensure_dirs():
    for d in [TILESET_DIR, CHAR_DIR, ICON_DIR, UI_DIR, PARTICLE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def save(img: Image.Image, path: Path):
    """Save image and increment global file counter."""
    global FILE_COUNT
    img.save(str(path))
    FILE_COUNT += 1


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def darken(color, factor=0.7):
    """Always returns 3-tuple RGB. Use + (255,) for RGBA."""
    return tuple(max(0, int(c * factor)) for c in color[:3])


def lighten(color, factor=1.3):
    """Always returns 3-tuple RGB. Use + (255,) for RGBA."""
    return tuple(min(255, int(c * factor)) for c in color[:3])


def with_alpha(color, alpha):
    return color[:3] + (alpha,)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def set_px(img: Image.Image, x, y, color):
    """Safe pixel set."""
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), color)


def fill_rect(draw: ImageDraw.ImageDraw, x, y, w, h, color):
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=color)


def draw_circle_filled(draw: ImageDraw.ImageDraw, cx, cy, r, color):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)


def draw_circle_outline(draw: ImageDraw.ImageDraw, cx, cy, r, color):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color)


# ===================================================================
# 1. TERRAIN TILES (32x32)
# ===================================================================

def generate_terrain_tiles():
    _gen_grass_tiles()
    _gen_forest_tiles()
    _gen_rock_tiles()
    _gen_water_tile()
    _gen_town_tiles()
    _gen_exchange_tile()


def _gen_grass_tiles():
    base = hex_to_rgb("#2a4a2a")
    for variant in range(4):
        img = Image.new("RGBA", (32, 32), base + (255,))
        draw = ImageDraw.Draw(img)
        rng = random.Random(42 + variant)
        # Scatter lighter / darker dots
        for _ in range(40):
            x, y = rng.randint(0, 31), rng.randint(0, 31)
            shade = rng.choice([darken(base, 0.85), lighten(base, 1.2), lighten(base, 1.35)])
            set_px(img, x, y, shade + (255,))
        # Grass tufts — short vertical lines
        num_tufts = 8 + variant * 3
        for _ in range(num_tufts):
            tx = rng.randint(1, 30)
            ty = rng.randint(4, 30)
            height = rng.randint(2, 4)
            c = rng.choice([lighten(base, 1.4), lighten(base, 1.15), darken(base, 0.8)])
            for dy in range(height):
                set_px(img, tx, ty - dy, c + (255,))
            # tuft tip slightly lighter
            set_px(img, tx, ty - height, lighten(c, 1.2) + (255,))
        # Weed patterns unique per variant
        if variant in (1, 3):
            for _ in range(3):
                wx = rng.randint(3, 28)
                wy = rng.randint(3, 28)
                for dx, dy in [(-1, 0), (0, -1), (1, -1), (0, -2)]:
                    set_px(img, wx + dx, wy + dy, lighten(base, 1.5) + (255,))
        if variant in (2, 3):
            for _ in range(4):
                wx = rng.randint(3, 28)
                wy = rng.randint(3, 28)
                c2 = (0x3a, 0x6a, 0x2a, 255)
                set_px(img, wx, wy, c2)
                set_px(img, wx + 1, wy - 1, c2)
                set_px(img, wx - 1, wy - 1, c2)
        save(img, TILESET_DIR / f"grass_{variant}.png")


def _gen_forest_tiles():
    base = hex_to_rgb("#1a3a1a")
    for variant in range(3):
        img = Image.new("RGBA", (32, 32), base + (255,))
        draw = ImageDraw.Draw(img)
        rng = random.Random(100 + variant)
        # Ground texture
        for _ in range(25):
            x, y = rng.randint(0, 31), rng.randint(0, 31)
            set_px(img, x, y, darken(base, 0.85) + (255,))
        # Triangle tree silhouettes
        tree_positions = [(rng.randint(4, 27), rng.randint(8, 28)) for _ in range(2 + variant)]
        canopy_dark = darken(base, 0.6)
        canopy_mid = darken(base, 0.75)
        trunk_col = (0x3a, 0x2a, 0x1a, 255)
        for tx, ty in tree_positions:
            # Trunk
            for dy in range(3):
                set_px(img, tx, ty + dy, trunk_col)
            # Triangle canopy
            for row in range(6):
                half = row // 1 + 1
                for dx in range(-half, half + 1):
                    py = ty - row - 1
                    px = tx + dx
                    c = canopy_mid if abs(dx) < half else canopy_dark
                    set_px(img, px, py, c + (255,))
            # Shadow beneath
            for dx in range(-2, 3):
                set_px(img, tx + dx, ty + 3, darken(base, 0.5) + (255,))
        save(img, TILESET_DIR / f"forest_{variant}.png")


def _gen_rock_tiles():
    base = hex_to_rgb("#5a5a5a")
    for variant in range(2):
        img = Image.new("RGBA", (32, 32), (0x4a, 0x4a, 0x3a, 255))
        draw = ImageDraw.Draw(img)
        rng = random.Random(200 + variant)
        # Big angular rock shapes
        num_rocks = 2 + variant
        for _ in range(num_rocks):
            rx = rng.randint(4, 24)
            ry = rng.randint(4, 24)
            rw = rng.randint(6, 12)
            rh = rng.randint(5, 10)
            rock_col = (rng.randint(0x50, 0x6a), rng.randint(0x50, 0x6a), rng.randint(0x50, 0x6a), 255)
            fill_rect(draw, rx, ry, rw, rh, rock_col)
            # Lighter top highlight
            for dx in range(rw):
                set_px(img, rx + dx, ry, lighten(rock_col, 1.4))
                if dx < rw - 1:
                    set_px(img, rx + dx, ry + 1, lighten(rock_col, 1.2))
            # Crack lines
            cx, cy = rx + rw // 2, ry + rh // 2
            crack_col = darken(rock_col, 0.5)
            for step in range(4):
                set_px(img, cx + step, cy + rng.randint(-1, 1), crack_col)
            # Dark bottom edge
            for dx in range(rw):
                set_px(img, rx + dx, ry + rh - 1, darken(rock_col, 0.6))
        save(img, TILESET_DIR / f"rock_{variant}.png")


def _gen_water_tile():
    base = hex_to_rgb("#1a3a5a")
    img = Image.new("RGBA", (32, 32), base + (255,))
    draw = ImageDraw.Draw(img)
    wave_light = lighten(base, 1.5)
    wave_mid = lighten(base, 1.25)
    # Horizontal wavy lines
    for row in range(4):
        y = 4 + row * 7
        for x in range(32):
            offset = int(2 * math.sin(x * 0.6 + row * 1.2))
            set_px(img, x, y + offset, wave_light + (255,))
            set_px(img, x, y + offset + 1, wave_mid + (255,))
    # Subtle sparkle dots
    rng = random.Random(300)
    for _ in range(8):
        sx, sy = rng.randint(0, 31), rng.randint(0, 31)
        set_px(img, sx, sy, lighten(base, 1.8) + (200,))
    save(img, TILESET_DIR / "water_0.png")


def _gen_town_tiles():
    base = hex_to_rgb("#5a4a3a")
    window_glow = (0xff, 0xdd, 0x44, 255)
    for variant in range(2):
        img = Image.new("RGBA", (32, 32), base + (255,))
        draw = ImageDraw.Draw(img)
        rng = random.Random(400 + variant)
        # Ground texture
        for _ in range(20):
            x, y = rng.randint(0, 31), rng.randint(0, 31)
            set_px(img, x, y, darken(base, 0.85) + (255,))
        # Small house outlines
        if variant == 0:
            houses = [(3, 8, 12, 10), (18, 12, 11, 9)]
        else:
            houses = [(6, 6, 10, 12), (20, 10, 9, 10)]
        for hx, hy, hw, hh in houses:
            wall_col = lighten(base, 1.15) + (255,)
            roof_col = darken(base, 0.7) + (255,)
            # Wall
            draw.rectangle([hx, hy + 3, hx + hw - 1, hy + hh - 1], fill=wall_col,
                           outline=darken(base, 0.5) + (255,))
            # Roof triangle
            mid = hx + hw // 2
            for row in range(4):
                for dx in range(-row - 1, row + 2):
                    px = mid + dx
                    py = hy + 2 - row
                    set_px(img, px, py, roof_col)
            # Windows
            wx1 = hx + 2
            wx2 = hx + hw - 4
            wy = hy + 5
            for wx in [wx1, wx2]:
                set_px(img, wx, wy, window_glow)
                set_px(img, wx + 1, wy, window_glow)
                set_px(img, wx, wy + 1, window_glow)
                set_px(img, wx + 1, wy + 1, window_glow)
            # Door
            dx_door = hx + hw // 2 - 1
            door_col = darken(base, 0.6) + (255,)
            fill_rect(draw, dx_door, hy + hh - 4, 3, 4, door_col)
        save(img, TILESET_DIR / f"town_{variant}.png")


def _gen_exchange_tile():
    base = hex_to_rgb("#5a4a3a")
    gold = hex_to_rgb("#c8a832")
    img = Image.new("RGBA", (32, 32), base + (255,))
    draw = ImageDraw.Draw(img)
    # Gold border (2px)
    draw.rectangle([0, 0, 31, 31], outline=gold + (255,))
    draw.rectangle([1, 1, 30, 30], outline=gold + (255,))
    # Interior slightly lighter
    fill_rect(draw, 2, 2, 28, 28, lighten(base, 1.1) + (255,))
    # Scales icon in center
    cx, cy = 16, 16
    # Pole
    for dy in range(-5, 6):
        set_px(img, cx, cy + dy, gold + (255,))
    # Beam
    for dx in range(-6, 7):
        set_px(img, cx + dx, cy - 5, gold + (255,))
    # Left pan
    for dx in range(-2, 3):
        set_px(img, cx - 6 + dx, cy - 2, gold + (255,))
    # Right pan
    for dx in range(-2, 3):
        set_px(img, cx + 6 + dx, cy - 2, gold + (255,))
    # Chains
    for dy in range(3):
        set_px(img, cx - 6, cy - 5 + dy, gold + (255,))
        set_px(img, cx + 6, cy - 5 + dy, gold + (255,))
    # Base triangle
    for dx in range(-2, 3):
        set_px(img, cx + dx, cy + 6, gold + (255,))
    for dx in range(-1, 2):
        set_px(img, cx + dx, cy + 5, gold + (255,))
    save(img, TILESET_DIR / "exchange.png")


# ===================================================================
# 2. CHARACTER SPRITE SHEETS (128x96  =  4 cols x 3 rows of 32x32)
# ===================================================================

# Directions: col 0=down, 1=left, 2=right, 3=up
# Rows: 0=idle, 1=walk_a, 2=walk_b

CHARACTER_DEFS = [
    # (filename, body_hex, features, is_child, gender_hint)
    ("npc_he.png",       "#4CAF50", "apron_bun",     False, "f"),
    ("npc_sui.png",      "#E91E63", "twin_tails",    True,  "f"),
    ("npc_shan.png",     "#F44336", "hunched_stick",  False, "m"),
    ("npc_tang.png",     "#FF5722", "scarf",         False, "m"),
    ("npc_kuang.png",    "#2196F3", "messy_hair",    True,  "m"),
    ("npc_mu.png",       "#795548", "tool_belt",     False, "m"),
    ("npc_lan.png",      "#9C27B0", "shawl_hunched", False, "f"),
    ("npc_shi.png",      "#607D8B", "bow_back",      False, "m"),
    ("npc_shangren.png", "#FFC107", "hat_backpack",  False, "m"),
    ("player.png",       "#e94560", "cape",          False, "m"),
]


def generate_character_sprites():
    for fname, body_hex, features, is_child, gender in CHARACTER_DEFS:
        img = _make_sprite_sheet(body_hex, features, is_child, gender)
        save(img, CHAR_DIR / fname)


def _make_sprite_sheet(body_hex, features, is_child, gender):
    """Create a 128x96 sprite sheet with 12 frames."""
    sheet = Image.new("RGBA", (128, 96), (0, 0, 0, 0))
    body_col = hex_to_rgb(body_hex)
    skin = (0xf0, 0xd0, 0xb0)
    outline = darken(body_col, 0.5)
    hair_col = darken(body_col, 0.6)

    directions = ["down", "left", "right", "up"]
    anim_frames = ["idle", "walk_a", "walk_b"]

    for col, direction in enumerate(directions):
        for row, anim in enumerate(anim_frames):
            frame = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            _draw_character(frame, body_col, skin, outline, hair_col,
                            direction, anim, features, is_child, gender)
            sheet.paste(frame, (col * 32, row * 32))
    return sheet


def _draw_character(frame, body_col, skin, outline, hair_col,
                    direction, anim, features, is_child, gender):
    """Draw a single 32x32 character frame."""
    draw = ImageDraw.Draw(frame)

    # Dimensions based on child/adult
    if is_child:
        head_r = 4
        body_h = 7
        leg_h = 4
        total_h = head_r * 2 + body_h + leg_h  # ~19
        cx = 16
        head_cy = 32 - total_h + head_r  # top of sprite area
        body_top = head_cy + head_r + 1
        body_w = 6
    else:
        head_r = 4
        body_h = 10
        leg_h = 5
        total_h = head_r * 2 + body_h + leg_h  # ~23
        cx = 16
        head_cy = 32 - total_h + head_r
        body_top = head_cy + head_r + 1
        body_w = 8

    body_bottom = body_top + body_h
    leg_bottom = body_bottom + leg_h

    # Walk bob offset
    bob = 0
    if anim == "walk_a":
        bob = -1
    elif anim == "walk_b":
        bob = 0

    head_cy += bob
    body_top += bob
    body_bottom += bob

    # --- Head ---
    head_col = skin + (255,)
    outline_a = outline + (255,)
    draw_circle_filled(draw, cx, head_cy, head_r, head_col)
    draw_circle_outline(draw, cx, head_cy, head_r, outline_a)

    # Eyes based on direction
    eye_col = (0x20, 0x20, 0x20, 255)
    if direction == "down":
        set_px(frame, cx - 2, head_cy, eye_col)
        set_px(frame, cx + 2, head_cy, eye_col)
    elif direction == "left":
        set_px(frame, cx - 2, head_cy, eye_col)
    elif direction == "right":
        set_px(frame, cx + 2, head_cy, eye_col)
    elif direction == "up":
        pass  # No eyes from behind

    # Hair on top of head
    hair_a = hair_col + (255,)
    for dx in range(-head_r + 1, head_r):
        set_px(frame, cx + dx, head_cy - head_r, hair_a)
        set_px(frame, cx + dx, head_cy - head_r + 1, hair_a)

    # --- Body ---
    body_a = body_col + (255,)
    half_w = body_w // 2
    draw.rectangle([cx - half_w, body_top, cx + half_w - 1, body_bottom - 1],
                   fill=body_a, outline=outline_a)

    # Shoulder shading
    for dx in range(-half_w, half_w):
        set_px(frame, cx + dx, body_top, lighten(body_col, 1.2) + (255,))

    # --- Legs ---
    leg_spread = 0
    if anim == "walk_a":
        leg_spread = 2
    elif anim == "walk_b":
        leg_spread = -2

    leg_col = darken(body_col, 0.8) + (255,)
    shoe_col = darken(body_col, 0.5) + (255,)
    # Left leg
    lx = cx - 2 + (leg_spread if anim == "walk_a" else (-leg_spread if anim == "walk_b" else 0))
    for dy in range(leg_h):
        set_px(frame, cx - 2, body_bottom + dy, leg_col)
        set_px(frame, cx - 1, body_bottom + dy, leg_col)
    # Right leg
    for dy in range(leg_h):
        set_px(frame, cx + 1, body_bottom + dy, leg_col)
        set_px(frame, cx + 2, body_bottom + dy, leg_col)

    # Walk animation: shift leg pixels
    if anim == "walk_a":
        # Left leg forward
        set_px(frame, cx - 3, body_bottom + leg_h - 2, leg_col)
        set_px(frame, cx - 3, body_bottom + leg_h - 1, shoe_col)
        set_px(frame, cx + 2, body_bottom + leg_h - 1, shoe_col)
    elif anim == "walk_b":
        # Right leg forward
        set_px(frame, cx + 3, body_bottom + leg_h - 2, leg_col)
        set_px(frame, cx + 3, body_bottom + leg_h - 1, shoe_col)
        set_px(frame, cx - 2, body_bottom + leg_h - 1, shoe_col)
    else:
        # Idle shoes
        set_px(frame, cx - 2, body_bottom + leg_h - 1, shoe_col)
        set_px(frame, cx + 2, body_bottom + leg_h - 1, shoe_col)

    # --- Arms ---
    arm_col = skin + (255,)
    if direction == "left":
        # Left arm visible
        for dy in range(body_h - 2):
            set_px(frame, cx - half_w - 1, body_top + 2 + dy, arm_col)
    elif direction == "right":
        for dy in range(body_h - 2):
            set_px(frame, cx + half_w, body_top + 2 + dy, arm_col)
    else:
        # Arms on sides
        for dy in range(body_h - 3):
            set_px(frame, cx - half_w - 1, body_top + 2 + dy, arm_col)
            set_px(frame, cx + half_w, body_top + 2 + dy, arm_col)

    # --- Features ---
    _draw_features(frame, draw, cx, head_cy, head_r, body_top, body_bottom,
                   body_w, body_col, outline, hair_col, direction, features, is_child, bob)


def _draw_features(frame, draw, cx, head_cy, head_r, body_top, body_bottom,
                   body_w, body_col, outline, hair_col, direction, features, is_child, bob):
    """Draw character-specific features."""
    half_w = body_w // 2

    if features == "apron_bun":
        # Apron: lighter rectangle on front torso
        apron_col = lighten(body_col, 1.5) + (255,)
        if direction != "up":
            for dy in range(3, 7):
                for dx in range(-2, 3):
                    set_px(frame, cx + dx, body_top + dy, apron_col)
        # Hair bun on top
        bun_col = darken(hair_col, 0.8) + (255,)
        draw_circle_filled(draw, cx, head_cy - head_r - 1, 2, bun_col)

    elif features == "twin_tails":
        # Twin tails: two small circles on sides of head
        tail_col = darken(hair_col, 0.7) + (255,)
        draw_circle_filled(draw, cx - head_r - 1, head_cy - 1, 2, tail_col)
        draw_circle_filled(draw, cx + head_r + 1, head_cy - 1, 2, tail_col)

    elif features == "hunched_stick":
        # Hunched posture: darken upper body one side
        hunch_col = darken(body_col, 0.7) + (255,)
        for dy in range(3):
            set_px(frame, cx + half_w - 1, body_top + dy, hunch_col)
            set_px(frame, cx + half_w, body_top + dy, hunch_col)
        # Walking stick
        stick_col = (0x8a, 0x6a, 0x4a, 255)
        if direction in ("down", "left"):
            sx = cx + half_w + 2
        else:
            sx = cx - half_w - 2
        for dy in range(-2, 10):
            set_px(frame, sx, body_top + dy, stick_col)

    elif features == "scarf":
        # Colored scarf band at neck
        scarf_col = (0xff, 0xaa, 0x33, 255)
        for dx in range(-half_w, half_w + 1):
            set_px(frame, cx + dx, body_top, scarf_col)
            set_px(frame, cx + dx, body_top + 1, scarf_col)
        # Trailing end
        if direction == "left":
            set_px(frame, cx + half_w + 1, body_top + 1, scarf_col)
            set_px(frame, cx + half_w + 2, body_top + 2, scarf_col)
        elif direction == "right":
            set_px(frame, cx - half_w - 1, body_top + 1, scarf_col)
            set_px(frame, cx - half_w - 2, body_top + 2, scarf_col)
        else:
            set_px(frame, cx + half_w + 1, body_top + 1, scarf_col)
            set_px(frame, cx + half_w + 1, body_top + 2, scarf_col)

    elif features == "messy_hair":
        # Jagged pixels sticking up from head
        hair_a = darken(hair_col, 0.7) + (255,)
        spikes = [(-3, -2), (-1, -3), (1, -4), (3, -2), (0, -3), (2, -3)]
        for dx, dy in spikes:
            set_px(frame, cx + dx, head_cy - head_r + dy, hair_a)

    elif features == "tool_belt":
        # Lighter horizontal line at waist
        belt_col = lighten(body_col, 1.6) + (255,)
        belt_y = body_top + (body_bottom - body_top) * 2 // 3
        for dx in range(-half_w, half_w + 1):
            set_px(frame, cx + dx, belt_y, belt_col)
        # Small tool hanging
        tool_col = (0xaa, 0xaa, 0xaa, 255)
        set_px(frame, cx + half_w - 1, belt_y + 1, tool_col)
        set_px(frame, cx + half_w - 1, belt_y + 2, tool_col)

    elif features == "shawl_hunched":
        # Wider shoulders (shawl)
        shawl_col = lighten(body_col, 1.3) + (255,)
        for dx in range(-half_w - 2, half_w + 3):
            set_px(frame, cx + dx, body_top, shawl_col)
            set_px(frame, cx + dx, body_top + 1, shawl_col)
        # Slightly hunched: darken one shoulder side
        hunch = darken(body_col, 0.65) + (255,)
        for dy in range(2):
            set_px(frame, cx + half_w, body_top + dy, hunch)

    elif features == "bow_back":
        # Bow diagonal line on back
        bow_col = (0x8a, 0x7a, 0x5a, 255)
        if direction in ("down", "left", "right"):
            bx = cx + half_w + 1 if direction != "left" else cx - half_w - 1
            for i in range(5):
                set_px(frame, bx, body_top + 1 + i, bow_col)
            # Diagonal string
            set_px(frame, bx - 1, body_top, bow_col)
            set_px(frame, bx + 1, body_top + 6, bow_col)
        if direction == "up":
            # Bow visible on back
            for i in range(6):
                set_px(frame, cx, body_top + i, bow_col)
            set_px(frame, cx - 1, body_top - 1, bow_col)
            set_px(frame, cx + 1, body_top + 6, bow_col)

    elif features == "hat_backpack":
        # Wider top of head (hat)
        hat_col = body_col + (255,)
        hat_brim = darken(body_col, 0.7) + (255,)
        for dx in range(-head_r - 2, head_r + 3):
            set_px(frame, cx + dx, head_cy - head_r - 1, hat_brim)
        for dx in range(-head_r, head_r + 1):
            set_px(frame, cx + dx, head_cy - head_r - 2, hat_col)
            set_px(frame, cx + dx, head_cy - head_r - 3, hat_col)
        # Backpack bump on back
        bp_col = darken(body_col, 0.75) + (255,)
        if direction != "down":
            bx = cx + half_w + 1
            for dy in range(4):
                set_px(frame, bx, body_top + 2 + dy, bp_col)
                set_px(frame, bx + 1, body_top + 2 + dy, bp_col)

    elif features == "cape":
        # Flowing cape behind body
        cape_col = darken(body_col, 0.75) + (220,)
        cape_light = body_col + (200,)
        if direction == "up":
            # Cape fully visible from behind
            for dy in range(body_bottom - body_top + 3):
                width = min(half_w + 2, half_w + dy // 3 + 1)
                for dx in range(-width, width + 1):
                    py = body_top + dy
                    c = cape_light if dx == 0 else cape_col
                    set_px(frame, cx + dx, py, c)
        else:
            # Cape trailing to one side
            side = -1 if direction == "right" else 1
            for dy in range(body_bottom - body_top + 2):
                for i in range(2):
                    px = cx + side * (half_w + 1 + i)
                    py = body_top + dy
                    c = cape_light if i == 0 else cape_col
                    set_px(frame, px, py, c)
            # Flutter at bottom
            for i in range(3):
                set_px(frame, cx + side * (half_w + i), body_bottom + 1, cape_col)


# ===================================================================
# 3. ITEM ICONS (16x16)
# ===================================================================

def generate_item_icons():
    _gen_wood_icon()
    _gen_stone_icon()
    _gen_ore_icon()
    _gen_food_icon()
    _gen_herb_icon()
    _gen_rope_icon()
    _gen_potion_icon()
    _gen_tool_icon()
    _gen_bread_icon()
    _gen_gold_icon()


def _gen_wood_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    brown = (0x8B, 0x5E, 0x3C, 255)
    dark_brown = (0x5a, 0x3a, 0x1a, 255)
    ring_col = (0x6a, 0x4a, 0x2a, 255)
    # Log cross-section (circle)
    draw_circle_filled(draw, 8, 8, 6, brown)
    draw_circle_outline(draw, 8, 8, 6, dark_brown)
    # Tree rings
    draw_circle_outline(draw, 8, 8, 2, ring_col)
    draw_circle_outline(draw, 8, 8, 4, ring_col)
    # Center dot
    set_px(img, 8, 8, dark_brown)
    save(img, ICON_DIR / "wood.png")


def _gen_stone_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    gray = (0x7a, 0x7a, 0x7a, 255)
    dark = (0x4a, 0x4a, 0x4a, 255)
    light = (0x9a, 0x9a, 0x9a, 255)
    # Irregular rock shape
    points = [(3, 10), (2, 6), (5, 3), (10, 2), (13, 5), (14, 9), (11, 13), (6, 13)]
    draw.polygon(points, fill=gray, outline=dark)
    # Highlight on top
    draw.line([(5, 4), (10, 3)], fill=light)
    draw.line([(4, 5), (9, 4)], fill=light)
    save(img, ICON_DIR / "stone.png")


def _gen_ore_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    dark_gray = (0x4a, 0x4a, 0x50, 255)
    blue_crystal = (0x44, 0x88, 0xcc, 255)
    sparkle = (0xaa, 0xdd, 0xff, 255)
    # Rock base
    points = [(2, 12), (1, 7), (4, 4), (11, 3), (14, 7), (13, 12)]
    draw.polygon(points, fill=dark_gray, outline=(0x3a, 0x3a, 0x3a, 255))
    # Blue crystal facets
    crystal_pts = [(7, 2), (5, 6), (9, 6)]
    draw.polygon(crystal_pts, fill=blue_crystal)
    crystal_pts2 = [(10, 3), (8, 7), (12, 7)]
    draw.polygon(crystal_pts2, fill=lighten(blue_crystal, 1.1) + (255,))
    # Sparkle
    set_px(img, 7, 2, sparkle)
    set_px(img, 11, 4, sparkle)
    save(img, ICON_DIR / "ore.png")


def _gen_food_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    green = (0x4a, 0x8a, 0x2a, 255)
    stem = (0x6a, 0x9a, 0x3a, 255)
    gold = (0xcc, 0xaa, 0x33, 255)
    # Wheat stalk
    # Main stem
    for y in range(3, 15):
        set_px(img, 8, y, stem)
    # Grain kernels
    for i, dy in enumerate(range(2, 8)):
        side = 1 if i % 2 == 0 else -1
        set_px(img, 8 + side, 2 + dy, gold)
        set_px(img, 8 + side * 2, 2 + dy, gold)
    # Top grain
    set_px(img, 8, 2, gold)
    set_px(img, 7, 2, gold)
    set_px(img, 9, 2, gold)
    # Leaves
    set_px(img, 6, 10, green)
    set_px(img, 5, 11, green)
    set_px(img, 10, 9, green)
    set_px(img, 11, 10, green)
    save(img, ICON_DIR / "food.png")


def _gen_herb_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    green = (0x3a, 0x8a, 0x3a, 255)
    dark_green = (0x2a, 0x6a, 0x2a, 255)
    red = (0xcc, 0x33, 0x33, 255)
    # Leaf shape
    leaf_pts = [(8, 2), (4, 7), (6, 12), (8, 14), (10, 12), (12, 7)]
    draw.polygon(leaf_pts, fill=green, outline=dark_green)
    # Leaf vein
    for y in range(3, 13):
        set_px(img, 8, y, dark_green)
    # Red berries
    draw_circle_filled(draw, 5, 5, 1, red)
    draw_circle_filled(draw, 11, 5, 1, red)
    draw_circle_filled(draw, 8, 4, 1, red)
    save(img, ICON_DIR / "herb.png")


def _gen_rope_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rope = (0xaa, 0x8a, 0x4a, 255)
    rope_dark = (0x7a, 0x5a, 0x2a, 255)
    # Coiled rope (concentric arcs)
    draw_circle_outline(draw, 8, 8, 5, rope)
    draw_circle_outline(draw, 8, 8, 3, rope_dark)
    draw_circle_filled(draw, 8, 8, 1, rope)
    # Tail end
    set_px(img, 13, 8, rope)
    set_px(img, 14, 9, rope)
    set_px(img, 14, 10, rope_dark)
    save(img, ICON_DIR / "rope.png")


def _gen_potion_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bottle = (0x66, 0x44, 0xaa, 255)
    liquid = (0x88, 0x55, 0xcc, 255)
    cork = (0x8a, 0x6a, 0x4a, 255)
    glass = (0xaa, 0xbb, 0xcc, 180)
    highlight = (0xdd, 0xdd, 0xff, 200)
    # Bottle body
    draw.rectangle([5, 7, 10, 14], fill=glass)
    draw.rectangle([5, 8, 10, 14], fill=bottle)
    # Liquid fill
    draw.rectangle([6, 9, 9, 13], fill=liquid)
    # Neck
    draw.rectangle([7, 4, 8, 7], fill=glass)
    # Cork
    draw.rectangle([6, 3, 9, 4], fill=cork)
    # Highlight
    set_px(img, 6, 9, highlight)
    set_px(img, 6, 10, highlight)
    # Outline
    draw.rectangle([5, 7, 10, 14], outline=(0x33, 0x22, 0x66, 255))
    save(img, ICON_DIR / "potion.png")


def _gen_tool_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    metal = (0x88, 0x88, 0x99, 255)
    handle = (0x6a, 0x4a, 0x2a, 255)
    # Hammer head
    draw.rectangle([3, 3, 10, 6], fill=metal, outline=(0x55, 0x55, 0x66, 255))
    # Highlight on top
    draw.line([(4, 3), (9, 3)], fill=lighten(metal, 1.3) + (255,))
    # Handle
    draw.rectangle([7, 6, 8, 14], fill=handle, outline=darken(handle, 0.7) + (255,))
    save(img, ICON_DIR / "tool.png")


def _gen_bread_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bread = (0xcc, 0x99, 0x44, 255)
    crust = (0xaa, 0x77, 0x33, 255)
    highlight = (0xdd, 0xbb, 0x66, 255)
    # Bread loaf shape
    points = [(3, 12), (2, 8), (4, 5), (8, 4), (12, 5), (14, 8), (13, 12)]
    draw.polygon(points, fill=bread, outline=crust)
    # Score lines on top
    draw.line([(5, 6), (7, 5)], fill=crust)
    draw.line([(8, 5), (10, 6)], fill=crust)
    draw.line([(11, 6), (12, 7)], fill=crust)
    # Highlight
    draw.line([(5, 6), (11, 6)], fill=highlight)
    save(img, ICON_DIR / "bread.png")


def _gen_gold_icon():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    gold = (0xcc, 0xa8, 0x32, 255)
    gold_light = (0xff, 0xdd, 0x55, 255)
    gold_dark = (0x8a, 0x6a, 0x1a, 255)
    # Coin circle
    draw_circle_filled(draw, 8, 8, 6, gold)
    draw_circle_outline(draw, 8, 8, 6, gold_dark)
    # Inner ring
    draw_circle_outline(draw, 8, 8, 4, gold_dark)
    # Shine highlight
    set_px(img, 6, 5, gold_light)
    set_px(img, 7, 5, gold_light)
    set_px(img, 5, 6, gold_light)
    # Dollar/G symbol in center
    set_px(img, 8, 7, gold_dark)
    set_px(img, 8, 8, gold_dark)
    set_px(img, 8, 9, gold_dark)
    set_px(img, 7, 7, gold_dark)
    set_px(img, 9, 9, gold_dark)
    set_px(img, 7, 9, gold_dark)
    set_px(img, 9, 7, gold_dark)
    save(img, ICON_DIR / "gold.png")


# ===================================================================
# 4. FURNITURE (32x32)
# ===================================================================

def generate_furniture():
    _gen_bed()
    _gen_table()
    _gen_chair()


def _gen_bed():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    wood = (0x6a, 0x4a, 0x2a, 255)
    wood_dark = (0x4a, 0x2a, 0x1a, 255)
    blanket = (0x44, 0x66, 0xaa, 255)
    pillow = (0xee, 0xee, 0xdd, 255)
    # Bed frame (side view)
    # Headboard
    draw.rectangle([2, 6, 5, 24], fill=wood, outline=wood_dark)
    # Footboard
    draw.rectangle([26, 10, 29, 24], fill=wood, outline=wood_dark)
    # Frame bottom
    draw.rectangle([2, 22, 29, 24], fill=wood, outline=wood_dark)
    # Mattress
    draw.rectangle([5, 14, 26, 21], fill=(0xee, 0xdd, 0xcc, 255))
    # Blanket
    draw.rectangle([10, 14, 26, 20], fill=blanket,
                   outline=darken(blanket, 0.7) + (255,))
    # Pillow
    draw.rectangle([5, 14, 10, 18], fill=pillow,
                   outline=darken(pillow, 0.8) + (255,))
    # Legs
    draw.rectangle([3, 24, 5, 28], fill=wood_dark)
    draw.rectangle([27, 24, 29, 28], fill=wood_dark)
    save(img, ICON_DIR / "bed.png")


def _gen_table():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    wood = (0x7a, 0x5a, 0x3a, 255)
    wood_dark = (0x5a, 0x3a, 0x1a, 255)
    wood_light = (0x9a, 0x7a, 0x5a, 255)
    # Table top (front view)
    draw.rectangle([2, 10, 29, 13], fill=wood, outline=wood_dark)
    # Top surface highlight
    draw.line([(3, 10), (28, 10)], fill=wood_light)
    # Legs
    draw.rectangle([4, 13, 6, 28], fill=wood, outline=wood_dark)
    draw.rectangle([25, 13, 27, 28], fill=wood, outline=wood_dark)
    # Cross bar
    draw.rectangle([6, 20, 25, 21], fill=wood_dark)
    save(img, ICON_DIR / "table.png")


def _gen_chair():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    wood = (0x7a, 0x5a, 0x3a, 255)
    wood_dark = (0x5a, 0x3a, 0x1a, 255)
    seat_col = (0x8a, 0x6a, 0x4a, 255)
    # Back rest
    draw.rectangle([8, 3, 10, 18], fill=wood, outline=wood_dark)
    draw.rectangle([21, 3, 23, 18], fill=wood, outline=wood_dark)
    # Back slats
    draw.rectangle([10, 5, 21, 7], fill=wood, outline=wood_dark)
    draw.rectangle([10, 10, 21, 12], fill=wood, outline=wood_dark)
    # Seat
    draw.rectangle([6, 18, 25, 21], fill=seat_col, outline=wood_dark)
    # Front legs
    draw.rectangle([7, 21, 9, 29], fill=wood, outline=wood_dark)
    draw.rectangle([22, 21, 24, 29], fill=wood, outline=wood_dark)
    save(img, ICON_DIR / "chair.png")


# ===================================================================
# 5. RESOURCE OVERLAYS (32x32, semi-transparent)
# ===================================================================

def generate_resource_overlays():
    _gen_res_wood()
    _gen_res_stone()
    _gen_res_ore()
    _gen_res_food()
    _gen_res_herb()


def _gen_res_wood():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    brown = (0x6a, 0x4a, 0x2a, 180)
    dark = (0x4a, 0x2a, 0x1a, 180)
    ring = (0x5a, 0x3a, 0x1a, 180)
    # Tree stump
    draw.ellipse([8, 18, 24, 28], fill=brown, outline=dark)
    draw.ellipse([9, 14, 23, 20], fill=brown, outline=dark)
    # Rings on top
    draw_circle_outline(draw, 16, 17, 2, ring)
    draw_circle_outline(draw, 16, 17, 4, ring)
    set_px(img, 16, 17, dark)
    # Log pile next to stump
    draw.ellipse([2, 22, 8, 28], fill=brown, outline=dark)
    draw.ellipse([4, 20, 10, 26], fill=brown, outline=dark)
    save(img, ICON_DIR / "res_wood.png")


def _gen_res_stone():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    gray = (0x7a, 0x7a, 0x7a, 180)
    dark = (0x4a, 0x4a, 0x4a, 180)
    light = (0x9a, 0x9a, 0x9a, 180)
    # Stone pile: several overlapping rocks
    stones = [(6, 20, 10, 8), (14, 18, 12, 10), (22, 22, 8, 6), (10, 24, 14, 6)]
    for sx, sy, sw, sh in stones:
        c = gray if sw > 8 else dark
        draw.ellipse([sx, sy, sx + sw, sy + sh], fill=c, outline=dark)
        # Highlight
        draw.line([(sx + 2, sy + 1), (sx + sw - 2, sy + 1)], fill=light)
    save(img, ICON_DIR / "res_stone.png")


def _gen_res_ore():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rock = (0x4a, 0x4a, 0x50, 180)
    rock_dark = (0x3a, 0x3a, 0x3a, 180)
    blue = (0x44, 0x88, 0xcc, 180)
    sparkle = (0xaa, 0xdd, 0xff, 200)
    # Rock base
    pts = [(4, 28), (2, 18), (8, 14), (24, 14), (30, 18), (28, 28)]
    draw.polygon(pts, fill=rock, outline=rock_dark)
    # Blue crystal veins
    for x, y in [(10, 18), (16, 16), (22, 19), (14, 22)]:
        draw.polygon([(x, y - 3), (x - 2, y + 1), (x + 2, y + 1)], fill=blue)
    # Sparkle dots
    for x, y in [(10, 16), (18, 15), (24, 17), (12, 20)]:
        set_px(img, x, y, sparkle)
    save(img, ICON_DIR / "res_ore.png")


def _gen_res_food():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    green = (0x3a, 0x8a, 0x3a, 180)
    dark_green = (0x2a, 0x5a, 0x2a, 180)
    berry = (0xcc, 0x33, 0x55, 200)
    stem = (0x5a, 0x3a, 0x1a, 180)
    # Berry bush
    draw_circle_filled(draw, 16, 18, 8, green)
    draw_circle_filled(draw, 10, 20, 5, dark_green)
    draw_circle_filled(draw, 22, 20, 5, dark_green)
    # Berries
    for bx, by in [(13, 16), (19, 17), (16, 20), (11, 19), (21, 19)]:
        draw_circle_filled(draw, bx, by, 1, berry)
    # Stem / trunk
    draw.line([(16, 26), (16, 22)], fill=stem, width=2)
    save(img, ICON_DIR / "res_food.png")


def _gen_res_herb():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    green = (0x4a, 0x9a, 0x4a, 180)
    dark_green = (0x2a, 0x6a, 0x2a, 180)
    flower1 = (0xee, 0xaa, 0xdd, 200)
    flower2 = (0xee, 0xee, 0x55, 200)
    stem_col = (0x3a, 0x7a, 0x3a, 180)
    # Several herb stems with leaves
    stems = [(8, 28, 8, 12), (16, 28, 16, 10), (24, 28, 24, 14)]
    for x1, y1, x2, y2 in stems:
        draw.line([(x1, y1), (x2, y2)], fill=stem_col, width=1)
        # Leaves
        draw.polygon([(x2 - 3, y2 + 2), (x2, y2), (x2 + 3, y2 + 2)], fill=green)
        draw.polygon([(x2 - 2, y2 + 5), (x2, y2 + 3), (x2 + 2, y2 + 5)], fill=dark_green)
    # Small flowers
    draw_circle_filled(draw, 8, 11, 2, flower1)
    draw_circle_filled(draw, 16, 9, 2, flower2)
    draw_circle_filled(draw, 24, 13, 2, flower1)
    save(img, ICON_DIR / "res_herb.png")


# ===================================================================
# 6. PARTICLE TEXTURES
# ===================================================================

def generate_particles():
    _gen_rain_drop()
    _gen_snow_flake()
    _gen_storm_bolt()


def _gen_rain_drop():
    img = Image.new("RGBA", (2, 8), (0, 0, 0, 0))
    # White-blue gradient raindrop (top=bright, bottom=transparent)
    for y in range(8):
        alpha = int(255 * (1.0 - y / 8.0))
        blue = int(200 + 55 * (1.0 - y / 8.0))
        col = (220, 230, min(255, blue), alpha)
        set_px(img, 0, y, col)
        set_px(img, 1, y, col)
    save(img, PARTICLE_DIR / "rain_drop.png")


def _gen_snow_flake():
    img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    white = (255, 255, 255, 230)
    light = (220, 230, 255, 180)
    # Cross pattern
    set_px(img, 1, 0, light)
    set_px(img, 2, 0, light)
    set_px(img, 0, 1, light)
    set_px(img, 1, 1, white)
    set_px(img, 2, 1, white)
    set_px(img, 3, 1, light)
    set_px(img, 0, 2, light)
    set_px(img, 1, 2, white)
    set_px(img, 2, 2, white)
    set_px(img, 3, 2, light)
    set_px(img, 1, 3, light)
    set_px(img, 2, 3, light)
    save(img, PARTICLE_DIR / "snow_flake.png")


def _gen_storm_bolt():
    img = Image.new("RGBA", (8, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    yellow = (0xff, 0xff, 0x33, 255)
    bright = (0xff, 0xff, 0xcc, 255)
    # Lightning bolt shape
    bolt_pts = [
        (5, 0), (2, 6), (4, 6), (1, 12), (3, 12), (0, 16),
        (6, 9), (4, 9), (7, 3), (5, 3)
    ]
    draw.polygon(bolt_pts, fill=yellow, outline=bright)
    # Bright core
    core_pts = [(4, 2), (3, 5), (4, 5), (2, 10), (4, 7), (3, 7), (5, 4)]
    draw.polygon(core_pts, fill=bright)
    save(img, PARTICLE_DIR / "storm_bolt.png")


# ===================================================================
# 7. MOOD ICONS (16x16)
# ===================================================================

def generate_mood_icons():
    _gen_mood("mood_happy.png", (0x44, 0xaa, 0x44), "happy")
    _gen_mood("mood_neutral.png", (0xcc, 0xcc, 0x44), "neutral")
    _gen_mood("mood_sad.png", (0x44, 0x88, 0xcc), "sad")
    _gen_mood("mood_anxious.png", (0xdd, 0x88, 0x33), "anxious")
    _gen_mood("mood_angry.png", (0xcc, 0x33, 0x33), "angry")


def _gen_mood(filename, color, mood_type):
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    face_col = color + (255,)
    outline_col = darken(color, 0.6) + (255,)
    eye_col = (0x20, 0x20, 0x20, 255)
    # Face circle
    draw_circle_filled(draw, 8, 8, 6, face_col)
    draw_circle_outline(draw, 8, 8, 6, outline_col)
    # Eyes
    set_px(img, 5, 6, eye_col)
    set_px(img, 6, 6, eye_col)
    set_px(img, 10, 6, eye_col)
    set_px(img, 11, 6, eye_col)

    if mood_type == "happy":
        # Smile arc
        for x in range(5, 12):
            y_off = int(1.5 * math.sin((x - 5) * math.pi / 6))
            set_px(img, x, 10 + y_off, eye_col)
    elif mood_type == "neutral":
        # Straight line mouth
        for x in range(5, 12):
            set_px(img, x, 10, eye_col)
    elif mood_type == "sad":
        # Frown arc (inverted smile)
        for x in range(5, 12):
            y_off = -int(1.5 * math.sin((x - 5) * math.pi / 6))
            set_px(img, x, 11 + y_off, eye_col)
    elif mood_type == "anxious":
        # Wavy mouth
        for x in range(5, 12):
            y_off = int(math.sin((x - 5) * math.pi / 2) * 1)
            set_px(img, x, 10 + y_off, eye_col)
        # Worry lines above eyes
        set_px(img, 5, 4, outline_col)
        set_px(img, 6, 4, outline_col)
        set_px(img, 10, 4, outline_col)
        set_px(img, 11, 4, outline_col)
    elif mood_type == "angry":
        # Frown
        for x in range(5, 12):
            y_off = -int(1.0 * math.sin((x - 5) * math.pi / 6))
            set_px(img, x, 11 + y_off, eye_col)
        # Angry eyebrows (diagonal)
        set_px(img, 4, 4, eye_col)
        set_px(img, 5, 5, eye_col)
        set_px(img, 6, 5, eye_col)
        set_px(img, 10, 5, eye_col)
        set_px(img, 11, 5, eye_col)
        set_px(img, 12, 4, eye_col)

    save(img, UI_DIR / filename)


# ===================================================================
# 8. SEASON BADGES (32x32)
# ===================================================================

def generate_season_badges():
    _gen_season_spring()
    _gen_season_summer()
    _gen_season_autumn()
    _gen_season_winter()


def _gen_season_spring():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg = (0x88, 0xcc, 0x88, 255)
    earth = (0x6a, 0x4a, 0x2a, 255)
    green = (0x44, 0xaa, 0x44, 255)
    light_green = (0x66, 0xcc, 0x66, 255)
    stem = (0x44, 0x88, 0x33, 255)
    # Background circle
    draw_circle_filled(draw, 16, 16, 14, bg)
    draw_circle_outline(draw, 16, 16, 14, darken(bg, 0.7))
    # Earth/soil at bottom
    draw.rectangle([4, 20, 28, 28], fill=earth)
    # Sprout stem
    draw.line([(16, 20), (16, 10)], fill=stem, width=2)
    # Leaves
    leaf_pts_l = [(16, 13), (11, 10), (13, 14)]
    leaf_pts_r = [(16, 11), (21, 8), (19, 12)]
    draw.polygon(leaf_pts_l, fill=green)
    draw.polygon(leaf_pts_r, fill=light_green)
    # Tiny sprout bud at top
    draw_circle_filled(draw, 16, 9, 2, light_green)
    save(img, UI_DIR / "season_spring.png")


def _gen_season_summer():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg = (0x55, 0xaa, 0xdd, 255)
    sun = (0xff, 0xdd, 0x33, 255)
    sun_bright = (0xff, 0xee, 0x88, 255)
    cloud_dark = (0x55, 0x66, 0x77, 255)
    # Background circle
    draw_circle_filled(draw, 16, 16, 14, bg)
    draw_circle_outline(draw, 16, 16, 14, darken(bg, 0.7))
    # Sun
    draw_circle_filled(draw, 14, 12, 6, sun)
    draw_circle_filled(draw, 14, 12, 3, sun_bright)
    # Sun rays
    for angle_deg in range(0, 360, 45):
        rad = math.radians(angle_deg)
        for r in range(7, 10):
            x = int(14 + r * math.cos(rad))
            y = int(12 + r * math.sin(rad))
            set_px(img, x, y, sun + (255,) if len(sun) == 3 else sun)
    # Dark cloud edge (lower right)
    draw_circle_filled(draw, 22, 22, 5, cloud_dark)
    draw_circle_filled(draw, 18, 23, 4, cloud_dark)
    draw_circle_filled(draw, 26, 23, 3, cloud_dark)
    save(img, UI_DIR / "season_summer.png")


def _gen_season_autumn():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg = (0xcc, 0x88, 0x44, 255)
    leaf_orange = (0xdd, 0x66, 0x22, 255)
    leaf_red = (0xcc, 0x33, 0x22, 255)
    stem = (0x5a, 0x3a, 0x1a, 255)
    # Background circle
    draw_circle_filled(draw, 16, 16, 14, bg)
    draw_circle_outline(draw, 16, 16, 14, darken(bg, 0.7))
    # Falling leaf shape (maple-like)
    leaf_pts = [(16, 6), (10, 12), (12, 12), (8, 18), (12, 16),
                (14, 22), (16, 18), (18, 22), (20, 16), (24, 18),
                (20, 12), (22, 12)]
    draw.polygon(leaf_pts, fill=leaf_orange, outline=leaf_red)
    # Stem
    draw.line([(16, 6), (16, 3)], fill=stem, width=1)
    # Leaf veins
    draw.line([(16, 8), (12, 14)], fill=leaf_red, width=1)
    draw.line([(16, 8), (20, 14)], fill=leaf_red, width=1)
    draw.line([(16, 8), (16, 18)], fill=leaf_red, width=1)
    save(img, UI_DIR / "season_autumn.png")


def _gen_season_winter():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg = (0x44, 0x66, 0xaa, 255)
    white = (0xff, 0xff, 0xff, 255)
    light_blue = (0xcc, 0xdd, 0xff, 255)
    # Background circle
    draw_circle_filled(draw, 16, 16, 14, bg)
    draw_circle_outline(draw, 16, 16, 14, darken(bg, 0.7))
    # Snowflake - six-pointed with branches
    # Main axes
    for angle_deg in [0, 60, 120]:
        rad = math.radians(angle_deg)
        for r in range(-8, 9):
            x = int(16 + r * math.cos(rad))
            y = int(16 + r * math.sin(rad))
            set_px(img, x, y, white)
        # Small branches on each axis
        for sign in [-1, 1]:
            for br_dist in [4, 6]:
                bx = int(16 + sign * br_dist * math.cos(rad))
                by = int(16 + sign * br_dist * math.sin(rad))
                perp = rad + math.pi / 3 * sign
                for br in range(1, 3):
                    px = int(bx + br * math.cos(perp))
                    py = int(by + br * math.sin(perp))
                    set_px(img, px, py, light_blue)
    # Center dot
    draw_circle_filled(draw, 16, 16, 1, white)
    save(img, UI_DIR / "season_winter.png")


# ===================================================================
# 9. UI NINE-PATCH ELEMENTS
# ===================================================================

def generate_ui_elements():
    _gen_panel_bg()
    _gen_button("button_normal.png", (0x1a, 0x1a, 0x2e), (0x3a, 0x3a, 0x4e))
    _gen_button("button_hover.png", (0x2a, 0x2a, 0x3e), (0xc8, 0xa8, 0x32))
    _gen_button("button_pressed.png", (0x3a, 0x3a, 0x4e), (0xdd, 0xbb, 0x44))
    _gen_tarot_frame()


def _gen_panel_bg():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg = (0x14, 0x14, 0x1e, 255)
    border = (0x2a, 0x2a, 0x3e, 255)
    r = 6  # corner radius
    # Fill background with rounded corners
    draw.rounded_rectangle([0, 0, 63, 63], radius=r, fill=bg, outline=border)
    # Subtle inner shadow on edges
    inner = lighten((0x14, 0x14, 0x1e), 1.15) + (255,)
    draw.rounded_rectangle([1, 1, 62, 62], radius=r - 1, outline=inner)
    save(img, UI_DIR / "panel_bg.png")


def _gen_button(filename, bg_rgb, border_rgb):
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg = bg_rgb + (255,)
    border = border_rgb + (255,)
    # Rounded rectangle button
    draw.rounded_rectangle([0, 0, 31, 31], radius=4, fill=bg, outline=border)
    # Subtle top highlight
    highlight = lighten(bg_rgb, 1.3) + (255,)
    draw.line([(4, 1), (27, 1)], fill=highlight)
    # Subtle bottom shadow
    shadow = darken(bg_rgb, 0.7) + (255,)
    draw.line([(4, 30), (27, 30)], fill=shadow)
    save(img, UI_DIR / filename)


def _gen_tarot_frame():
    img = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    dark_bg = (0x0e, 0x0e, 0x14, 255)
    gold = (0xc8, 0xa8, 0x32, 255)
    gold_light = (0xdd, 0xcc, 0x66, 255)
    gold_dark = (0x8a, 0x6a, 0x1a, 255)
    # Outer frame
    draw.rounded_rectangle([0, 0, 63, 95], radius=4, fill=dark_bg, outline=gold)
    # Second border line (inner)
    draw.rounded_rectangle([2, 2, 61, 93], radius=3, outline=gold)
    # Ornate corners — small diamond shapes
    corners = [(6, 6), (57, 6), (6, 89), (57, 89)]
    for cx, cy in corners:
        for dx, dy in [(0, -2), (-1, -1), (0, -1), (1, -1),
                        (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
                        (-1, 1), (0, 1), (1, 1), (0, 2)]:
            set_px(img, cx + dx, cy + dy, gold_light)
    # Top/bottom center ornaments
    for mid_x in [32]:
        # Top
        for dx in range(-3, 4):
            set_px(img, mid_x + dx, 3, gold_light)
        set_px(img, mid_x, 4, gold_light)
        set_px(img, mid_x, 2, gold_light)
        # Bottom
        for dx in range(-3, 4):
            set_px(img, mid_x + dx, 92, gold_light)
        set_px(img, mid_x, 91, gold_light)
        set_px(img, mid_x, 93, gold_light)
    # Side ornaments at midpoint
    for mid_y in [48]:
        for dy in range(-3, 4):
            set_px(img, 1, mid_y + dy, gold_light)
            set_px(img, 62, mid_y + dy, gold_light)
    # Inner dark area (card face)
    draw.rectangle([5, 8, 58, 87], fill=dark_bg)
    # Very subtle inner border glow
    draw.rectangle([5, 8, 58, 87], outline=gold_dark)
    save(img, UI_DIR / "tarot_frame.png")


# ===================================================================
# MAIN
# ===================================================================

def main():
    ensure_dirs()
    random.seed(42)  # Reproducible output

    print("=" * 50)
    print("AgentHome Pixel Art Asset Generator")
    print("=" * 50)
    print(f"Output directory: {ART_DIR}\n")

    print("Generating terrain tiles...")
    generate_terrain_tiles()

    print("Generating character sprites...")
    generate_character_sprites()

    print("Generating item icons...")
    generate_item_icons()

    print("Generating furniture...")
    generate_furniture()

    print("Generating resource overlays...")
    generate_resource_overlays()

    print("Generating particles...")
    generate_particles()

    print("Generating mood icons...")
    generate_mood_icons()

    print("Generating season badges...")
    generate_season_badges()

    print("Generating UI elements...")
    generate_ui_elements()

    print(f"\nDone! Generated {FILE_COUNT} PNG files in {ART_DIR}")

    # Summary by directory
    for label, d in [("Tileset", TILESET_DIR), ("Characters", CHAR_DIR),
                     ("Icons", ICON_DIR), ("UI", UI_DIR), ("Particles", PARTICLE_DIR)]:
        count = len(list(d.glob("*.png")))
        print(f"  {label:12s}: {count} files  ({d})")


if __name__ == "__main__":
    main()
