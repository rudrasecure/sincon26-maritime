# SINCON 2026 Maritime Hacking Kampung

Participant toolkit for RUDRA Secure's Maritime Hacking Kampung at **SINCON 2026**.

You scanned a QR code at the Kampung and landed here. This repository is the small kit
you use at two of the hands-on stations, **Ballast** and **Engine**, on RUDRA's
maritime cyber range. It holds a live register viewer for each station to help you
*get oriented* on a real shipboard controller, plus the worksheet for each station.

> **These are read-only viewers, not solutions.** They connect and show you the
> controller's live registers — what the ship is doing right now, refreshed every
> second — so you can get oriented. The exercise itself you do yourself. A mentor is
> at the station to help.

## What's here

```
kampung/
  ballast_registers.py  Ballast station: live register viewer (read-only, refreshes each second)
  engine_registers.py   Engine  station: live register viewer (read-only, refreshes each second)
docs/
  CONNECT.md             join the Kampung Wi-Fi and find the controller
  REGISTER_CHEATSHEET.md a partial register map (the read side; you discover the rest)
  BALLAST_WORKSHEET.md   the Ballast station, step by step
  ENGINE_WORKSHEET.md    the Engine  station, step by step
requirements.txt    the one dependency, pymodbus (install before you join the Wi-Fi)
```

## Quick start

1. Install the one dependency, **pymodbus**, *before* you join the Wi-Fi. The Kampung
   network is air-gapped, so there is no internet once you are on it:
   ```bash
   pip install -r requirements.txt
   ```
2. Join the Kampung Wi-Fi and get your laptop on the OT network: **[docs/CONNECT.md](docs/CONNECT.md)**.
3. Run the register viewer for the station you're at:
   ```bash
   python3 kampung/ballast_registers.py 10.71.30.10   # Ballast station
   python3 kampung/engine_registers.py  10.71.20.10   # Engine  station
   ```
   Python 3.8+ and pymodbus (step 1) are all you need. Ctrl+C to stop.
4. Watch the live registers, then open the worksheet for that station and go.

## A word on realism

For the Kampung we put you **directly onto an operational-technology (OT) subnet** so
you can spend your time on the technique that matters at each station. **On a real
vessel you would never have this.** Shipboard OT networks are segmented and are not
directly addressable from where a visitor, or an attacker, starts out. Getting *onto*
the bus is the hard part of a real engagement, and it is a separate body of work:
pivoting, segmentation, the ship's IT/OT boundary. That is what RUDRA's full maritime
course covers. Here, you start already on the wire.

Everything here runs against a **simulated** vessel on a closed range. The same actions
against a ship in service are illegal and dangerous. They are safe only here.

---

RUDRA Secure · https://rudrasecure.com · Maritime Hacking Kampung, SINCON 2026
