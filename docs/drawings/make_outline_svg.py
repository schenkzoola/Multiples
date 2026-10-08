#!/usr/bin/env python3
"""Generate mechanical outline drawings straight from the assembly STEP file.

Unlike the other drawing scripts, this one needs the `cadquery` package
(`pip install cadquery`) — there's no stdlib way to compute hidden-line
removal (HLR) on real 3D geometry. See docs/drawings/README.md.

These are true projections of the assembled module (panel, PCB, jacks and
switch together), not diagrams: an HLR pass works out which edges of the
real STEP geometry are visible from a given direction and emits them as
vector paths, which we then simplify and restyle to match the house look.

Writes docs/images/outline-front.svg, outline-side.svg, one
outline-iso-{top,bottom}-{left,right}.svg per corner — all four corners are
generated every time, so there's always a fresh set to pick a hero shot
from, not just whichever one is currently wired into the docs (today:
outline-iso-top-left.svg) — and outline-bare-parts.svg (the panel and the
bare, unpopulated board side by side, for the assembly guide's "what you
have before you start" shot).
Run from anywhere: python3 docs/drawings/make_outline_svg.py
(or name one view to render just that one, e.g. ... outline-front.svg)

Things to know before changing a view:

1. The front view looks straight down all 8 jacks' own barrel axis (and
   the panel's holes, coaxial with them) — a textbook degenerate case for
   exact-BRep HLR, where OCCT's visibility tie-breaking between surfaces
   that are exactly parallel/coincident from that viewpoint becomes
   unreliable. It showed up as a different jack missing its inner circle,
   or doubling a ring line, or missing its outer ring, depending on what
   was tried — never a difference in the actual geometry, confirmed by
   isolating any single jack + the panel, which always rendered correctly.

   What did NOT reliably fix it: nudging the orthographic projection
   direction off-axis by a tiny tilt. A tilt breaks *some* of the exact
   ties, but which ones depends on the magnitude in a way that doesn't
   converge — a value that fixed one jack would leave another broken, and
   a bigger value fixed that one while breaking a third. Several rounds of
   this did not find one tilt that fixed all 8 at once.

   What DID fix it, reliably, in one pass: a PERSPECTIVE projection
   instead of orthographic (`focus` below — see `export_hlr`), with its
   apex centered on the model. Perspective rays genuinely diverge from a
   point rather than running exactly parallel, which removes the
   coincidence orthographic projection has at every point in the frame,
   not just approximately at one tilt angle. A large focus distance
   (`FRONT_FOCUS_MM`, about 75x the model's own size here) keeps the
   visible perspective distortion negligible — it should look like a
   straight-on front view, not a wide-angle product shot.

   The apex MUST be centered on the model (at its own bounding-box
   center), not at the STEP file's coordinate origin — this assembly's
   origin is nowhere near the part (geometry sits around x=157, y=-90,
   not x=y=0). An off-center apex looks at the model from an angle even
   though the projection *direction* is still straight down an axis,
   which showed up as a part of the PCB's edge peeking out past one side
   of the panel but not the other (real parallax from the off-axis
   viewpoint, not a bug, but also not what a straight-on view should show,
   and a giveaway that the apex is in the wrong place).

   A tempting-looking shortcut that quietly breaks: isolating each jack +
   the panel, rendering 9 small HLR calls (8 jacks + the switch)
   separately, and compositing by assigning each a Y-slice of the panel.
   This works for the geometry's sake (every jack really does render
   identically in isolation) but throws away the panel's silkscreen text
   and logo, which aren't modeled as solids at all — they only survive if
   the panel's own top-level sub-assembly is kept intact, never rebuilt
   from an extracted solid list. Getting that composite fully correct
   (panel sub-assembly kept raw, jack/switch solids grouped by position)
   worked, but it's much more code than just fixing the projection, and an
   earlier attempt at it silently shipped jacks with no knurl detail for
   a review cycle before that was caught. Perspective projection needs
   none of this — it runs over the real, unmodified, full assembly.

2. This is real geometric computation, not a quick export, and it does NOT
   scale predictably with geometry size or projection type. The exact-axis
   orthographic front view took 24 minutes over the full assembly; the
   perspective version of the same view, same direction, same assembly,
   took under a minute. Oblique (side, isometric) orthographic views of
   the same assembly also take about a minute. Time a new view on a copy
   before assuming any of this carries over to a different model.

3. We set the HLR projector's reference axis explicitly (`export_hlr`
   below) instead of using cadquery's default exporter. cadquery's
   `cq.exporters.export` lets OCCT auto-pick that axis, and it picks
   inconsistently across directions — negating just the Y component of a
   working `projectionDir` silently mirrored the panel's silkscreen text
   backwards in testing. Always setting an explicit `up` vector avoids
   that regardless of which direction you project from.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSEMBLY = ROOT / "hardware" / "ST01_Multiple.step"
OUT = ROOT / "docs" / "images"

INK = "#1a1a1a"
PAD = 2.0  # mm of white space kept around the content on each side

# A number pattern that includes scientific notation (e.g. "1.23e-05").
# cadquery/OCCT emit coordinates in whatever form Python's float-to-str
# produces, which switches to this form for very small magnitudes — the
# perspective projection below produces plenty of those, since it's
# centered on the model rather than the STEP file's own (distant) origin.
# A plain "-?\d+\.?\d*" pattern silently mis-tokenizes those (splits the
# exponent off as a second bogus number), desyncing every x/y pair after
# the first one it hits — not a crash, just quietly wrong coordinates.
NUM = r"-?\d+\.?\d*(?:[eE][+-]?\d+)?"

# Max deviation (mm) allowed when simplifying HLR curve polylines. cadquery
# discretizes curves to 0.001 mm, far finer than needed for a doc image;
# 0.02 mm cuts file size by 4-5x with no visible difference (checked at
# normal embed sizes) since it's still way below print/screen resolution.
SIMPLIFY_TOLERANCE = 0.02

# How far away the perspective "camera" sits for the front view, in mm —
# about 75x the model's own size, which keeps distortion low enough to
# read as a straight-on view. See point 1 in the module docstring for why
# this needs to be perspective at all. Only the front view needs it; the
# side and isometric views aren't axis-aligned onto repeated coaxial
# parts, so they don't hit the same degenerate case.
FRONT_FOCUS_MM = 10000.0

# (projectionDir, up) for each view. `up` only has to be roughly vertical in
# screen space; it's made orthogonal to the direction automatically. Keeping
# it the same (0,1,0) for every view is what makes the HLR axis consistent
# (see the module docstring) and is also what lets `flip_y` below be a
# constant instead of something re-derived per direction.
VIEWS = {
    "outline-front.svg": dict(projectionDir=(0, 0, 1), focus=FRONT_FOCUS_MM, title="Passive Multiple — front view"),
    "outline-side.svg": dict(projectionDir=(1, 0.00005, 0.0001), title="Passive Multiple — side view"),
    "outline-iso-top-left.svg": dict(projectionDir=(-1, 1, 1), title="Passive Multiple — isometric, top-left"),
    "outline-iso-top-right.svg": dict(projectionDir=(1, 1, 1), title="Passive Multiple — isometric, top-right"),
    "outline-iso-bottom-left.svg": dict(projectionDir=(-1, -1, 1), title="Passive Multiple — isometric, bottom-left"),
    "outline-iso-bottom-right.svg": dict(projectionDir=(1, -1, 1), title="Passive Multiple — isometric, bottom-right"),
    # Special-cased in render_one(): built from bare_parts_paths(), not a
    # single export_hlr() call, so projectionDir here is just the viewing
    # direction passed through to that function, not a VIEWS-style lookup.
    "outline-bare-parts.svg": dict(projectionDir=(0, 0, 1), title="Passive Multiple — panel and bare PCB"),
}

# Which isometric corner is actually used in the docs right now (the others
# are still generated every run — see the module docstring).
CHOSEN_ISO = "outline-iso-top-left.svg"


def export_hlr(shape, direction, focus=None, up=(0, 1, 0)):
    """Visible-edge paths (raw mm coordinates) for `shape` seen from
    `direction`, with an explicitly fixed screen-up vector and the
    projector centered on the shape's own bounding box.

    Centering matters even for the plain orthographic views (harmless
    there, parallel rays don't care where the origin is) but is required
    once `focus` makes this a perspective projection — an off-center apex
    looks at the model from an angle no matter what `direction` says. See
    point 1 in the module docstring.
    """
    from cadquery.occ_impl.exporters.svg import makeSVGedge
    from cadquery.occ_impl.shapes import Shape, TOLERANCE
    from OCP.BRepLib import BRepLib
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

    bb = shape.BoundingBox()
    origin = gp_Pnt((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2)

    n = gp_Vec(*direction).Normalized()
    u = gp_Vec(*up)
    right = u.Crossed(n)
    if right.Magnitude() < 1e-9:
        raise ValueError("direction parallel to up vector")
    right.Normalize()

    ax2 = gp_Ax2(origin, gp_Dir(n.X(), n.Y(), n.Z()), gp_Dir(right.X(), right.Y(), right.Z()))
    projector = HLRAlgo_Projector(ax2, focus) if focus else HLRAlgo_Projector(ax2)

    hlr = HLRBRep_Algo()
    hlr.Add(shape.wrapped)
    hlr.Projector(projector)
    hlr.Update()
    hlr.Hide()

    hlr_shapes = HLRBRep_HLRToShape(hlr)
    visible = []
    for getter in (hlr_shapes.VCompound, hlr_shapes.Rg1LineVCompound, hlr_shapes.OutLineVCompound):
        c = getter()
        if not c.IsNull():
            visible.append(c)
    for el in visible:
        BRepLib.BuildCurves3d_s(el, TOLERANCE)

    return [makeSVGedge(e) for s in map(Shape, visible) for e in s.Edges()]


# Used only by bare_parts_paths(), below: how far apart (mm) to place the
# panel and the bare board when shown side by side, in place of the old
# "PCB and faceplate" photo in the assembly guide.
BARE_PARTS_GAP_MM = 8.0


def bare_parts_paths(shape, direction):
    """Front view of the panel and the bare (unpopulated) PCB board, side
    by side — what a builder actually has in hand before assembly, since
    the main view shows the fully populated module. Both come straight out
    of the same assembly STEP, each with no coaxial-jack view to go
    degenerate on (no jacks are installed in either), so this is a single
    ordinary HLR pass per part, no perspective trick needed.

    The two parts keep their real relative Y position from the assembly
    (only the board is shifted sideways, in X, to sit next to the panel)
    rather than being centered independently — this is what lines their
    jack positions up vertically, same as they'd align once assembled.
    """
    from cadquery.occ_impl.shapes import Shape
    from OCP.TopoDS import TopoDS_Builder, TopoDS_Compound, TopoDS_Iterator

    it = TopoDS_Iterator(shape.wrapped)
    top_children = []
    while it.More():
        top_children.append(it.Value())
        it.Next()
    panel_child = min(top_children, key=lambda c: abs(Shape(c).BoundingBox().ylen - 128.5))
    panel_shape = Shape(panel_child)

    # The bare board substrate plus its two copper/mask layers — matches
    # the standalone Multiple.kicad_pcb board outline, no components.
    all_solids = shape.Solids()
    board_solids = [s for s in all_solids if abs(s.BoundingBox().ylen - 100.0) < 0.1
                    and abs(s.BoundingBox().xlen - 15.0) < 0.1 and s.BoundingBox().zlen < 2]
    builder = TopoDS_Builder()
    comp = TopoDS_Compound()
    builder.MakeCompound(comp)
    for s in board_solids:
        builder.Add(comp, s.wrapped)
    board_shape = Shape(comp)

    shift_x = panel_shape.BoundingBox().xmax - board_shape.BoundingBox().xmin + BARE_PARTS_GAP_MM

    merged = export_hlr(panel_shape, direction)
    for d in export_hlr(board_shape, direction):
        nums = re.findall(NUM, d)
        pts = [(float(nums[i]) + shift_x, float(nums[i + 1])) for i in range(0, len(nums), 2)]
        merged.append(" ".join(("M" if i == 0 else "L") + f"{x:.3f},{y:.3f}" for i, (x, y) in enumerate(pts)))
    return merged


def rdp(points, eps):
    """Ramer-Douglas-Peucker polyline simplification."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5
    best_i, best_d = 0, -1.0
    for i, (x, y) in enumerate(points[1:-1], 1):
        d = (abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm if norm else
             ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5)
        if d > best_d:
            best_d, best_i = d, i
    if best_d <= eps:
        return [points[0], points[-1]]
    return rdp(points[:best_i + 1], eps)[:-1] + rdp(points[best_i:], eps)


def finish_svg(raw_paths, title, scale=6, flip_y=True):
    """Simplify the raw edge paths and lay them out in an SVG cropped
    tightly to content (viewBox in real mm, 1 unit = 1 mm)."""
    all_pts = []
    parsed = []
    for d in raw_paths:
        nums = re.findall(NUM, d)
        pts = [(float(nums[i]), float(nums[i + 1])) for i in range(0, len(nums), 2)]
        pts = rdp(pts, SIMPLIFY_TOLERANCE)
        if flip_y:
            pts = [(x, -y) for x, y in pts]
        parsed.append(pts)
        all_pts.extend(pts)

    xs, ys = [p[0] for p in all_pts], [p[1] for p in all_pts]
    xmin, xmax = min(xs) - PAD, max(xs) + PAD
    ymin, ymax = min(ys) - PAD, max(ys) + PAD
    vw, vh = xmax - xmin, ymax - ymin

    body = [f"<path d='{' '.join(('M' if i == 0 else 'L') + f'{x:.3f},{y:.3f}' for i, (x, y) in enumerate(pts))}'/>"
            for pts in parsed]

    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='{xmin:.2f} {ymin:.2f} {vw:.2f} {vh:.2f}' "
            f"width='{vw * scale:.0f}' height='{vh * scale:.0f}'>\n<title>{title}</title>\n"
            f"<rect x='{xmin:.2f}' y='{ymin:.2f}' width='{vw:.2f}' height='{vh:.2f}' fill='#fff'/>\n"
            f"<g stroke='{INK}' stroke-width='0.1' fill='none'>\n" + "\n".join(body) + "\n</g>\n</svg>\n")


def render_one(name):
    """Render a single named view. Invoked as a subprocess by main() so that
    OCCT's per-process state (it has shown signs of corruption across
    repeated HLR passes in one process — a crash partway through a batch
    run) can never take out any view but the one it was computing."""
    import cadquery as cq

    v = VIEWS[name]
    shape = cq.importers.importStep(str(ASSEMBLY)).val()
    if name == "outline-bare-parts.svg":
        paths = bare_parts_paths(shape, v["projectionDir"])
    else:
        paths = export_hlr(shape, v["projectionDir"], focus=v.get("focus"))
    svg = finish_svg(paths, v["title"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(svg)
    print("wrote", OUT / name)


def main():
    if len(sys.argv) > 1:
        render_one(sys.argv[1])
        return

    failures = []
    for name, v in VIEWS.items():
        print(f"rendering {name} (projectionDir={v['projectionDir']})...")
        result = subprocess.run([sys.executable, __file__, name])
        if result.returncode != 0:
            print(f"  FAILED (exit {result.returncode}) — leaving any existing {name} untouched")
            failures.append(name)
    if failures:
        print("\nFailed views:", ", ".join(failures))
        print("Re-run with just that name, e.g.:")
        print(f"  python3 {Path(__file__).name} {failures[0]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
