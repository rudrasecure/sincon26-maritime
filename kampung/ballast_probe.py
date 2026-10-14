#!/usr/bin/env python3
"""
ballast_probe.py — SINCON 2026 Maritime Hacking Kampung, Ballast station starter.

This is your way in, not your way through. It connects to the ballast controller,
fingerprints it, and shows you what it is telling the world about itself and about
the ship right now. Then it points you at where to start looking. It does NOT solve
the exercise for you, and it never writes a single register — it only reads.

    python3 ballast_probe.py 10.71.30.10
    python3 ballast_probe.py 10.71.30.10:5021
    python3 ballast_probe.py --host 10.71.30.10 --port 5021
    python3 ballast_probe.py 10.71.30.10 --map        # deeper recon: dump the map

You get the controller's IP from the Kampung Wi-Fi (see docs/CONNECT.md). The port
is 5021 unless a mentor tells you otherwise.

What it shows you:
  1. The nameplate — who made this box, what it is, its serial and asset tag
     (Modbus device identification, function code 0x2B/14 — the same thing an OT
     recon sweep reads).
  2. The rated plate — pumps, tanks and capacities it advertises in holding
     registers, the way a real gauging system does.
  3. Live telemetry — tank levels, list angle, pump state, active alarms, right now.
  4. Where to start — honest hints, no answers.
"""

import argparse
import sys
import time

from mbtcp import ModbusTCP, ModbusError, DEVICE_ID_NAMES, parse_target, s16, u32

PORT_DEFAULT = 5021

DEVICE_CLASS = {1: "Propulsion control", 2: "Ballast & stability control",
                3: "Power management", 4: "Inert gas system", 5: "Navigation lights"}

# The eight ballast tanks, in register order (holding registers 0-7 = reported level %).
TANKS = ["FPT  (fore peak, centreline)", "APT  (aft peak, centreline)",
         "DB1P (double-bottom 1, port)", "DB1S (double-bottom 1, stbd)",
         "DB2P (double-bottom 2, port)", "DB2S (double-bottom 2, stbd)",
         "WBTP (wing ballast, port)", "WBTS (wing ballast, stbd)"]

# Alarm flags at holding registers 20-25 (non-zero = active).
ALARMS = ["list > 2° (warning)", "list > 5° (critical)", "list > 15° (DANGER)",
          "tank high level", "ballast pump 1 fault", "ballast pump 2 fault"]


def rule(title):
    print("\n" + "=" * 66)
    print(f"  {title}")
    print("=" * 66)


def fmt_fw(bcd):
    """Firmware version is one decimal digit per field: 310 -> v3.1.0."""
    return "v" + ".".join(list(str(bcd))) if bcd else "—"


def nameplate(c):
    rule("1. NAMEPLATE  (Modbus device identification, FC 0x2B / MEI 14)")
    try:
        objs = c.read_device_identification()
    except (ModbusError, OSError) as e:
        print(f"  device identification unavailable: {e}")
        print("  (not every controller answers FC43 — fall back to the rated plate below)")
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
    rule("2. RATED PLATE  (static asset registers, HR 200-225)")
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

    plate = c.read_holding_safe(210, 16)
    if plate is None:
        return
    total_cap = plate[5] * 10  # stored /10
    print(f"\n  ballast tanks      {plate[0]}")
    print(f"  ballast pumps      {plate[1]}  @ {plate[2]} m3/h, {plate[3]} m head, {plate[4]} kW each")
    print(f"  total capacity     {total_cap:,} m3")
    print(f"  gauge type         {'float' if plate[6] == 1 else str(plate[6])}")
    indep = plate[7] == 1
    print(f"  independent SIL channel  {'yes — a separate high-high transmitter' if indep else 'no'}")
    print("\n  per-tank capacity (m3):")
    for i, name in enumerate(TANKS):
        print(f"    {name:<32} {plate[8 + i]:>7,}")
    if indep:
        print("\n  Note the last line of the header block: this gauging system declares an")
        print("  INDEPENDENT safety channel — a second measurement that does not share a")
        print("  sensor with the tank gauges. Keep that in mind when something stops you.")


def telemetry(c):
    rule("3. LIVE TELEMETRY  (what the ship is doing, right now)")
    st = c.read_holding_safe(0, 14)
    if st is None:
        print("  could not read the status block (HR 0-13).")
        return
    print("  tank levels (reported %):")
    for i, name in enumerate(TANKS):
        print(f"    {name:<32} {st[i]:>3d}%")
    print(f"\n  pump 1 running     {'yes' if st[10] else 'no'}")
    print(f"  pump 2 running     {'yes' if st[11] else 'no'}")
    print(f"  list (heel) angle  {s16(st[12]) / 10:+.1f}°   (port negative, starboard positive)")
    print(f"  trim angle         {s16(st[13]) / 10:+.1f}°   (+ by the bow)")

    al = c.read_holding_safe(20, 6)
    if al is not None:
        active = [ALARMS[i] for i in range(6) if al[i]]
        print(f"\n  active alarms      {', '.join(active) if active else 'none'}")


def change_scan(c):
    """Teach the telemetry-vs-command method: snapshot twice, show what moved on its own."""
    rule("4. WHAT MOVES ON ITS OWN  (telemetry vs. command)")
    print("  Reading HR 0-29 twice, 4 s apart. A register that changes with no one")
    print("  writing to it is TELEMETRY (the plant reporting itself). A register that")
    print("  only ever moves when someone writes it is a COMMAND. That difference is")
    print("  how you find the controls without a manual.\n")
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
        print("  nothing in HR 0-29 moved in 4 s — the ship may be sitting still.")
        print("  (Give her something to do, or watch over a longer window.)")


def full_map(c):
    """Deeper recon for the keen: a coarse readability map of the address space."""
    rule("5. ADDRESS-SPACE MAP  (--map)   — recon, not answers")
    print("  Which register windows answer a read, and a sample of each. Some of these")
    print("  are telemetry, some are an asset plate, and some are controls. Working out")
    print("  which is which — and what each control does — is the exercise.\n")
    for base in range(0, 560, 20):
        vals = c.read_holding_safe(base, 20)
        if vals is None:
            continue
        nonzero = [v for v in vals if v != 0]
        if not nonzero:
            tag = "(all zero)"
        else:
            tag = " ".join(str(v) for v in vals[:8]) + (" ..." if len(vals) > 8 else "")
        print(f"  HR {base:>3d}-{base + 19:<3d}  {tag}")


def hints():
    rule("WHERE TO START")
    print("""  Three layers never quite agree, and that gap is the whole game:
    - what the ship is actually doing  (the list angle above — physical truth)
    - what the controller holds         (the registers you just read)
    - what the crew sees                (the loadicator and bridge screens)

  The task: unbalance her and lay her over. To do that you have to:
    1. Find the command registers. The nameplate and telemetry above are reads.
       Somewhere in this device are registers that DO things. Find them by
       consequence: change one, watch the live telemetry, see what the ship does.
       (Re-run with --map to see the territory.)
    2. Expect to be stopped. A protection will catch a crude attempt and hold the
       list to a few degrees. Read the rated plate again: this box told you it has
       an INDEPENDENT safety channel. A guard that reads its OWN instrument cannot
       be fooled by lying to the gauges the control system shows — so find that
       instrument and deal with it directly. That is the lesson of the station.

  Two things that quietly waste a lazy attacker's time — figure out why:
    - water will not move unless the right machinery is actually running;
    - not all tanks are equal. Some are tiny and on the centreline; the ones that
      lay a ship over are the big ones, far outboard.

  This script only reads. Everything that changes the ship, you write yourself.
  A mentor is standing right there — use them.""")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Ballast controller starter probe (read-only).",
        epilog="Example: python3 ballast_probe.py 10.71.30.10")
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
        ap.error("give the controller IP, e.g.  python3 ballast_probe.py 10.71.30.10")

    print(f"SINCON 2026 — Ballast station starter probe")
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
