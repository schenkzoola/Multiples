# Bill of Materials — Passive Multiple v1.0

A machine-readable copy is in [BOM.csv](BOM.csv). The original spreadsheet is [PassiveMultiples/BOM.ods](../PassiveMultiples/BOM.ods).

| Qty | Reference | Part | Manufacturer / Part No. | Notes |
|----:|-----------|------|--------------------------|-------|
| 8 | J1–J8 | 3.5 mm mono switched jack, vertical PCB mount, with nut | QingPu WQP-PJ398SM or WQP518MA, or equivalent. Either one works. | [Datasheet / product page](http://www.qingpu-electronics.com/en/products/WQP-PJ398SM-362.html). The switched (normalling) lug is not used. |
| 1 | SW1 | Pushbutton switch, DPDT, latching (push on, push off), PCB mount. It fits either way round. | APEM MHPS2285, or equivalent | [Digi-Key 679-4053-ND](https://www.digikey.com/product-detail/en/apem-inc/MHPS2285/679-4053-ND/1795385). Rated 0.1 A at 30 VDC. An equivalent must be a latching DPDT switch with the same 2 × 3 pin layout, and a plunger that fits the button cap. |
| 1 | — | Button cap, cylindrical, red | Tayda A-5390 (red, 6 × 5 mm) | [Tayda listing](https://www.taydaelectronics.com/push-button-switch-caps-red-color-6-x-5-mm-5390.html). Any cap that fits the MHPS2285 plunger and passes through the 6.5 mm panel hole will work. |
| 1 | — | Main PCB, 15 × 100 mm, 2-layer, 1.6 mm FR4 | Schenktronics | Gerbers: [PassiveMultiplesGerbers.zip](../PassiveMultiples/PassiveMultiplesGerbers.zip) |
| 1 | — | Faceplate, 3HP (15 × 128.5 mm), 1.6 mm aluminium PCB | Schenktronics | Single-sided, so it can also be made in FR4. Gerbers: [PassiveMultiplesFaceplateGerbers.zip](../PassiveMultiplesFaceplate/PassiveMultiplesFaceplateGerbers.zip) |

## Not included

| Qty | Part | Notes |
|----:|------|-------|
| 2 | M3 rack screws | Supplied with most Eurorack cases. |

No power cable is needed. The module is passive.
