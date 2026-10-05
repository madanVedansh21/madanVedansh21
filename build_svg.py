#!/usr/bin/env python3
"""
build_svg.py — Vedansh Madan's GitHub Profile SVG Generator
Generates dark_mode.svg and light_mode.svg with:
  - Left column: animated photo → ASCII art transition (CSS keyframes, no JS)
  - Right column: neofetch-style info panel with stat <tspan id="..."> placeholders
  
Run this locally when photo/ASCII/text changes.
today.py (on schedule) only refreshes stat IDs; never re-run build_svg.py in CI.

Credit: Architecture/stats-pipeline approach inspired by Andrew6rant's profile
(https://github.com/Andrew6rant/Andrew6rant) — adapted and rewritten for my own use.
"""

import base64
import html
import os
import sys
from pathlib import Path

# ── Optional Pillow for photo processing ──────────────────────────────────────
try:
    from PIL import Image, ImageOps, ImageEnhance
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent
# Accept .jpg or .png (PNG preferred when it exists — supports transparency)
_jpg = ROOT / "assets" / "photo.jpg"
_png = ROOT / "assets" / "photo.png"
# If user copied a PNG as photo.jpg, detect it by trying to open with Pillow
PHOTO_PATH  = _jpg  # resolved below in prepare_photo()
ASCII_PATH  = ROOT / "assets" / "ascii.txt"
DARK_OUT    = ROOT / "dark_mode.svg"
LIGHT_OUT   = ROOT / "light_mode.svg"

# ── Typography ────────────────────────────────────────────────────────────────
FONT_SIZE   = 13      # px  (monospace, left column)
LINE_HEIGHT = 16      # px  (vertical spacing between ASCII rows)
# Monospace char width ≈ 0.60 × font-size (with Consolas 109% size-adjust)
CHAR_WIDTH  = FONT_SIZE * 0.60

# ── Layout ────────────────────────────────────────────────────────────────────
PAD_LEFT    = 15      # left margin for ASCII block
PAD_TOP     = 30      # top  margin (first tspan y)
RIGHT_COL_X = 400     # x start of info panel
SVG_HEIGHT  = 540

# ── Animation timing ─────────────────────────────────────────────────────────
PHOTO_HOLD  = 3.0     # seconds photo is fully visible before fade starts
FADE_DUR    = 4.0     # seconds the photo fade takes
LINE_SPREAD = 4.0     # total seconds over which ASCII lines appear (scan effect)

# ── Photo target dimensions ───────────────────────────────────────────────────
MAX_PHOTO_W = 450     # px — resize to this width before base64 (keeps file small)
JPEG_QUAL   = 70      # JPEG quality (lower = smaller file)

# ── Themes ───────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":         "#161b22",
        "text":       "#c9d1d9",
        "key":        "#ffa657",
        "value":      "#a5d6ff",
        "add":        "#3fb950",
        "del":        "#f85149",
        "cc":         "#616e7f",
        "ascii_fill": "#c9d1d9",
        "header":     "#58a6ff",
    },
    "light": {
        "bg":         "#f6f8fa",
        "text":       "#24292f",
        "key":        "#953800",
        "value":      "#0550ae",
        "add":        "#116329",
        "del":        "#82071e",
        "cc":         "#8c959f",
        "ascii_fill": "#24292f",
        "header":     "#0969da",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_ascii():
    """Read ascii.txt, return list of lines (preserving spaces)."""
    with open(ASCII_PATH, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    # Strip trailing empty lines only
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def prepare_photo(block_w: int, block_h: int, bg_color: tuple = (22, 27, 34)) -> str:
    """
    Process the photo and return a base64-encoded JPEG data URI.
    Supports PNG with transparent background (composites onto bg_color).
    Falls back to empty string if photo doesn't exist or Pillow missing.
    bg_color: RGB tuple for compositing transparent pixels (default = dark theme bg).
    """
    # Resolve actual photo path — support PNG saved as photo.jpg
    photo_path = ROOT / "assets" / "photo.jpg"
    if not photo_path.exists():
        photo_path = ROOT / "assets" / "photo.png"
    if not photo_path.exists():
        print("[build_svg] WARNING: No photo found in assets/ — SVG will show ASCII only.")
        return ""

    if not HAS_PILLOW:
        print("[build_svg] WARNING: Pillow not installed — skipping photo embed.")
        return ""

    # Open, detect actual format regardless of extension
    img = Image.open(photo_path)
    fmt = img.format  # 'PNG', 'JPEG', etc.

    # Handle transparency: composite RGBA/P onto a solid background
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, bg_color + (255,))
        background.paste(img, mask=img.split()[3])   # use alpha as mask
        img = background.convert("RGB")
    else:
        img = img.convert("RGB")

    # Center-crop to match ASCII block aspect ratio
    target_ratio = block_w / block_h
    w, h = img.size
    current_ratio = w / h
    if current_ratio > target_ratio:
        # too wide — crop sides
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        # too tall — crop top/bottom (bias upward slightly for faces)
        new_h = int(w / target_ratio)
        top = max(0, int(h * 0.05))
        top = min(top, h - new_h)
        img = img.crop((0, top, w, top + new_h))

    # Resize: cap at MAX_PHOTO_W
    target_w = min(MAX_PHOTO_W, block_w * 2)
    target_h = int(target_w * block_h / block_w)
    img = img.resize((target_w, target_h), Image.LANCZOS)

    # Slight desaturation for terminal aesthetic
    img = ImageEnhance.Color(img).enhance(0.85)

    # Encode as JPEG
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUAL, optimize=True)
    enc = base64.b64encode(buf.getvalue()).decode()
    size_kb = len(enc) * 3 // 4 // 1024
    print(f"[build_svg] Photo encoded: ~{size_kb} KB  (source: {photo_path.name}, fmt: {fmt})")
    if size_kb > 150:
        print(f"[build_svg] WARNING: photo base64 is {size_kb} KB — consider reducing JPEG_QUAL or MAX_PHOTO_W.")
    return "data:image/jpeg;base64," + enc



def build_css(theme: dict, n_rows: int) -> str:
    """Return the <style> block for one SVG."""
    # Per-line animation delays: 3s hold + evenly spread over LINE_SPREAD seconds
    delay_rules = []
    for i in range(n_rows):
        delay = PHOTO_HOLD + (i * LINE_SPREAD / max(n_rows - 1, 1))
        delay_rules.append(f"  .al{i} {{ animation-delay: {delay:.2f}s; }}")
    delay_css = "\n".join(delay_rules)

    return f"""
@font-face {{
  src: local('Consolas'), local('Consolas Bold');
  font-family: 'ConsolasFallback';
  font-display: swap;
  -webkit-size-adjust: 109%;
  size-adjust: 109%;
}}
/* Colour roles */
.key   {{ fill: {theme['key']}; }}
.value {{ fill: {theme['value']}; }}
.add   {{ fill: {theme['add']}; }}
.del   {{ fill: {theme['del']}; }}
.cc    {{ fill: {theme['cc']}; }}
.hdr   {{ fill: {theme['header']}; font-weight: bold; }}
text, tspan {{ white-space: pre; }}

/* ── Photo → ASCII animation ───────────────────────────── */
.photo {{
  opacity: 1;
  animation: photoOut {FADE_DUR + PHOTO_HOLD}s ease-in-out forwards;
}}
@keyframes photoOut {{
  0%,  {int(PHOTO_HOLD / (FADE_DUR + PHOTO_HOLD) * 100)}% {{ opacity: 1; }}
  100% {{ opacity: 0; }}
}}

.ascii-line {{
  opacity: 0;
  animation: lineIn 1.1s ease-out forwards;
}}
@keyframes lineIn {{
  to {{ opacity: 1; }}
}}

{delay_css}

/* Accessibility: honour reduced-motion preference */
@media (prefers-reduced-motion: reduce) {{
  .photo      {{ animation: none; opacity: 0; }}
  .ascii-line {{ animation: none; opacity: 1; }}
}}
""".strip()


def build_left_col(lines: list, block_w: int, block_h: int, photo_b64: str,
                   theme: dict, pad_left: int, pad_top: int) -> str:
    """Return SVG markup for the animated left column."""
    parts = []

    # Photo layer (only if we have a photo)
    if photo_b64:
        parts.append(
            f'<image class="photo" '
            f'x="{pad_left}" y="{pad_top}" '
            f'width="{block_w}" height="{block_h}" '
            f'href="{photo_b64}" '
            f'xlink:href="{photo_b64}" '
            f'preserveAspectRatio="xMidYMid slice"/>'
        )

    # ASCII text layer
    parts.append(
        f'<text font-family="ConsolasFallback,Consolas,\'Courier New\',monospace" '
        f'font-size="{FONT_SIZE}px" fill="{theme["ascii_fill"]}" '
        f'xml:space="preserve">'
    )
    for i, line in enumerate(lines):
        y = pad_top + i * LINE_HEIGHT
        escaped = html.escape(line, quote=False)
        parts.append(
            f'  <tspan class="ascii-line al{i}" '
            f'x="{pad_left}" y="{y}">{escaped}</tspan>'
        )
    parts.append('</text>')

    return "\n".join(parts)


def dots(total_dots: int) -> str:
    """Return a dot-leader string of fixed length."""
    if total_dots <= 0:
        return " "
    return " " + ("." * total_dots) + " "


def build_right_col(theme: dict, rx: int) -> str:
    """Return the right-hand neofetch info panel SVG markup."""
    t = theme
    cc = 'class="cc"'
    kc = 'class="key"'
    vc = 'class="value"'
    hc = 'class="hdr"'

    # Helper: one info row
    def row(y, key, key2, dot_n, val_id, val_text, extra=""):
        k2 = f'.<tspan {kc}>{key2}</tspan>' if key2 else ""
        return (
            f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
            f'<tspan {kc}>{key}</tspan>{k2}:'
            f'<tspan {cc} id="{val_id}_dots">{dots(dot_n)}</tspan>'
            f'<tspan {vc} id="{val_id}">{val_text}</tspan>{extra}'
        )

    # ── Section separator ──────────────────────────────────────────────────
    sep_len = 44   # dash count to fill the right side
    def sep(y, label=""):
        dashes = "—" * (sep_len - len(label))
        return f'<tspan x="{rx}" y="{y}" fill="{t["header"]}">vedansh@madan</tspan> -{dashes}-'

    lines = []
    y = 30

    # Header
    lines.append(f'<text x="{rx}" y="{y}" fill="{t["text"]}">')
    lines.append(sep(y))
    y += 20

    # ── System ────────────────────────────────────────────────────────────
    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>OS</tspan>:'
        f'<tspan {cc}> ........................ </tspan>'
        f'<tspan {vc}>Windows 11, Linux, Android</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Uptime</tspan>:'
        f'<tspan {cc} id="age_data_dots"> ...................... </tspan>'
        f'<tspan {vc} id="age_data">20 years, 2 months, 0 days</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Host</tspan>:'
        f'<tspan {cc}> ......................... </tspan>'
        f'<tspan {vc}>IIIT Nagpur — CSE (2024–2028)</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Role</tspan>:'
        f'<tspan {cc}> ......................... </tspan>'
        f'<tspan {vc}>Full-Stack Developer · MERN · AI</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Work</tspan>:'
        f'<tspan {cc}> ......................... </tspan>'
        f'<tspan {vc}>Full-Stack Intern @ QuickIntell</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>IDE</tspan>:'
        f'<tspan {cc}> .......................... </tspan>'
        f'<tspan {vc}>VS Code · Cursor</tspan>'
    )
    y += 20

    # blank spacer
    lines.append(f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>')
    y += 20

    # ── Languages ─────────────────────────────────────────────────────────
    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Languages</tspan>.<tspan {kc}>Programming</tspan>:'
        f'<tspan {cc}> ...... </tspan>'
        f'<tspan {vc}>C++, JS, TS, Python</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Languages</tspan>.<tspan {kc}>Web</tspan>:'
        f'<tspan {cc}> ............... </tspan>'
        f'<tspan {vc}>React, Next.js, Tailwind</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Languages</tspan>.<tspan {kc}>Infra</tspan>:'
        f'<tspan {cc}> .............. </tspan>'
        f'<tspan {vc}>Docker, AWS, Nginx, Linux</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Languages</tspan>.<tspan {kc}>Real</tspan>:'
        f'<tspan {cc}> ............... </tspan>'
        f'<tspan {vc}>English, Hindi</tspan>'
    )
    y += 20

    # blank spacer
    lines.append(f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>')
    y += 20

    # ── Interests ─────────────────────────────────────────────────────────
    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Interests</tspan>.<tspan {kc}>Build</tspan>:'
        f'<tspan {cc}> ........... </tspan>'
        f'<tspan {vc}>Real-time systems, AI Agents</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Interests</tspan>.<tspan {kc}>Learn</tspan>:'
        f'<tspan {cc}> ........... </tspan>'
        f'<tspan {vc}>DSA, System Design, Blockchain</tspan>'
    )
    y += 20

    # ── Contact separator ─────────────────────────────────────────────────
    lines.append(
        f'<tspan x="{rx}" y="{y}" fill="{t["header"]}">- Contact </tspan>'
        f'-——————————————————————————————————————————-—-'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Email</tspan>:'
        f'<tspan {cc}> .......................... </tspan>'
        f'<tspan {vc}>vedanshmadan207@gmail.com</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>LinkedIn</tspan>:'
        f'<tspan {cc}> ..................... </tspan>'
        f'<tspan {vc}>vedansh-madan</tspan>'
    )
    y += 20

    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>GitHub</tspan>:'
        f'<tspan {cc}> ....................... </tspan>'
        f'<tspan {vc}>madanVedansh21</tspan>'
    )
    y += 20

    # ── GitHub Stats separator ────────────────────────────────────────────
    lines.append(
        f'<tspan x="{rx}" y="{y}" fill="{t["header"]}">- GitHub Stats </tspan>'
        f'-————————————————————————————————————————-—-'
    )
    y += 20

    # Repos + Stars
    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Repos</tspan>:'
        f'<tspan {cc} id="repo_data_dots"> .... </tspan>'
        f'<tspan {vc} id="repo_data">0</tspan>'
        f' {{<tspan {kc}>Contributed</tspan>: '
        f'<tspan {vc} id="contrib_data">0</tspan>}} | '
        f'<tspan {kc}>Stars</tspan>:'
        f'<tspan {cc} id="star_data_dots"> ... </tspan>'
        f'<tspan {vc} id="star_data">0</tspan>'
    )
    y += 20

    # Commits + Followers
    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Commits</tspan>:'
        f'<tspan {cc} id="commit_data_dots"> ............. </tspan>'
        f'<tspan {vc} id="commit_data">0</tspan>'
        f' | <tspan {kc}>Followers</tspan>:'
        f'<tspan {cc} id="follower_data_dots"> ...... </tspan>'
        f'<tspan {vc} id="follower_data">0</tspan>'
    )
    y += 20

    # LOC
    lines.append(
        f'<tspan x="{rx}" y="{y}" {cc}>. </tspan>'
        f'<tspan {kc}>Lines of Code</tspan>:'
        f'<tspan {cc} id="loc_data_dots"> .............. </tspan>'
        f'<tspan {vc} id="loc_data">0</tspan>'
        f' ( <tspan class="add" id="loc_add">0</tspan>'
        f'<tspan class="add">++</tspan>, '
        f'<tspan id="loc_del_dots"> </tspan>'
        f'<tspan class="del" id="loc_del">0</tspan>'
        f'<tspan class="del">--</tspan> )'
    )

    lines.append('</text>')
    return "\n".join(lines)


def build_svg(theme_name: str, lines: list, photo_b64: str) -> str:
    """Assemble and return the full SVG string."""
    theme = THEMES[theme_name]

    rows     = len(lines)
    cols     = max((len(l) for l in lines), default=40)
    block_w  = int(cols * CHAR_WIDTH)
    block_h  = rows * LINE_HEIGHT
    svg_w    = RIGHT_COL_X + 590   # total canvas width

    css       = build_css(theme, rows)
    left_col  = build_left_col(lines, block_w, block_h, photo_b64, theme,
                               PAD_LEFT, PAD_TOP)
    right_col = build_right_col(theme, RIGHT_COL_X)

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     font-family="ConsolasFallback,Consolas,monospace"
     width="{svg_w}px" height="{SVG_HEIGHT}px"
     font-size="{FONT_SIZE}px">
<style>
{css}
</style>
<rect width="{svg_w}px" height="{SVG_HEIGHT}px" fill="{theme['bg']}" rx="15"/>
{left_col}
{right_col}
</svg>"""


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("[build_svg] Loading ASCII art ...")
    lines = load_ascii()
    rows  = len(lines)
    cols  = max((len(l) for l in lines), default=40)
    block_w = int(cols * CHAR_WIDTH)
    block_h = rows * LINE_HEIGHT
    print(f"[build_svg] ASCII block: {rows} rows x {cols} cols -> {block_w}x{block_h} px")

    # Theme bg colors for PNG transparency compositing
    theme_bgs = {
        "dark":  (22,  27,  34),   # #161b22
        "light": (246, 248, 250),  # #f6f8fa
    }

    for theme_name, out_path in [("dark", DARK_OUT), ("light", LIGHT_OUT)]:
        print(f"[build_svg] Preparing photo for {theme_name} theme ...")
        photo_b64 = prepare_photo(block_w, block_h, bg_color=theme_bgs[theme_name])
        print(f"[build_svg] Building {theme_name}_mode.svg ...")
        svg = build_svg(theme_name, lines, photo_b64)
        out_path.write_text(svg, encoding="utf-8")
        size_kb = out_path.stat().st_size // 1024
        print(f"[build_svg]   -> {out_path.name}  ({size_kb} KB)")
        if size_kb > 500:
            print(f"[build_svg]   WARNING: File is over 500 KB — consider reducing photo size.")

    print("[build_svg] Done!")


if __name__ == "__main__":
    main()
