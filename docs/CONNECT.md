# Connecting at the Kampung

Three steps: join the Wi-Fi, confirm you're on the network, point a starter script at
the controller.

## 1. Join the Kampung Wi-Fi

| | |
|---|---|
| **SSID** | `Ship OT Bridge` |
| **Password** | *posted at the station — ask a mentor* |

This Wi-Fi drops you straight onto the ship's OT subnet for the station you're at.
(See the realism note in the [README](../README.md): a real ship would never let you
on this easily — that's the point of the exercise being *here*.)

Your laptop gets an address automatically (DHCP). You'll be on the `10.71.x.x` range.

## 2. Confirm you can reach the controller

Each station has one controller. The mentor will confirm the address, but the defaults are:

| Station | Target | Address | Port |
|---|---|---|---|
| **Ballast** | the ballast / tank-gauging controller | `10.71.30.10` | `5021` |
| **Engine** | the propulsion controller | `10.71.20.10` | `5020` |

(What make and model each one actually is, you'll find out in a moment — fingerprinting
it is the first thing the starter script does.)

Quick reachability check:

```bash
# Linux / macOS
nc -vz 10.71.30.10 5021          # "succeeded" means you're on

# any OS, using the starter (it will tell you if it can't connect)
python3 kampung/ballast_probe.py 10.71.30.10
```

If it can't connect: check you joined `Ship OT Bridge` (not the venue Wi-Fi), check the
IP, and if it still won't go, grab a mentor.

## 3. Run the starter script

```bash
python3 kampung/ballast_probe.py 10.71.30.10        # or 10.71.30.10:5021
python3 kampung/engine_probe.py  10.71.20.10        # or 10.71.20.10:5020
```

Add `--map` for a deeper look at the controller's register space once you've read the
basics:

```bash
python3 kampung/ballast_probe.py 10.71.30.10 --map
```

## Tooling you might want

Nothing is required beyond Python 3.8+. If you want to write your own scripts that
*change* registers (the probes only read), `pymodbus` is the usual choice:

```bash
pip install -r requirements.txt
```

`nmap` with the `modbus-discover` script, or Metasploit's `modbus_client`, will also
read the same device-identification nameplate the starter shows you — try them if you
have them.
