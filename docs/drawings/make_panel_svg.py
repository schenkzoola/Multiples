#!/usr/bin/env python3
"""Generate faceplate line drawings from the KiCad faceplate file.

Writes docs/images/panel.svg (annotated front view).
Run from anywhere: python3 docs/drawings/make_panel_svg.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "PassiveMultiplesFaceplate" / "PassiveMultiplesFaceplate.kicad_pcb"
OUT = ROOT / "docs" / "images"

INK = "#1a1a1a"
DIM = "#555"
RED = "#d9302c"
FONT = "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'"

# Drill sizes (mm) that identify each kind of hole.
JACK, SWITCH = 6.0, 6.5


def parse(path):
    s = path.read_text()
    edges = [tuple(map(float, m)) for m in re.findall(
        r"\(gr_line \(start ([\d.]+) ([\d.]+)\) \(end ([\d.]+) ([\d.]+)\) \(layer Edge\.Cuts\)", s)]
    xs = [v for e in edges for v in (e[0], e[2])]
    ys = [v for e in edges for v in (e[1], e[3])]
    outline = (min(xs), min(ys), max(xs), max(ys))

    holes = []
    for m in re.finditer(r"\(module Mounting_Holes:\S+.*?\(at ([\d.]+) ([\d.]+)\).*?\(drill ([\d.]+)\)", s, re.S):
        holes.append((float(m[1]), float(m[2]), float(m[3])))

    silk_lines = [(tuple(map(float, m[:4])), float(m[4])) for m in re.findall(
        r"\(gr_line \(start ([\d.]+) ([\d.]+)\) \(end ([\d.]+) ([\d.]+)\) \(layer F\.SilkS\) \(width ([\d.]+)\)", s)]
    silk_circles = [tuple(map(float, m)) for m in re.findall(
        r"\(gr_circle \(center ([\d.]+) ([\d.]+)\) \(end ([\d.]+) ([\d.]+)\) \(layer F\.SilkS\) \(width ([\d.]+)\)", s)]
    texts = []
    for m in re.finditer(r"\(gr_text (\S+) \(at ([\d.]+) ([\d.]+)(?: ([\d.]+))?\) \(layer F\.SilkS\)"
                         r"(.*?)\n  \)", s, re.S):
        size = re.search(r"\(size ([\d.]+)", m[5])
        justify = re.search(r"\(justify (\w+)", m[5])
        texts.append(dict(text=m[1], x=float(m[2]), y=float(m[3]), rot=float(m[4] or 0),
                          size=float(size[1]), justify=justify and justify[1]))
    return outline, holes, silk_lines, silk_circles, texts


def panel_body(outline, holes, silk_lines, silk_circles, texts):
    """SVG elements for the faceplate itself, in board coordinates (mm)."""
    x0, y0, x1, y1 = outline
    el = [f"<rect x='{x0}' y='{y0}' width='{x1 - x0}' height='{y1 - y0}' rx='0.4' "
          f"fill='#fff' stroke='{INK}' stroke-width='0.3'/>"]
    for (xa, ya, xb, yb), w in silk_lines:
        el.append(f"<line x1='{xa}' y1='{ya}' x2='{xb}' y2='{yb}' stroke='{INK}' "
                  f"stroke-width='{w}' stroke-linecap='round'/>")
    for cx, cy, ex, ey, w in silk_circles:
        r = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
        el.append(f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{INK}' stroke-width='{w}'/>")
    for t in texts:
        anchor = "start" if t["justify"] == "left" else "middle"
        rot = f" transform='rotate({-t['rot']} {t['x']} {t['y']})'" if t["rot"] else ""
        el.append(f"<text x='{t['x']}' y='{t['y']}' {FONT} font-size='{t['size'] * 1.15}' "
                  f"font-weight='bold' fill='{INK}' text-anchor='{anchor}' dominant-baseline='central'{rot}>"
                  f"{t['text']}</text>")
    for x, y, d in holes:
        if d == JACK:
            # Knurled jack nut with the socket opening.
            el.append(f"<circle cx='{x}' cy='{y}' r='3.9' fill='#fff' stroke='{INK}' stroke-width='0.35'/>")
            el.append(f"<circle cx='{x}' cy='{y}' r='3.1' fill='none' stroke='{INK}' stroke-width='0.2'/>")
            el.append(f"<circle cx='{x}' cy='{y}' r='1.8' fill='{INK}'/>")
        elif d == SWITCH:
            el.append(f"<circle cx='{x}' cy='{y}' r='2.25' fill='{RED}' stroke='{INK}' stroke-width='0.3'/>")
        else:
            el.append(f"<circle cx='{x}' cy='{y}' r='{d / 2}' fill='#fff' stroke='{INK}' stroke-width='0.3'/>")
    return el


def svg(view, body, title):
    vx, vy, vw, vh = view
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='{vx} {vy} {vw} {vh}' "
            f"width='{vw * 4:.0f}' height='{vh * 4:.0f}'>\n<title>{title}</title>\n"
            f"<rect x='{vx}' y='{vy}' width='{vw}' height='{vh}' fill='#fff'/>\n"
            + "\n".join(body) + "\n</svg>\n")


def annotated(outline, holes, *silk):
    x0, y0, x1, y1 = outline
    body = panel_body(outline, holes, *silk)
    jacks = sorted(y for _, y, d in holes if d == JACK)
    switch_y = next(y for _, y, d in holes if d == SWITCH)
    bank_a, bank_b = jacks[:4], jacks[4:]
    bx = x1 + 4

    def bracket(ys, label):
        top, bot = ys[0] - 3, ys[-1] + 3
        mid = (top + bot) / 2
        return [f"<path d='M{bx - 1.5} {top} H{bx} V{bot} H{bx - 1.5}' fill='none' stroke='{DIM}' stroke-width='0.3'/>",
                f"<text x='{bx + 2.5}' y='{mid}' {FONT} font-size='3.2' font-weight='bold' fill='{INK}' "
                f"dominant-baseline='central'>{label}</text>",
                f"<text x='{bx + 2.5}' y='{mid + 4.5}' {FONT} font-size='2.4' fill='{DIM}' "
                f"dominant-baseline='central'>4 jacks, wired together</text>"]

    body += bracket(bank_a, "Bank A")
    body += bracket(bank_b, "Bank B")
    body += [f"<line x1='{x1 - 4.5}' y1='{switch_y}' x2='{bx}' y2='{switch_y}' stroke='{DIM}' stroke-width='0.3'/>",
             f"<circle cx='{x1 - 4.5}' cy='{switch_y}' r='0.5' fill='{DIM}'/>",
             f"<text x='{bx + 2.5}' y='{switch_y}' {FONT} font-size='3.2' font-weight='bold' fill='{INK}' "
             f"dominant-baseline='central'>Link button</text>",
             f"<text x='{bx + 2.5}' y='{switch_y + 4.5}' {FONT} font-size='2.4' fill='{DIM}' "
             f"dominant-baseline='central'>in = linked, out = split</text>"]
    pad = 4
    return svg((x0 - pad, y0 - pad, (x1 - x0) + 46 + pad, (y1 - y0) + 2 * pad), body,
               "Passive Multiple front panel")


def main():
    data = parse(PCB)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "panel.svg").write_text(annotated(*data))
    print("wrote", OUT / "panel.svg")


if __name__ == "__main__":
    main()
