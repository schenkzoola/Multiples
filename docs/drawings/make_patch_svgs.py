#!/usr/bin/env python3
"""Generate the patch-example drawings for the user manual.

Each example draws the panel (from the KiCad faceplate file) with source
modules on the left, destination modules on the right, and patch cables.

Writes docs/images/patch-*.svg.
Run from anywhere: python3 docs/drawings/make_patch_svgs.py
"""
from pathlib import Path

from make_panel_svg import FONT, INK, JACK, PCB, RED, SWITCH, panel_body, parse, svg

OUT = Path(__file__).resolve().parents[2] / "docs" / "images"

GREY = "#777"
BLUE = "#2a6fb0"  # second signal, for patches with two
BOX_W, BOX_H = 38, 11
GAP = 22  # space between the panel and the module boxes


def text(x, y, s, size=2.6, weight="normal", color=INK, anchor="middle"):
    return (f"<text x='{x:.2f}' y='{y:.2f}' {FONT} font-size='{size}' font-weight='{weight}' fill='{color}' "
            f"text-anchor='{anchor}' dominant-baseline='central'>{s}</text>")


def marker(color, name):
    return (f"<marker id='{name}' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='4' markerHeight='4' "
            f"orient='auto'><path d='M0 1 L10 5 L0 9 z' fill='{color}'/></marker>")


class Patch:
    def __init__(self, data):
        self.data = data
        outline, holes = data[0], data[1]
        self.x0, self.y0, self.x1, self.y1 = outline
        jacks = sorted(((x, y) for x, y, d in holes if d == JACK), key=lambda j: j[1])
        self.bank_a, self.bank_b = jacks[:4], jacks[4:]
        self.button = next((x, y) for x, y, d in holes if d == SWITCH)
        self.cables, self.boxes, self.plugs, self.notes = [], [], [], []

    def jack(self, name):
        bank, n = name[0], int(name[1:])
        return (self.bank_a if bank == "A" else self.bank_b)[n - 1]

    def box(self, side, y, title, sub):
        x = self.x0 - GAP - BOX_W if side == "left" else self.x1 + GAP
        self.boxes += [f"<rect x='{x}' y='{y - BOX_H / 2}' width='{BOX_W}' height='{BOX_H}' rx='1.2' "
                       f"fill='#fff' stroke='{INK}' stroke-width='0.35'/>",
                       text(x + BOX_W / 2, y - 2, title, 3.4, "bold"),
                       text(x + BOX_W / 2, y + 2.7, sub, 2.7, color=GREY)]
        return (x + BOX_W, y) if side == "left" else (x, y)

    def source(self, jack, title, sub, color=RED):
        jx, jy = self.jack(jack)
        bx, by = self.box("left", jy, title, sub)
        self.cable((bx, by), (jx, jy), color, into_jack=True)

    def dest(self, jack, title, sub, color=RED):
        jx, jy = self.jack(jack)
        bx, by = self.box("right", jy, title, sub)
        self.cable((jx, jy), (bx, by), color, into_jack=False)

    def cable(self, a, b, color, into_jack):
        (ax, ay), (bx, by) = a, b
        k = abs(bx - ax) * 0.5
        mid = "r" if color == RED else "b"
        end = "" if into_jack else f" marker-end='url(#{mid})'"
        self.cables.append(f"<path d='M{ax:.2f} {ay:.2f} C{ax + k:.2f} {ay:.2f} {bx - k:.2f} {by:.2f} {bx:.2f} {by:.2f}' "
                           f"fill='none' stroke='{color}' stroke-width='0.9' stroke-linecap='round'{end}/>")
        jx, jy = b if into_jack else a
        self.plugs.append(f"<circle cx='{jx}' cy='{jy}' r='2.3' fill='{color}' stroke='{INK}' stroke-width='0.3'/>")

    def button_note(self, label, sub):
        bx, by = self.button
        x = self.x0 - 3
        self.notes += [text(x, by - 1.8, label, 3.2, "bold", color=RED, anchor="end"),
                       text(x, by + 2.4, sub, 2.7, color=GREY, anchor="end")]

    def render(self, title):
        body = [f"<defs>{marker(RED, 'r')}{marker(BLUE, 'b')}</defs>"]
        body += panel_body(*self.data)
        body += self.cables + self.plugs + self.boxes + self.notes
        left = self.x0 - GAP - BOX_W - 3
        width = (self.x1 + GAP + BOX_W + 3) - left
        return svg((left, self.y0 - 3, width, (self.y1 - self.y0) + 6), body, title)


def clock(data):
    p = Patch(data)
    p.source("A1", "Clock", "out")
    p.dest("A2", "Kick", "trigger in")
    p.dest("A3", "Snare", "trigger in")
    p.dest("B1", "Hi-hat", "trigger in")
    p.dest("B2", "Sequencer", "clock in")
    p.button_note("Button in", "banks linked")
    return p.render("Patch example: one clock to four modules")


def pitch(data):
    p = Patch(data)
    p.source("A1", "Sequencer", "pitch CV out")
    p.dest("A2", "VCO 1", "V/oct in")
    p.dest("A3", "VCO 2", "V/oct in")
    p.dest("A4", "VCO 3", "V/oct in")
    p.button_note("Button out", "Bank B stays free")
    return p.render("Patch example: pitch to three oscillators")


def mute(data):
    p = Patch(data)
    p.source("A1", "Drum voice", "audio out")
    p.dest("B1", "Mixer", "channel in")
    p.button_note("Press in time", "in = on, out = muted")
    return p.render("Patch example: performance mute")


def split(data):
    p = Patch(data)
    p.source("A1", "Clock", "out", color=RED)
    p.dest("A2", "Drum 1", "trigger in", color=RED)
    p.dest("A3", "Drum 2", "trigger in", color=RED)
    p.source("B1", "LFO", "out", color=BLUE)
    p.dest("B2", "Filter", "cutoff CV in", color=BLUE)
    p.dest("B3", "VCA", "CV in", color=BLUE)
    p.button_note("Button out", "banks split")
    return p.render("Patch example: two separate multiples")


def main():
    data = parse(PCB)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fig in (("patch-1-clock.svg", clock), ("patch-2-pitch.svg", pitch),
                      ("patch-3-mute.svg", mute), ("patch-4-split.svg", split)):
        (OUT / name).write_text(fig(data))
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
