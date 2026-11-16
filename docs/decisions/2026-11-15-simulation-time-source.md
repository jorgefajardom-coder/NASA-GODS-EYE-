# D-CLK-01 — Gazebo simulated time is the single time base of a simulated run

Recorded 15 November 2026, America/Bogota. Authority: Jesús, owner of the ICD,
bringup and integration adapters, after Jorge flagged that switching the stack
to Gazebo simulated time is a contract decision for that owner. Status:
**proposed by the integration owner; Jorge's display review and David's review
of resource-time semantics are pending.** This does not change any ROS
message/service field, unit, enum, interface package version, canonical replay
1.0.0 or `mge-public-rasters-1.0.0`.

## Context

PR49 (`f9f1fe6`) already bridges `/world/<world>/clock` into ROS `/clock` in
`gazebo_mock.launch.py`, starts consumers only after one advancing clock
publisher is observed and passes `use_sim_time=true` to every node it launches.
The physical rover debits time from Gazebo odometry stamps and keeps a steady
watchdog for braking. The ICD, however, only said "`/clock` from Gazebo when it
runs", and `vertical_mock.launch.py` checked the clock only for
`mission:=real`. With `use_sim_time:=true` and the MOCK mission, a missing or
paused clock left every node at t=0 without failing. The recorded packages
published so far (`recorded-recovery-001/002`) are wall-clock MOCK runs
(`clock_source: system`).

## Decision

1. A run has exactly one time base. Either every MGE node uses
   `use_sim_time=true` against exactly one external, advancing `/clock`, or the
   whole run uses the wall clock and is recorded as `clock_source: system`.
   Mixing time bases inside one run is not allowed.
2. When Gazebo runs, its bridged clock is that time base. Mission headers,
   ETAs, `time_remaining_s` debit, stop-acknowledgement deadlines and replay
   `timestamp_sim_s` follow it. Pausing Gazebo pauses mission time.
3. Any launch with `use_sim_time:=true` (MOCK or real mission) must observe one
   advancing `/clock` publisher before starting providers. It fails with
   `NOT_READY: EXTERNAL_SIMULATION_CLOCK_REQUIRED` (absent or frozen clock) or
   `PROVIDER_COLLISION` (two publishers). No node fabricates a clock.
4. Steady-clock timers are allowed only for liveness and safety: brake watchdog,
   odometry freshness, mirror throttling and mission polling. They never stamp
   messages or debit resources.
5. Wall-clock MOCK runs remain valid for software evidence and stay labelled as
   such. A Gazebo-time run is not a LIVE mission or physical validation.

## Consequences

- `vertical_mock.launch.py` now requires the clock whenever
  `use_sim_time:=true`, not only for `mission:=real`, and requires the stamps to
  advance with exactly one publisher. `gazebo_mock.launch.py` already satisfies
  this; launching Gazebo paused now fails before providers start.
- The web viewer already accepts `clock_source: 'sim'` and normalizes replay time
  from `time_start_sim_s` (`web/src/data/gatewayReplay.ts`). Jorge should confirm
  the display with a Gazebo-time package before it replaces a wall-clock one.
- New evidence recordings of stop/replan/return should use the Gazebo-time
  wrapper when Gazebo is part of the claim. The historical wall-clock packages are
  kept unchanged.
- Gazebo's real-time factor can make a run take longer in wall time than in
  simulated time. Durations in evidence are reported in simulated time.

## Not decided here

Whether non-Gazebo MOCK runs must also move to simulated time (which would need
a separately reviewed clock provider) is left open. So are physical calibration,
scientific approval of resource rates, three-role acceptance and the JES-07 /
AC-10 organizer review.
