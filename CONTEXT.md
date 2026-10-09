# FCR-N Dispatcher

A battery (BESS) that provides FCR-N to the Nordic grid by following a droop law on grid frequency.

## Language

**FCR-N**:
Frequency Containment Reserve, Normal. A symmetric reserve that responds to frequency inside the 49.9 to 50.1 Hz band.
_Avoid_: FCR (too broad, also covers FCR-D)

**FCR-N capacity** (C_FCR-N):
The power the battery delivers at a full frequency deviation of 0.1 Hz.
_Avoid_: Bid size, reserve size

**Droop law**:
P = C_FCR-N / 0.1 Hz · (50.0 Hz − f). It maps a measured frequency to a requested power. Positive power means discharge to the grid, so a low frequency gives a positive power.

**Full activation**:
The response at a frequency deviation of 0.1 Hz or more: ±C_FCR-N. FCR-N never asks for more than C_FCR-N, even below 49.9 Hz or above 50.1 Hz.

**Commanded power**:
The power the controller asks the battery to deliver.
_Avoid_: Setpoint, target

**Actual power**:
The power the battery really delivers after it applies its own limits.

**Usable energy capacity** (E):
The energy the battery may use for FCR-N. It is smaller than the nameplate capacity of a real unit.
_Avoid_: Capacity (clashes with FCR-N capacity), nameplate capacity

**State of Charge** (SoC):
Stored energy divided by usable energy capacity, a value in [0, 1].

**Limited energy reservoir** (LER):
A unit that cannot sustain full activation for two hours. A battery is an LER.

**Step test**:
The Table 3 frequency sequence 50.0 → 49.95 → 50.0 → 49.9 → 50.1 → 50.0 Hz, used in prequalification.

**Steady-state power** (Pss):
The mean actual power over the last 60 s of a step in the step test.

**Steady-state response** (ΔPss):
The power change at 49.9 Hz or 50.1 Hz, measured against the average of the two 50.0 Hz steady states around it.

**Sample**:
One record of the dispatcher's state at one instant: timestamp, frequency, commanded power, actual power and SoC. Every sample is stored.
_Avoid_: Reading, measurement, data point

**Run**:
One process lifetime of the dispatcher, from start to stop. Every sample belongs to exactly one run. The run identifier exists only to find the samples of one step test. In production the dispatcher runs for weeks, samples are read by time, and the run identifier carries no meaning.
