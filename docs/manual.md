# Passive Multiple — User Manual

<img src="images/front.jpg" alt="Passive Multiple front panel" width="120">

## Overview

The Passive Multiple is a 3HP Eurorack utility module with eight jacks in two banks of four. All jacks in a bank are wired together, so one signal in a bank goes out of the other three jacks. The red button links the two banks, making one 8-jack multiple.

The module has no electronics beyond the jacks and the switch, so it does not need power.

## Specifications

| | |
|---|---|
| Format | Eurorack, 3HP |
| Panel | 15 × 128.5 mm |
| Depth | About the height of the jacks (skiff-friendly) |
| Power | None needed |
| Jacks | 8 × 3.5 mm mono (TS) |
| Switch | Latching push-on/push-off button (in = linked), rated 0.1 A / 30 VDC |

## Panel layout

<img src="images/panel.svg" alt="Panel layout: Bank A on top, the link button in the middle, Bank B below" width="300">

The lines printed on the panel show the connections: jacks joined by a line are wired together, and the switch symbol between the banks is the link button.

## Using the module

### Split mode (button out)

You get two separate 1-in, 3-out multiples. Patch one source into any jack in a bank and take copies from the other three jacks.

### Linked mode (button in)

All eight jacks are wired together, giving you 1 in and 7 out.

### Link button

The button is latching (push on, push off). When it is **in**, the banks are linked. When it is **out**, they are split.

### Using the button as a performance switch

The link button can also be played live. Patch a signal into Bank A and take it out of Bank B. The button then turns that signal on and off. Press it in time with the music to drop a part in and out, mute a modulation source, or cut a clock or gate stream.

You can do this while still using both banks as multiples. Any other jacks in Bank A always carry the signal. The jacks in Bank B only carry it while the button is in.

When the button is out, the Bank B jacks aren't connected to anything, so the modules patched from them get no signal. With audio, you may hear a small click when you switch. The switch changes sharply, so it works best on rhythmic material.

### Signals in any direction

The jacks have no set inputs or outputs, so any jack works as either. You can also use a bank backwards: connect several inputs to one output, or connect one cable to a cable that is too short.

## Good practice

- **Use one output per bank.** Connecting two module outputs to the same bank (or to linked banks) shorts them together. Most Eurorack outputs have protection resistors and survive this, but the signal you get is meaningless. It is also the most common patching mistake with a multiple.
- **Pitch CV (V/oct):** A passive multiple has no buffering. Most inputs have high impedance, so the load is small, but spreading one pitch CV across many oscillators can drop the voltage slightly and put them a little out of tune. If tuning matters, use a buffered multiple or check the tuning after patching.
- **Audio and gates** work fine through a passive multiple.
- **Grounds:** the sleeves of all eight jacks are wired together, in both modes.

## Installation

1. Power off your case. The module does not need power, but you should never work in a powered case.
2. Place the module in any 3HP space. There is no ribbon cable to connect.
3. Secure it with two M3 rack screws. Do not overtighten them.

## Circuit

Each jack's tip is wired to the other tips in its bank, and all sleeves are wired together. The two poles of the switch are wired in parallel between the Bank A tips and the Bank B tips. The schematic is in [PassiveMultiples/PassiveMultiples.sch](../PassiveMultiples/PassiveMultiples.sch) (KiCad 5).
