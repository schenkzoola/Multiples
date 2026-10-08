#!/usr/bin/env python3
"""Generate faceplate line drawings from the KiCad faceplate file.

Writes docs/images/panel.svg (annotated front view) and docs/images/panel-plain.svg
(the panel alone, for packaging labels where small captions would be lost).
Run from anywhere: python3 docs/drawings/make_panel_svg.py

The faceplate file is KiCad's S-expression format (KiCad 10: footprints, nested
stroke/effects blocks, quoted layer names). Parsed with a small generic
S-expression reader rather than ad hoc regexes, since graphics like the logo
live inside a footprint and need its position and rotation applied.
"""
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "hardware" / "panel" / "PassiveMultiplesFaceplate.kicad_pcb"
OUT = ROOT / "docs" / "images"

INK = "#1a1a1a"
DIM = "#555"
RED = "#d9302c"
FONT = "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'"

# Drill sizes (mm) that identify each kind of hole.
JACK, SWITCH = 6.0, 6.5

# Footprints that carry the Schenktronics wordmark as silkscreen polygons.
LOGO_FOOTPRINT = "SchentronicsLogo"


def read_sexp(text):
    """Parse a KiCad S-expression file into nested lists of strings."""
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)

    def parse(pos):
        items = []
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == "(":
                node, pos = parse(pos + 1)
                items.append(node)
            elif tok == ")":
                return items, pos + 1
            else:
                items.append(tok[1:-1] if tok.startswith('"') else tok)
                pos += 1
        return items, pos

    node, _ = parse(1)  # skip the opening paren of (kicad_pcb ...)
    return node


def tagged(node, name):
    """Direct children of node that are lists starting with `name`."""
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def first(node, name):
    found = tagged(node, name)
    return found[0] if found else None


def at_xyr(node):
    a = first(node, "at")
    vals = [float(v) for v in a[1:]] if a else []
    while len(vals) < 3:
        vals.append(0.0)
    return tuple(vals[:3])


def stroke_width(node):
    s = first(node, "stroke")
    w = first(s, "width") if s else None
    return float(w[1]) if w else 0.2


def parse(path):
    root = read_sexp(path.read_text())

    edges = []
    for e in tagged(root, "gr_line"):
        if first(e, "layer") and first(e, "layer")[1] == "Edge.Cuts":
            sx, sy = (float(v) for v in first(e, "start")[1:])
            ex, ey = (float(v) for v in first(e, "end")[1:])
            edges.append((sx, sy, ex, ey))
    xs = [v for e in edges for v in (e[0], e[2])]
    ys = [v for e in edges for v in (e[1], e[3])]
    outline = (min(xs), min(ys), max(xs), max(ys))

    holes = []
    for fp in tagged(root, "footprint"):
        if "Mounting_Holes" in fp[1]:
            x, y, _ = at_xyr(fp)
            pad = first(fp, "pad")
            holes.append((x, y, float(first(pad, "drill")[1])))

    silk_lines = []
    for e in tagged(root, "gr_line"):
        layer = first(e, "layer")
        if layer and layer[1] == "F.SilkS":
            sx, sy = (float(v) for v in first(e, "start")[1:])
            ex, ey = (float(v) for v in first(e, "end")[1:])
            silk_lines.append(((sx, sy, ex, ey), stroke_width(e)))

    silk_circles = []
    for c in tagged(root, "gr_circle"):
        layer = first(c, "layer")
        if layer and layer[1] == "F.SilkS":
            cx, cy = (float(v) for v in first(c, "center")[1:])
            ex, ey = (float(v) for v in first(c, "end")[1:])
            silk_circles.append((cx, cy, ex, ey, stroke_width(c)))

    texts = []
    for t in tagged(root, "gr_text"):
        layer = first(t, "layer")
        if not (layer and layer[1] == "F.SilkS"):
            continue
        x, y, rot = at_xyr(t)
        effects = first(t, "effects")
        font = first(effects, "font")
        size = float(first(font, "size")[1])
        justify = first(effects, "justify")
        italic = first(font, "italic") is not None
        texts.append(dict(text=t[1], x=x, y=y, rot=rot, size=size,
                          justify=justify[1] if justify else None, italic=italic))

    logo_polys = []
    for fp in tagged(root, "footprint"):
        if LOGO_FOOTPRINT not in fp[1]:
            continue
        ox, oy, orot = at_xyr(fp)
        theta = math.radians(orot)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        for poly in tagged(fp, "fp_poly"):
            layer = first(poly, "layer")
            if not (layer and layer[1] == "F.SilkS"):
                continue
            pts = []
            for xy in tagged(first(poly, "pts"), "xy"):
                lx, ly = float(xy[1]), float(xy[2])
                # KiCad rotates footprints clockwise for positive angles.
                bx = ox + lx * cos_t + ly * sin_t
                by = oy - lx * sin_t + ly * cos_t
                pts.append((bx, by))
            logo_polys.append(pts)

    return outline, holes, silk_lines, silk_circles, texts, logo_polys


def panel_body(outline, holes, silk_lines, silk_circles, texts, logo_polys):
    """SVG elements for the faceplate itself, in board coordinates (mm)."""
    x0, y0, x1, y1 = outline
    el = [f"<rect x='{x0}' y='{y0}' width='{x1 - x0}' height='{y1 - y0}' rx='0.4' "
          f"fill='#fff' stroke='{INK}' stroke-width='0.3'/>"]
    for pts in logo_polys:
        el.append(f"<polygon points='{' '.join(f'{x},{y}' for x, y in pts)}' fill='{INK}'/>")
    for (xa, ya, xb, yb), w in silk_lines:
        el.append(f"<line x1='{xa}' y1='{ya}' x2='{xb}' y2='{yb}' stroke='{INK}' "
                  f"stroke-width='{w}' stroke-linecap='round'/>")
    for cx, cy, ex, ey, w in silk_circles:
        r = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
        el.append(f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='{INK}' stroke-width='{w}'/>")
    for t in texts:
        anchor = "start" if t["justify"] == "left" else "middle"
        rot = f" transform='rotate({-t['rot']} {t['x']} {t['y']})'" if t["rot"] else ""
        style = " font-style='italic'" if t["italic"] else ""
        el.append(f"<text x='{t['x']}' y='{t['y']}' {FONT} font-size='{t['size'] * 1.15}'{style} "
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


def plain(outline, holes, *silk):
    x0, y0, x1, y1 = outline
    pad = 1
    return svg((x0 - pad, y0 - pad, (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad), panel_body(outline, holes, *silk),
               "Passive Multiple front panel")


def main():
    data = parse(PCB)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "panel.svg").write_text(annotated(*data))
    (OUT / "panel-plain.svg").write_text(plain(*data))
    print("wrote", OUT / "panel.svg", "and", OUT / "panel-plain.svg")


if __name__ == "__main__":
    main()
