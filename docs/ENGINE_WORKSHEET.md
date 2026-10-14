# Engine station

**Target:** the propulsion controller — `10.71.20.10:5020`
**Protocol:** Modbus TCP · **Time:** ~10 minutes · **One seat, one person**

> Live-fire against the range's propulsion controller. Simulated vessel, closed range
> — see the realism note in the [README](../README.md).

## The idea

This is a high-fidelity engine twin — a real governor, acceleration ramps, limiters,
and a safety system built as a **separate box**, the way a real ship is. Two tasks,
each harder than the last.

## 1. Orient (demo)

```bash
python3 kampung/engine_probe.py 10.71.20.10
```

Read the **nameplate** (device identification, FC43) — it names the vendor and the
propulsion-control product, your first win. Read the **rated plate** (a ~27 MW,
7-cylinder slow-speed main engine) and the **live telemetry** (rpm, load, exhaust,
lube-oil pressure).

## 2. Task A — find the lever and take it

1. **Fingerprint** — done: the starter already read the device-identification strings.
2. **Classify.** Watch the registers while the engine runs. A value that changes on its
   own is telemetry; a value that only moves when *someone writes it*, and the engine
   then responds, is a command. (The starter's "what moves on its own" scan gets you
   started; `--map` shows the territory.)
3. **Confirm by consequence.** Write the register you think is the engine speed command
   — the lever — and watch the rpm (HR 0) ramp to follow it. If the engine moved, you
   found it.

The twin **fights back**: it ramps rather than snapping, a governor works to hold your
setpoint, and a limiter clamps the fuel if you push too hard. That realistic push-back
is how you know you're driving a real control loop, not a lookup table.

## 3. Task B — the lying gauge

Force the *displayed* lubricating-oil pressure so the bridge gauge reads healthy, then
command the engine into a condition that should be protected against. The engine
**trips anyway** — because the safety unit doesn't read the gauge. It reads its own
sensor, and the screen you faked never reached it.

Working out *why the trip still fires* despite a healthy-looking gauge is the point of
the task.

## 4. Cross-check (the lesson)

Same principle as the Ballast station, on a different system: **a faked screen fools
the crew but not the safety system, because they're separate boxes reading separate
sensors.** And you've now learned to find a command register by its behaviour alone —
the skill that transfers to any OT controller, any protocol.

## ⚑ Flag

Complete Task B: force the gauge, command the fault, and the safety trip that fires
despite the healthy gauge carries your flag.

## Reset

Tell a mentor when you're done; they reset the engine twin for the next player.
