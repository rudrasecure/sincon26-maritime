#!/usr/bin/env python3
"""
ballast_probe.py: Kampung ballast station starter (read-only).

Connects to the ballast controller, fingerprints it, and shows what it reports about
itself and the ship right now, then points you where to start. It never writes.

    python3 ballast_probe.py 10.71.30.10
    python3 ballast_probe.py 10.71.30.10:5021
    python3 ballast_probe.py 10.71.30.10 --map

Needs pymodbus (pip install pymodbus). The IP comes from the Ship OT Bridge Wi-Fi
(docs/CONNECT.md); the port is 5021.
"""
import sys

import probe
from probe import s16, u32

PORT = 5021

# The eight tanks in register order: status level at HR 0-7, capacity at HR 218+.
TANKS = [
    ("FPT", "fore peak, centreline"),
    ("APT", "aft peak, centreline"),
    ("DB1P", "double-bottom 1, port"),
    ("DB1S", "double-bottom 1, stbd"),
    ("DB2P", "double-bottom 2, port"),
    ("DB2S", "double-bottom 2, stbd"),
    ("WBTP", "wing ballast, port"),
    ("WBTS", "wing ballast, stbd"),
]
ALARMS = ["list > 2 deg", "list > 5 deg (critical)", "list > 15 deg (danger)",
          "tank high level", "pump 1 fault", "pump 2 fault"]


def rated(read):
    probe.head("Rated plate (HR 200-225)")
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
    p = read(210, 16)
    if not p:
        return
    print(f"  {p[0]} tanks, {p[1]} pumps @ {p[2]} m3/h / {p[3]} m head / {p[4]} kW each")
    print(f"  total capacity {p[5] * 10:,} m3, gauge {'float' if p[6] == 1 else p[6]}")
    print(f"  independent SIL channel: {'yes, a separate high-high transmitter' if p[7] == 1 else 'no'}")
    caps = ", ".join(f"{code} {p[8 + i]:,}" for i, (code, _) in enumerate(TANKS))
    print(f"  per-tank capacity (m3): {caps}")


def telemetry(read):
    probe.head("Live telemetry")
    st = read(0, 14)
    if not st:
        print("  status block unreadable.")
        return
    for i, (code, desc) in enumerate(TANKS):
        print(f"  {code:<5} {desc:<23} {st[i]:>3d}%")
    print(f"  pump 1 {'running' if st[10] else 'off'}, pump 2 {'running' if st[11] else 'off'}")
    print(f"  list {s16(st[12]) / 10:+.1f} deg (port -, stbd +), trim {s16(st[13]) / 10:+.1f} deg")
    al = read(20, 6)
    if al:
        active = [ALARMS[i] for i in range(6) if al[i]]
        print(f"  alarms {', '.join(active) if active else 'none'}")


def hints():
    probe.head("Where to start")
    print("""  Everything above is a read. Somewhere in here are registers that DO things.
  Find them by consequence: write one, watch the telemetry, see what the ship does.
  Re-run with --map for the territory.

  A crude attempt gets caught. A protection holds the list to a few degrees, and it
  reads its own independent instrument, so lying to the control gauges will not move
  it. Find that instrument and deal with it directly. That is the lesson here.

  Two things that waste your time, and why: water will not move unless the pumps are
  actually running, and the centreline peaks barely heel her. The big outboard wing
  tanks are what lay a ship over.

  This script only reads. Everything that moves the ship, you write. Ask a mentor.""")


if __name__ == "__main__":
    sys.exit(probe.run(PORT, "Ballast station starter probe (read-only).", rated, telemetry, hints))
