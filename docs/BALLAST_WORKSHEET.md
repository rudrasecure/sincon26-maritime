# Ballast station

**Target:** the ballast / tank-gauging controller, `10.71.30.10:5021`
**Protocol:** Modbus TCP · **Time:** ~10 minutes · **One or two per seat**

> Live-fire against the range's ballast controller. Everything is simulated on a
> closed range (see the realism note in the [README](../README.md)). The register map
> is for this range only.

## The idea

A ballast system keeps a ship upright and trimmed by moving water between tanks. Here
you run it the wrong way on purpose: pump one side down, hold the other full, until she
takes a list on the big screen. None of the heel is scripted. A hydrostatic model works
it out from the water you actually move, and the loadicator reads the same list the
bridge would. Your first attempt stalls a few degrees in. Working out what stopped it,
and beating it, is the job.

## 1. Orient (demo)

Run the register viewer and watch the live values (Ctrl+C to stop):

```bash
python3 kampung/ballast_registers.py 10.71.30.10
```

- The **live telemetry** is the truth layer: tank levels (HR0–7), pump status, and the
  current list angle (HR12). Watch what changes on its own.
- Note which tanks sit on the centreline versus outboard (the big outboard **wing**
  tanks carry the heel), and that this gauging system carries an **independent safety
  channel** separate from the tank gauges. File that away.

## 2. The puzzle (task)

1. **First attempt.** Find the command registers (the register cheatsheet points you at
   roughly where; confirm by consequence). Command a fill on one side and a drain on the other.
   She starts to heel, then stops at about **3 degrees**, valves forced shut. Something
   caught you. Work out what.
2. **The decoy.** There is an obvious-looking protection, a tank *overfill* guard, but
   it never fires here, because it only cares about tanks overflowing, not which side
   they are on. Chasing it wastes your time.
3. **The real guard.** What stopped you is an **anti-heeling function** watching its own
   **independent inclinometer**, a sensor separate from the tank-level gauges. Past a
   few degrees of list it shuts every valve that would deepen it.
4. **Defeat it.** A guard that reads its own instrument cannot be fooled by lying to the
   gauges the control system shows. So you have to find *that instrument* in the
   register map, make it report level, and hold it there. Blind, the function never sees
   the list develop, so it never trips, and she goes all the way over.

### Two traps that catch a lazy attacker

- **No pump, no water.** The ballast pumps have to be commanded on first. Leave them off
  and your attack silently does nothing.
- **The wings carry the heel.** Drain the big outboard **wing** tanks, not just the
  small double-bottoms. The wings are enormous and far outboard, so they carry by far
  the largest heeling arm. Drain only the little ones and the list stalls below the
  danger threshold.

## 3. Cross-check (the lesson)

You beat the anti-heeling guard only by finding and **blinding its independent
channel**. That is the one idea to leave with: *a safety system that reads its own
sensor cannot be defeated by lying to the control system's sensors.* It is the most
important principle in OT security, and the same trick you use at the Engine station. A
defender's job is the mirror image: spot that the gauges and the independent channel
disagree.

## Flag

Get her past **15 degrees**, the DANGER list threshold, and the alarm banner on the big
screen shows your flag.

## Reset

Tell a mentor when you are done; they reset the ballast state for the next player.
