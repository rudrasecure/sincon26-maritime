#!/usr/bin/env python3
"""
engine_probe.py: Kampung engine station starter (read-only).

Connects to the propulsion controller, fingerprints it, and shows its nameplate and
live telemetry, then points you where to start. It never writes.

    python3 engine_probe.py 10.71.20.10
    python3 engine_probe.py 10.71.20.10:5020
    python3 engine_probe.py 10.71.20.10 --map

Needs pymodbus (pip install pymodbus). The IP comes from the Ship OT Bridge Wi-Fi
(docs/CONNECT.md); the port is 5020.
"""
import sys

import probe
from probe import u32

PORT = 5020

STATUS = [(0, "engine speed", "rpm"), (1, "shaft power", "kW"), (2, "fuel index", "raw"),
          (3, "exhaust temp", "degC"), (4, "lube-oil pressure", "raw"),
          (6, "cooling water", "degC"), (8, "engine load", "%")]
ALARMS = ["overspeed", "lube-oil low pressure", "exhaust high temp", "cooling-water high temp",
          "emergency stopped", "steering pump 1 fault", "steering pump 2 fault", "steering hyd oil low"]


def rated(read):
    probe.head("Rated plate (HR 200-221)")
    h = read(200, 10)
    if not h:
        print("  no asset block at HR 200.")
        return
    print(f"  class      {probe.DEVICE_CLASS.get(h[0], h[0])}")
    print(f"  serial     {u32(h[1], h[2])}")
    print(f"  firmware   {probe.firmware(h[3])}  hw rev {h[4]}")
    print(f"  built      {h[5]} / commissioned {h[6]}")
    print(f"  run hours  {u32(h[7], h[8]):,}")
    print(f"  redundancy {'dual (A/B)' if h[9] == 1 else 'simplex'}")
    p = read(210, 12)
    if not p:
        return
    print(f"  MCR {p[0]:,} kW @ {p[1]} rpm, NCR {p[2]:,} kW @ {p[3]} rpm")
    print(f"  {p[4]} cylinders, bore {p[5]} mm, stroke {p[6]} mm")
    print(f"  propeller {'fixed' if p[10] == 0 else 'controllable'} pitch, {p[11] / 100:.2f} m")


def telemetry(read):
    probe.head("Live telemetry")
    st = read(0, 14)
    if not st:
        print("  status block unreadable.")
        return
    print(f"  main engine {'running' if st[7] else 'stopped'}")
    for addr, label, unit in STATUS:
        print(f"  {label:<20} {st[addr]:>6d} {unit}")
    al = read(20, 8)
    if al:
        active = [ALARMS[i] for i in range(8) if al[i]]
        print(f"  alarms {', '.join(active) if active else 'none'}")


def hints():
    probe.head("Where to start")
    print("""  Everything above is a read. Somewhere in here is the register that sets engine
  speed. Find it by consequence: write a value, watch the rpm follow. The twin pushes
  back; a governor holds the setpoint and a limiter clamps the fuel if you shove too
  hard. That push-back is how you know you found the real control loop.

  Then the lying gauge: you can force what a screen shows, but drive the engine into a
  condition that should be protected and it trips anyway. The safety unit reads its
  own sensor, not the gauge you faked. Working out why the trip still fires is the task.

  This script only reads. Everything that moves the engine, you write. Ask a mentor.""")


if __name__ == "__main__":
    sys.exit(probe.run(PORT, "Propulsion controller starter probe (read-only).", rated, telemetry, hints))
