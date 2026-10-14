#!/usr/bin/env python3
"""
engine_probe.py — SINCON 2026 Maritime Hacking Kampung, Engine station starter.

Same idea as ballast_probe.py: connect to the propulsion controller, fingerprint
it, show its nameplate and live telemetry, and point you at where to start. It
reads only — it never writes, and it does not solve the exercise for you.

    python3 engine_probe.py 10.71.20.10
    python3 engine_probe.py 10.71.20.10:5020
    python3 engine_probe.py --host 10.71.20.10 --port 5020
    python3 engine_probe.py 10.71.20.10 --map

Controller IP comes from the Kampung Wi-Fi (docs/CONNECT.md). Port is 5020 unless a
mentor says otherwise.
"""

import argparse
import sys
import time

from mbtcp import ModbusTCP, ModbusError, DEVICE_ID_NAMES, parse_target, s16, u32

PORT_DEFAULT = 5020

DEVICE_CLASS = {1: "Propulsion control", 2: "Ballast & stability control",
                3: "Power management", 4: "Inert gas system", 5: "Navigation lights"}

# Status holding registers that matter at this station.
STATUS = [
    (0, "main engine speed", "rpm", 1),
    (1, "shaft power", "kW", 1),
    (2, "fuel rack / index", "raw", 1),
    (3, "exhaust temperature", "degC", 1),
    (4, "lube-oil pressure", "raw reg", 1),
    (6, "cooling-water temp", "degC", 1),
    (8, "engine load", "%", 1),
]
ALARMS = ["overspeed", "lube-oil low-pressure trip", "exhaust high temp", "cooling-water high temp",
          "emergency stopped", "steering pump 1 fault", "steering pump 2 fault", "steering hyd oil low"]


def rule(title):
    print("\n" + "=" * 66)
    print(f"  {title}")
    print("=" * 66)


def fmt_fw(bcd):
    return "v" + ".".join(list(str(bcd))) if bcd else "—"


def nameplate(c):
    rule("1. NAMEPLATE  (Modbus device identification, FC 0x2B / MEI 14)")
    try:
        objs = c.read_device_identification()
    except (ModbusError, OSError) as e:
        print(f"  device identification unavailable: {e}")
        return
    if not objs:
        print("  the controller answered but advertised no identification objects.")
        return
    for oid in sorted(objs):
        name = DEVICE_ID_NAMES.get(oid, f"object 0x{oid:02X}")
        try:
            val = objs[oid].decode("latin-1")
        except Exception:
            val = objs[oid].hex()
        print(f"  {name:<20} {val}")


def rated_plate(c):
    rule("2. RATED PLATE  (static asset registers, HR 200-221)")
    hdr = c.read_holding_safe(200, 10)
    if hdr is None:
        print("  no asset block at HR 200 — this controller may not carry one.")
        return
    cls = DEVICE_CLASS.get(hdr[0], f"unknown ({hdr[0]})")
    serial = u32(hdr[1], hdr[2])
    hours = u32(hdr[7], hdr[8])
    print(f"  device class       {cls}")
    print(f"  serial number      {serial}")
    print(f"  firmware           {fmt_fw(hdr[3])}   hardware rev {hdr[4]}")
    print(f"  built / commissioned {hdr[5]} / {hdr[6]}")
    print(f"  powered-on hours   {hours:,}")
    print(f"  redundancy         {'dual (A/B)' if hdr[9] == 1 else 'simplex'}")

    plate = c.read_holding_safe(210, 12)
    if plate is None:
        return
    print(f"\n  MCR (max continuous) {plate[0]:,} kW @ {plate[1]} rpm")
    print(f"  NCR (normal)         {plate[2]:,} kW @ {plate[3]} rpm")
    print(f"  cylinders            {plate[4]}   bore {plate[5]} mm   stroke {plate[6]} mm")
    print(f"  propeller            {'fixed pitch' if plate[10] == 0 else 'controllable pitch'}, {plate[11] / 100:.2f} m")


def telemetry(c):
    rule("3. LIVE TELEMETRY  (what the engine is doing, right now)")
    st = c.read_holding_safe(0, 14)
    if st is None:
        print("  could not read the status block (HR 0-13).")
        return
    print(f"  main engine        {'RUNNING' if st[7] else 'stopped'}")
    for addr, label, unit, _ in STATUS:
        print(f"  {label:<22} {st[addr]:>6d} {unit}")
    al = c.read_holding_safe(20, 8)
    if al is not None:
        active = [ALARMS[i] for i in range(8) if al[i]]
        print(f"\n  active alarms      {', '.join(active) if active else 'none'}")


def change_scan(c):
    rule("4. WHAT MOVES ON ITS OWN  (telemetry vs. command)")
    print("  Reading HR 0-29 twice, 4 s apart. Registers that change on their own are")
    print("  telemetry (the engine reporting itself). Registers that only move when")
    print("  written are commands. That is how you find the throttle with no manual.\n")
    a = c.read_holding_safe(0, 30)
    time.sleep(4)
    b = c.read_holding_safe(0, 30)
    if a is None or b is None:
        print("  scan unavailable.")
        return
    moved = [i for i in range(30) if a[i] != b[i]]
    if moved:
        print("  changed on their own (telemetry):")
        for i in moved:
            print(f"    HR {i:<3d}  {a[i]} -> {b[i]}")
    else:
        print("  nothing in HR 0-29 moved in 4 s — the engine may be stopped or steady.")


def full_map(c):
    rule("5. ADDRESS-SPACE MAP  (--map)   — recon, not answers")
    print("  Which register windows answer a read, and a sample of each. Telemetry, an")
    print("  asset plate, and controls all live in here. Telling them apart is the task.\n")
    for base in range(0, 560, 20):
        vals = c.read_holding_safe(base, 20)
        if vals is None:
            continue
        nonzero = [v for v in vals if v != 0]
        tag = "(all zero)" if not nonzero else " ".join(str(v) for v in vals[:8]) + (" ..." if len(vals) > 8 else "")
        print(f"  HR {base:>3d}-{base + 19:<3d}  {tag}")


def hints():
    rule("WHERE TO START")
    print("""  Two tasks at this station, each harder than the last.

  TASK A — find the lever and take it.
    The nameplate and telemetry above are all reads. Somewhere in this controller
    is the register that sets engine speed. Find it by consequence: write a value,
    watch the rpm in the live telemetry, and confirm the engine followed you. The
    twin fights back — it ramps, a governor holds your setpoint, a limiter clamps
    the fuel if you shove too hard. That push-back is how you know you found the
    real control loop and not a number that does nothing.

  TASK B — the lying gauge.
    Make a displayed reading look healthy while you drive the engine into a
    condition that should be protected against. You will find you can force what
    the SCREEN shows. You will also find the engine trips anyway — because the
    safety unit is a separate box that reads its OWN sensor, not the gauge you
    faked. Fooling the crew is not the same as fooling the protection. Working out
    why the trip still fires is the point of the task.

  This script only reads. Everything that changes the engine, you write yourself.
  Ask a mentor — that is what they are here for.""")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Propulsion controller starter probe (read-only).",
        epilog="Example: python3 engine_probe.py 10.71.20.10")
    ap.add_argument("target", nargs="?", help="controller IP or IP:PORT")
    ap.add_argument("--host", help="controller IP (alternative to positional)")
    ap.add_argument("--port", type=int, help=f"Modbus TCP port (default {PORT_DEFAULT})")
    ap.add_argument("--unit", type=int, default=1, help="Modbus unit/slave id (default 1)")
    ap.add_argument("--map", action="store_true", dest="do_map",
                    help="also dump a coarse readability map of the register space")
    args = ap.parse_args(argv)

    if args.target:
        host, port = parse_target(args.target, args.port or PORT_DEFAULT)
    elif args.host:
        host, port = args.host, args.port or PORT_DEFAULT
    else:
        ap.error("give the controller IP, e.g.  python3 engine_probe.py 10.71.20.10")

    print("SINCON 2026 — Engine station starter probe")
    print(f"target: {host}:{port}  (unit {args.unit}) — read-only\n")

    try:
        with ModbusTCP(host, port, unit=args.unit) as c:
            nameplate(c)
            rated_plate(c)
            telemetry(c)
            change_scan(c)
            if args.do_map:
                full_map(c)
            hints()
    except OSError as e:
        print(f"\ncould not reach {host}:{port} — {e}")
        print("Are you on the Kampung Wi-Fi? Is the IP right? See docs/CONNECT.md, or ask a mentor.")
        return 1
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
