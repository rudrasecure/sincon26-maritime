# Connecting at the Kampung

Three steps: join the Wi-Fi, confirm you are on the network, point the register viewer
at the controller.

## 1. Join the Kampung Wi-Fi

| | |
|---|---|
| **SSID** | `Ship OT Bridge` |
| **Password** | *posted at the station; ask a mentor* |

This Wi-Fi drops you straight onto the ship's OT subnet for the station you are at.
(See the realism note in the [README](../README.md): a real ship would never let you
on this easily. That is the point of running the exercise here.)

Your laptop gets an address automatically over DHCP. You will be on the `10.71.x.x`
range.

## 2. Confirm you can reach the controller

Each station has one controller. The mentor will confirm the address. The defaults are:

| Station | Target | Address | Port |
|---|---|---|---|
| **Ballast** | the ballast / tank-gauging controller | `10.71.30.10` | `5021` |
| **Engine** | the propulsion controller | `10.71.20.10` | `5020` |

Quick reachability check:

```bash
# Linux / macOS
nc -vz 10.71.30.10 5021          # "succeeded" means you are on

# any OS, using the register viewer (it tells you if it cannot connect)
python3 kampung/ballast_registers.py 10.71.30.10
```

If it cannot connect: check you joined `Ship OT Bridge` and not the venue Wi-Fi, check
the IP, and if it still will not go, grab a mentor.

## 3. Run the register viewer

It prints the station's key registers as an ASCII table and refreshes every second
(Ctrl+C to stop):

```bash
python3 kampung/ballast_registers.py 10.71.30.10    # or 10.71.30.10:5021
python3 kampung/engine_registers.py  10.71.20.10    # or 10.71.20.10:5020
```

Watch which values change on their own and which only move when you write them — that
is how you tell telemetry from commands.

## Tooling you need

These scripts use **pymodbus**. Install it *before* you join the Wi-Fi, because this
network is air-gapped (no internet) once you are on it:

```bash
pip install -r requirements.txt
```

The same library is what you use to *write* registers in your own exploit; the viewers
only read.
