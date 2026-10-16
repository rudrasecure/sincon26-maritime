# Register cheat-sheet (partial)

This is the **read side** of each controller: the registers that tell you what the
ship is and what it is doing. It is deliberately partial. The **command** registers,
the ones that *do* things, you discover yourself, because learning to find a control
by its behaviour is the transferable skill at these stations. The register viewers and
your own reads give you everything you need to do that.

Everything below is a **holding register** (Modbus function code `0x03` to read,
`0x06` / `0x10` to write). Values are 16-bit. Some are signed (noted).

---

## Ballast controller: `10.71.30.10:5021`

**Asset block (reads).** HR **200-225**: device class, serial, firmware, year, running
hours, redundancy, then the rated plate (tanks, pumps, capacities).

**Live telemetry (reads):**

| HR | Meaning |
|---|---|
| 0-7 | Tank levels, %: FPT, APT, DB1P, DB1S, DB2P, DB2S, WBTP, WBTS (in that order) |
| 10, 11 | Ballast pump 1 / 2 running (0/1) |
| 12 | **List (heel) angle**, 0.1 deg signed (port negative, starboard positive) |
| 13 | Trim angle, 0.1 deg signed (positive by the bow) |
| 20-25 | Alarms (0/1): list>2, list>5, list>15, tank high, pump 1 fault, pump 2 fault |

**Commands.** There is a block of command registers higher in the map (think
**500-ish**). The cheat-sheet stops here on purpose: find which register does what by
writing one and watching the telemetry above react. This gauging system carries an
**independent safety channel** separate from the tank gauges; keep that fact in your
pocket for when something stops you.

---

## Engine (propulsion) controller: `10.71.20.10:5020`

**Asset block (reads).** HR **200-221**: device class, serial, firmware, then the rated
plate (MCR/NCR power and rpm, cylinders, bore, stroke, propeller).

**Live telemetry (reads):**

| HR | Meaning |
|---|---|
| 0 | Main engine speed, rpm |
| 1 | Shaft power, kW |
| 2 | Fuel rack / index |
| 3 | Exhaust temperature, degC |
| 4 | Lube-oil pressure |
| 6 | Cooling-water temperature, degC |
| 7 | Main engine running (0/1) |
| 8 | Engine load, % |
| 20-27 | Alarms (0/1): overspeed, LO low-pressure trip, exhaust high, CW high, emergency-stopped, steering faults |

**Commands.** Again a command block higher in the map (around **500**). Find the one
that sets engine speed by consequence: write it, watch HR 0 follow. And remember for
Task B: you can make a *displayed* value read whatever you like, but the safety unit is
a separate box reading its own sensor. Fooling the screen is not fooling the trip.

---

### Reading registers without the viewer

Use pymodbus directly (the same library the viewers use), or any Modbus tool:

```python
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient("10.71.30.10", port=5021)
c.connect()
print(c.read_holding_registers(0, count=14).registers)   # ballast telemetry
c.close()
```
