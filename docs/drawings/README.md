# Drawings

The panel drawing in the [user manual](../manual.md) ([`../images/panel.svg`](../images/panel.svg)) is generated from the KiCad faceplate file, [`PassiveMultiplesFaceplate.kicad_pcb`](../../PassiveMultiplesFaceplate/PassiveMultiplesFaceplate.kicad_pcb).

## Regenerating

After changing the faceplate in KiCad, run this from anywhere in the repo:

```sh
python3 docs/drawings/make_panel_svg.py
```

The script uses only the Python standard library.

## What it reads

| From the KiCad file | Used for |
|---------------------|----------|
| `Edge.Cuts` lines | Panel outline |
| Mounting-hole footprints and their drill sizes | Jacks (Ø6.0), the link button (Ø6.5) and the rack screw holes |
| `F.SilkS` lines, circles and text | Printed lines, the switch symbol and the labels |

The script tells holes apart by drill size, so if you change a hole size, update `JACK` and `SWITCH` at the top of the script. The "Bank A", "Bank B" and "Link button" labels are added by the script, not read from KiCad.
