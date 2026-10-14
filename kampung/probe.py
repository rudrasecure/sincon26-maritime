"""Shared rendering for the Kampung starter probes (ballast_probe, engine_probe).

Read-only. The Modbus/TCP client is pymodbus (pip install pymodbus; see
requirements.txt). A station script supplies three functions (rated, telemetry,
hints) and calls run(). Each is handed a read(addr, count) helper that returns a
list of register values, or None if the read failed.
"""
import argparse
import logging
import time

try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    raise SystemExit("pymodbus is required:  pip install pymodbus   (see requirements.txt)")

# Keep pymodbus's own INFO/ERROR chatter out of the probe's output; we print our own.
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)

# device-class code -> label, as advertised at HR 200 of the rated plate.
DEVICE_CLASS = {
    1: "Propulsion control",
    2: "Ballast & stability control",
    3: "Power management",
    4: "Inert gas system",
    5: "Navigation lights",
}

# FC43 object id -> label, for printing a device-identification dump.
OBJECT_NAMES = {
    0x00: "VendorName", 0x01: "ProductCode", 0x02: "MajorMinorRevision",
    0x03: "VendorUrl", 0x04: "ProductName", 0x05: "ModelName",
    0x06: "UserApplicationName", 0x80: "SerialNumber", 0x81: "AssetTag",
}


def s16(v):
    """Interpret a 16-bit register as a signed value."""
    return v - 0x10000 if v >= 0x8000 else v


def u32(hi, lo):
    """Combine two registers into a 32-bit unsigned value (hi word first)."""
    return (hi << 16) | lo


def head(title):
    print(f"\n{title}")
    print("-" * len(title))


def firmware(bcd):
    """One decimal digit per field: 310 -> v3.1.0."""
    return "v" + ".".join(str(bcd)) if bcd else "n/a"


def nameplate(client, unit):
    head("Nameplate (device identification, FC43)")
    objs, next_id = {}, 0
    for _ in range(8):  # bounded follow of the more-follows flag
        rr = client.read_device_information(read_code=0x03, object_id=next_id, device_id=unit)
        if rr.isError():
            print(f"  unavailable: {rr}")
            return
        objs.update(rr.information)
        if not getattr(rr, "more_follows", False):
            break
        next_id = rr.next_object_id
    for oid in sorted(objs):
        val = objs[oid]
        if isinstance(val, bytes):
            val = val.decode("latin-1")
        print(f"  {OBJECT_NAMES.get(oid, f'object 0x{oid:02X}'):<20} {val}")


def changes(read, span=30, gap=4):
    head("What moves on its own (telemetry vs command)")
    print(f"  Two reads of HR 0-{span - 1}, {gap}s apart. What changes by itself is")
    print("  telemetry; what only moves when written is a command.\n")
    a = read(0, span)
    time.sleep(gap)
    b = read(0, span)
    if a is None or b is None:
        print("  read failed.")
        return
    moved = [i for i in range(span) if a[i] != b[i]]
    if not moved:
        print(f"  nothing in HR 0-{span - 1} moved; the plant may be steady.")
        return
    for i in moved:
        print(f"  HR {i:<3d} {a[i]} -> {b[i]}")


def address_map(read, upto=560, step=20):
    head("Address map (--map): which windows answer, with a sample")
    for base in range(0, upto, step):
        vals = read(base, step)
        if vals is None:
            continue
        sample = "all zero" if not any(vals) else " ".join(map(str, vals[:8]))
        print(f"  HR {base:>3d}-{base + step - 1:<3d}  {sample}")


def run(default_port, blurb, rated, telemetry, hints):
    ap = argparse.ArgumentParser(description=blurb, epilog="read-only; it never writes.")
    ap.add_argument("target", nargs="?", help="controller IP or IP:PORT")
    ap.add_argument("--host", help="controller IP (instead of the positional arg)")
    ap.add_argument("--port", type=int, help=f"Modbus TCP port (default {default_port})")
    ap.add_argument("--unit", type=int, default=1, help="Modbus unit id (default 1)")
    ap.add_argument("--map", action="store_true", dest="do_map",
                    help="also dump a coarse readability map of the register space")
    args = ap.parse_args()

    target = args.target or args.host
    if not target:
        ap.error("give the controller IP, e.g. 10.71.30.10")
    if ":" in target and args.port is None:
        host, _, p = target.rpartition(":")
        port = int(p)
    else:
        host, port = target, args.port or default_port

    client = ModbusTcpClient(host, port=port, timeout=4)
    if not client.connect():
        print(f"cannot reach {host}:{port}.")
        print("On the Ship OT Bridge Wi-Fi? Right IP? See docs/CONNECT.md, or ask a mentor.")
        return 1

    def read(addr, count):
        rr = client.read_holding_registers(addr, count=count, device_id=args.unit)
        return None if rr.isError() else rr.registers

    print(f"target {host}:{port} (unit {args.unit}), read-only")
    try:
        nameplate(client, args.unit)
        rated(read)
        telemetry(read)
        changes(read)
        if args.do_map:
            address_map(read)
        hints()
    finally:
        client.close()
    return 0
