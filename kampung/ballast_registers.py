#!/usr/bin/env python3
"""
ballast_registers.py -- live view of the ballast PLC command block + anti-heel
instrument, as ONE ASCII table of ADDRESS and VALUE, refreshed every second
(like `watch`). Ctrl+C to stop.

    python3 kampung/ballast_registers.py                 # default 10.71.30.10:5021
    python3 kampung/ballast_registers.py 10.71.30.10
    python3 kampung/ballast_registers.py 10.71.30.10:5021
    python3 kampung/ballast_registers.py 10.71.30.10 --interval 2 --cols 2

Read-only by design. The bottom of this file shows, in a COMMENTED-OUT block,
how you would WRITE a register (and make a written value HOLD). Uncomment it
only against the range twin.

Needs pymodbus (pip install -r requirements.txt; same library the kit uses).
"""
import argparse
import math
import sys
import time

from pymodbus.client import ModbusTcpClient

HOST, PORT, UNIT = "10.71.30.10", 5021, 1


def s16(v):
    """Interpret a 16-bit register as signed (for the angle readout)."""
    return v - 0x10000 if v >= 0x8000 else v


# address, format.  deg = signed tenths of a degree, bool = 0/1, raw = integer.
# 1500 means "unmapped register" on this controller.
REGISTERS = [
    (0, "pct"), (1, "pct"), (2, "pct"), (3, "pct"),
    (4, "pct"), (5, "pct"), (6, "pct"), (7, "pct"),
    (8, "raw"), (9, "raw"), (10, "bool"), (11, "bool"),
    (12, "deg"), (13, "deg"),
    (138, "deg"), (139, "bool"),
    (500, "bool"), (501, "bool"), (502, "bool"), (503, "bool"),
    (504, "bool"), (505, "bool"), (506, "bool"), (507, "bool"),
    (510, "bool"), (511, "bool"), (512, "bool"),
]

# contiguous spans to pull once per refresh, then index into
BLOCKS = [(0, 14), (138, 2), (500, 13)]

W_ADDR, W_VAL = 6, 12   # column widths within each address/value pair


def fmt(value, kind):
    if value is None:
        return "n/a"
    if value == 1500:
        return "1500 (unmapped)"
    if kind == "pct":
        return f"{value}%"
    if kind == "deg":
        return f"{s16(value)/10:+.1f} deg"
    if kind == "bool":
        return "1" if value else "0"
    return str(value)


def snapshot(c):
    """Read every block once; return {addr: value} (addr missing on a read error)."""
    cache = {}
    for base, count in BLOCKS:
        rr = c.read_holding_registers(base, count=count, device_id=UNIT)
        if not rr.isError():
            for i, v in enumerate(rr.registers):
                cache[base + i] = v
    return cache


def render(cache, host, port, cols):
    cells = [(f"HR{addr}", fmt(cache.get(addr), kind)) for addr, kind in REGISTERS]
    nrows = math.ceil(len(cells) / cols)
    while len(cells) < nrows * cols:
        cells.append(None)
    columns = [cells[c * nrows:(c + 1) * nrows] for c in range(cols)]

    pair = "-" * (W_ADDR + 2) + "+" + "-" * (W_VAL + 2)
    bar = "+" + "+".join(pair for _ in range(cols)) + "+"
    head = "|" + "|".join(f" {'ADDR':<{W_ADDR}} | {'VALUE':<{W_VAL}} " for _ in range(cols)) + "|"

    lines = [f"Ballast PLC  {host}:{port}  (unit {UNIT}, Modbus/TCP FC03)   "
             f"{time.strftime('%H:%M:%S')}   [Ctrl+C to stop]", "", bar, head, bar]
    for r in range(nrows):
        row = []
        for c in range(cols):
            cell = columns[c][r]
            if cell is None:
                row.append(" " * (W_ADDR + 2) + " " + " " * (W_VAL + 1))
            else:
                a, v = cell
                row.append(f" {a:<{W_ADDR}} | {v:<{W_VAL}} ")
        lines.append("|" + "|".join(row) + "|")
    lines.append(bar)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Live ASCII table of the ballast PLC registers.")
    ap.add_argument("target", nargs="?", default=HOST, help="IP or IP:PORT (default 10.71.30.10:5021)")
    ap.add_argument("--interval", type=float, default=1.0, help="refresh seconds (default 1)")
    ap.add_argument("--cols", type=int, default=1, help="address/value column pairs (default 1)")
    a = ap.parse_args()
    host, port = (a.target.split(":", 1) + [str(PORT)])[:2] if ":" in a.target else (a.target, PORT)
    port = int(port)

    c = ModbusTcpClient(host, port=port, timeout=4)
    if not c.connect():
        sys.exit(f"cannot reach {host}:{port} -- on the Ship OT Bridge Wi-Fi?")
    try:
        while True:
            if not c.connected:
                c.connect()
            frame = render(snapshot(c), host, port, max(1, a.cols))
            sys.stdout.write("\033[2J\033[H" + frame + "\n")   # clear + home, then paint
            sys.stdout.flush()
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print()
    finally:
        c.close()


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# HOW TO WRITE A REGISTER (AND HOLD A VALUE)
# ---------------------------------------------------------------------------
# Writing is FC06 (write_register). Example only -- run it against the range twin.
#
#     from pymodbus.client import ModbusTcpClient
#     c = ModbusTcpClient("10.71.30.10", port=5021, timeout=4)
#     c.connect()
#
#     # --- a simple write: set a register, then read it back to confirm ---
#     c.write_register(42, 1234, device_id=1)                       # write 1234 to HR42
#     print(c.read_holding_registers(42, count=1, device_id=1).registers)
#
#     # --- making a written value HOLD (general pattern) ----------------------
#     # Some registers are refreshed from the live process every tick, so a plain
#     # write to them is overwritten almost immediately. Where a register has a
#     # companion "hold"/latch flag, setting that flag makes your written value
#     # persist. In the abstract (pick the pair you actually mean):
#     SOME_REG  = 42        # the register whose value you want to pin
#     HOLD_FLAG = 43        # its companion hold flag (example addresses)
#     c.write_register(SOME_REG,  777, device_id=1)                 # write the value
#     c.write_register(HOLD_FLAG, 1,   device_id=1)                 # hold it
#     # ... later, to release the hold / restore:
#     c.write_register(HOLD_FLAG, 0,   device_id=1)
#     c.close()
