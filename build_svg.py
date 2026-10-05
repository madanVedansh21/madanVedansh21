#!/usr/bin/env python3
"""
build_svg.py — Vedansh Madan's GitHub Profile SVG Generator
Generates dark_mode.svg and light_mode.svg with:
  - Left column: ASCII art (static, neofetch style)
  - Right column: neofetch-style info panel with stat <tspan id="..."> placeholders

Run this locally when ASCII/text changes.
today.py (on schedule) refreshes stat IDs only.

Credit: Architecture/stats-pipeline inspired by Andrew6rant's profile
(https://github.com/Andrew6rant/Andrew6rant) — adapted for my own use.
"""

import html
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent
ASCII_PATH = ROOT / "assets" / "ascii.txt"
DARK_OUT   = ROOT / "dark_mode.svg"
LIGHT_OUT  = ROOT / "light_mode.svg"

# ── Typography ────────────────────────────────────────────────────────────────
FONT_SIZE   = 14      # px (larger, clearer)
LINE_HEIGHT = 18      # px (spacious, crisp)
CHAR_WIDTH  = FONT_SIZE * 0.601   # Consolas monospace ratio

# ── Layout ────────────────────────────────────────────────────────────────────
PAD_X       = 18      # left padding for ASCII block
PAD_Y       = 28      # top of first line (y of first tspan)
COL_GAP     = 25      # gap between ASCII block right edge and info panel

# ── Themes ───────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":     "#161b22",
        "text":   "#c9d1d9",
        "key":    "#ffa657",
        "value":  "#a5d6ff",
        "add":    "#3fb950",
        "del":    "#f85149",
        "cc":     "#616e7f",
        "header": "#58a6ff",
        "ascii":  "#c9d1d9",   # high-contrast bright white/gray (crystal clear)
    },
    "light": {
        "bg":     "#f6f8fa",
        "text":   "#24292f",
        "key":    "#953800",
        "value":  "#0550ae",
        "add":    "#116329",
        "del":    "#82071e",
        "cc":     "#8c959f",
        "header": "#0969da",
        "ascii":  "#24292f",   # high-contrast dark charcoal (crystal clear)
    },
}


def load_ascii():
    with open(ASCII_PATH, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    # Crop excessive empty outer @ padding (cols 9 to 67 = 58 columns)
    # This brings the portrait into full focus, making it much larger and clearer!
    cropped = []
    for line in lines:
        if len(line) >= 67:
            cropped.append(line[9:67])
        else:
            cropped.append(line)
    return cropped


def build_ascii_col(lines, theme, x, y):
    """SVG markup for the static ASCII left column."""
    parts = [
        f'<text font-family="ConsolasFallback,Consolas,\'Courier New\',monospace" '
        f'font-size="{FONT_SIZE}px" fill="{theme["ascii"]}" '
        f'xml:space="preserve">'
    ]
    for i, line in enumerate(lines):
        ty = y + i * LINE_HEIGHT
        escaped = html.escape(line, quote=False)
        parts.append(f'  <tspan x="{x}" y="{ty}">{escaped}</tspan>')
    parts.append('</text>')
    return "\n".join(parts)


def dots(n):
    if n <= 0:
        return " "
    return " " + ("." * n) + " "


def build_info_col(theme, rx, start_y):
    """SVG markup for the right-hand neofetch info panel."""
    t = theme
    cc  = f'fill="{t["cc"]}"'
    kc  = f'fill="{t["key"]}"'
    vc  = f'fill="{t["value"]}"'
    tc  = f'fill="{t["text"]}"'
    hc  = f'fill="{t["header"]}"'

    LH = LINE_HEIGHT   # line height alias
    y  = start_y
    out = [f'<text font-family="ConsolasFallback,Consolas,\'Courier New\',monospace" font-size="{FONT_SIZE}px" xml:space="preserve">']

    def ln(markup):
        nonlocal y
        out.append(f'  <tspan x="{rx}" y="{y}">{markup}</tspan>')
        y += LH

    def blank():
        nonlocal y
        out.append(f'  <tspan x="{rx}" y="{y}"> </tspan>')
        y += LH

    # ── Header ──────────────────────────────────────────────────────────────
    ln(f'<tspan {hc}>vedansh@madan</tspan>'
       f'<tspan {cc}> --------------------------------</tspan>')

    # ── System info ─────────────────────────────────────────────────────────
    ln(f'<tspan {cc}>. </tspan><tspan {kc}>OS</tspan>'
       f'<tspan {cc}> ................... </tspan>'
       f'<tspan {vc}>Windows 11, Linux, Android</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Uptime</tspan>'
       f'<tspan {cc} id="age_data_dots"> ................ </tspan>'
       f'<tspan {vc} id="age_data">20 years, 4 months, 15 days</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Host</tspan>'
       f'<tspan {cc}> ................. </tspan>'
       f'<tspan {vc}>IIIT Nagpur — CSE (2024–2028)</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Role</tspan>'
       f'<tspan {cc}> ................. </tspan>'
       f'<tspan {vc}>Full-Stack Dev · MERN · AI</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Work</tspan>'
       f'<tspan {cc}> ................. </tspan>'
       f'<tspan {vc}>Ex-Full Stack Intern @ QuickIntell</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>IDE</tspan>'
       f'<tspan {cc}> .................. </tspan>'
       f'<tspan {vc}>VS Code · Cursor</tspan>')

    blank()

    # ── Languages ────────────────────────────────────────────────────────────
    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Lang.Prog</tspan>'
       f'<tspan {cc}> ............ </tspan>'
       f'<tspan {vc}>C++, JS, TS, Python</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Lang.Web</tspan>'
       f'<tspan {cc}> ............. </tspan>'
       f'<tspan {vc}>React, Next.js, Tailwind</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Lang.Infra</tspan>'
       f'<tspan {cc}> ........... </tspan>'
       f'<tspan {vc}>Docker, AWS, Nginx, Linux</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Lang.Real</tspan>'
       f'<tspan {cc}> ............ </tspan>'
       f'<tspan {vc}>English, Hindi</tspan>')

    blank()

    # ── Interests ────────────────────────────────────────────────────────────
    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Build</tspan>'
       f'<tspan {cc}> ................ </tspan>'
       f'<tspan {vc}>Real-Time Systems, AI Agents</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Learn</tspan>'
       f'<tspan {cc}> ................ </tspan>'
       f'<tspan {vc}>DSA, System Design, Scalable Systems</tspan>')

    blank()

    # ── Contact ──────────────────────────────────────────────────────────────
    ln(f'<tspan {hc}>- Contact </tspan>'
       f'<tspan {cc}>--------------------------</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Email</tspan>'
       f'<tspan {cc}> ............... </tspan>'
       f'<tspan {vc}>vedanshmadan207@gmail.com</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>LinkedIn</tspan>'
       f'<tspan {cc}> ............ </tspan>'
       f'<tspan {vc}>vedansh-madan</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>GitHub</tspan>'
       f'<tspan {cc}> .............. </tspan>'
       f'<tspan {vc}>madanVedansh21</tspan>')

    blank()

    # ── GitHub Stats ─────────────────────────────────────────────────────────
    ln(f'<tspan {hc}>- GitHub Stats </tspan>'
       f'<tspan {cc}>---------------------</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Repos</tspan>'
       f'<tspan {cc} id="repo_data_dots"> .... </tspan>'
       f'<tspan {vc} id="repo_data">0</tspan>'
       f'<tspan {cc}> {{</tspan><tspan {kc}>Contrib</tspan><tspan {cc}>: </tspan>'
       f'<tspan {vc} id="contrib_data">0</tspan><tspan {cc}>}}</tspan>'
       f'<tspan {cc}> | </tspan><tspan {kc}>Stars</tspan>'
       f'<tspan {cc} id="star_data_dots"> .. </tspan>'
       f'<tspan {vc} id="star_data">0</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Commits</tspan>'
       f'<tspan {cc} id="commit_data_dots"> .......... </tspan>'
       f'<tspan {vc} id="commit_data">0</tspan>'
       f'<tspan {cc}> | </tspan><tspan {kc}>Followers</tspan>'
       f'<tspan {cc} id="follower_data_dots"> .... </tspan>'
       f'<tspan {vc} id="follower_data">0</tspan>')

    ln(f'<tspan {cc}>. </tspan><tspan {kc}>Lines of Code</tspan>'
       f'<tspan {cc} id="loc_data_dots"> ........ </tspan>'
       f'<tspan {vc} id="loc_data">0</tspan>'
       f'<tspan {cc}> ( </tspan>'
       f'<tspan fill="{t["add"]}" id="loc_add">0</tspan>'
       f'<tspan fill="{t["add"]}">++</tspan>'
       f'<tspan {cc}>, </tspan>'
       f'<tspan id="loc_del_dots"> </tspan>'
       f'<tspan fill="{t["del"]}" id="loc_del">0</tspan>'
       f'<tspan fill="{t["del"]}">--</tspan>'
       f'<tspan {cc}> )</tspan>')

    out.append('</text>')
    return "\n".join(out), y   # return y so we know total height used


def build_svg(theme_name, lines):
    theme = THEMES[theme_name]

    rows   = len(lines)
    cols   = max((len(l) for l in lines), default=40)
    asc_w  = int(cols * CHAR_WIDTH)          # pixel width of ASCII block
    asc_h  = rows * LINE_HEIGHT              # pixel height of ASCII block

    right_x = PAD_X + asc_w + COL_GAP       # x start of info panel
    right_w = 460                            # fixed width for info panel
    svg_w   = right_x + right_w + PAD_X     # total SVG width
    svg_h   = max(asc_h + PAD_Y + 20, 560)  # at least 560px tall

    ascii_svg = build_ascii_col(lines, theme, PAD_X, PAD_Y)
    info_svg, info_bottom = build_info_col(theme, right_x, PAD_Y)

    svg_h = max(svg_h, info_bottom + 20)

    return f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     font-family="ConsolasFallback,Consolas,monospace"
     width="{svg_w}px" height="{svg_h}px"
     font-size="{FONT_SIZE}px">
<style>
@font-face {{
  src: local('Consolas'), local('Consolas Bold');
  font-family: 'ConsolasFallback';
  font-display: swap;
  size-adjust: 109%;
  -webkit-size-adjust: 109%;
}}
text, tspan {{ white-space: pre; }}
</style>
<rect width="{svg_w}px" height="{svg_h}px" fill="{theme['bg']}" rx="15"/>
{ascii_svg}
{info_svg}
</svg>"""


def main():
    print("[build_svg] Loading ASCII art...")
    lines = load_ascii()
    rows  = len(lines)
    cols  = max((len(l) for l in lines), default=40)
    asc_w = int(cols * CHAR_WIDTH)
    asc_h = rows * LINE_HEIGHT
    print(f"[build_svg] ASCII block: {rows} rows x {cols} cols -> {asc_w}x{asc_h} px")

    for theme_name, out_path in [("dark", DARK_OUT), ("light", LIGHT_OUT)]:
        print(f"[build_svg] Building {theme_name}_mode.svg...")
        svg = build_svg(theme_name, lines)
        out_path.write_text(svg, encoding="utf-8")
        size_kb = out_path.stat().st_size // 1024
        print(f"[build_svg]   -> {out_path.name}  ({size_kb} KB)")

    print("[build_svg] Done!")


if __name__ == "__main__":
    main()
