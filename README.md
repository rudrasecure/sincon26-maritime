# SINCON 2026 — Maritime Hacking Kampung

Participant toolkit for RUDRA Secure's Maritime Hacking Kampung at **SINCON 2026**.

You scanned a QR code at the Kampung and landed here. This repository is the small
kit you use at two of the hands-on stations — **Ballast** and **Engine** — on RUDRA's
maritime cyber range. It contains starter scripts that help you *get oriented* on a
real shipboard controller, plus the worksheets for each station.

> **These are starter scripts, not solutions.** They connect, fingerprint the
> controller, and show you what it is and what the ship is doing right now — then
> point you at where to begin. The actual exercise, you do yourself. A mentor is at
> the station to help.

## What's here

```
kampung/
  mbtcp.py          a tiny, dependency-free Modbus/TCP client (standard library only)
  ballast_probe.py  Ballast station starter — fingerprint + orient (read-only)
  engine_probe.py   Engine  station starter — fingerprint + orient (read-only)
docs/
  CONNECT.md             join the Kampung Wi-Fi and find the controller
  REGISTER_CHEATSHEET.md a partial register map (the read side; you discover the rest)
  BALLAST_WORKSHEET.md   the Ballast station, step by step
  ENGINE_WORKSHEET.md    the Engine  station, step by step
requirements.txt    optional — only if you want pymodbus for your own write scripts
```

## Quick start

1. Join the Kampung Wi-Fi and get your laptop on the OT network — **[docs/CONNECT.md](docs/CONNECT.md)**.
2. Run the starter for the station you're at:
   ```bash
   python3 kampung/ballast_probe.py 10.71.30.10      # Ballast station
   python3 kampung/engine_probe.py  10.71.20.10      # Engine  station
   ```
   Python 3.8+ is all you need — the probes use only the standard library.
3. Read what it tells you, then open the worksheet for that station and go.

## A word on realism

For the Kampung we put you **directly onto an operational-technology (OT) subnet** so
you can spend your time on the technique that matters at each station. **On a real
vessel you would never have this.** Shipboard OT networks are segmented and are not
directly addressable from anywhere a visitor — or an attacker — starts out. Getting
*onto* the bus is the hard part of a real engagement, and it's a whole separate body
of work (pivoting, segmentation, the ship's IT/OT boundary). That's what RUDRA's full
maritime course covers. Here, you start already on the wire.

Everything here runs against a **simulated** vessel on a closed range. The same
actions against a ship in service are illegal and dangerous. They are safe only here.

---

RUDRA Secure · https://rudrasecure.com · Maritime Hacking Kampung, SINCON 2026
