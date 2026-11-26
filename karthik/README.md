# Karthik — Mission 4 work area

This folder holds Mission 4's loss-accounting workflow, dataset exporter,
report, and data card. It leaves the shared board sketch and other mission
folders untouched. Live ESP32 results and the final dataset are not claimed
until a complete board capture is saved here.

## Files

- `mission4.py` — exact count predictions, all-144-clip payload generation,
  board stream capture, input/feature loss accounting, timeline correction,
  clip-boundary rejection, `.npz` dataset export, and explicit speed sweeps.
- `MISSION4_REPORT.md` — report in the assignment's eight required sections.
- `MISSION4_HANDOFF.md` — explicit pending hardware checklist, pass criteria,
  commands, labeling rules, and expected evidence artifacts.
- `data_card.md` — half-page data card draft; hardware-specific fields remain
  clearly marked pending.

## Count prediction

From the repository root:

```sh
python3 karthik/mission4.py predict
```

## Board runs

Identify physical ports first with `python3 board_link.py ports`. Keep the
Arduino serial monitor closed. Port names are machine-specific. The expected
settings are 16 kHz, antialias filter enabled, int16 little-endian, S=1.0,
480-sample window, 320-sample hop, 512-point FFT, 40 log-mel outputs, 320
samples per packet, and `speed=1`.

For a full feature-enabled stream and loss-free dataset export:

```sh
python3 karthik/mission4.py --port PORT --baud 921600 stream --speed 1 --export-dataset
```

The script refuses dataset export unless the board summary, packet/sample
counts, input and return CRC counters, feature count, and loss counters all
pass. It drops frames that cross clip boundaries. Expected output is saved as
`mission4_feat_PORT_speed1p0.json`, the raw capture `.npz`, and
`team14_mission4_dataset.npz`.

For the required deliberate skip case:

```sh
python3 karthik/mission4.py --port PORT --baud 921600 stream --speed 1 --skip 10 11 200
```

For speed limits, run explicit candidate speeds. Test both feature-on and
feature-off, on both physical ports. The sweep stops at the first run with
loss or an incomplete summary:

```sh
python3 karthik/mission4.py --port PORT --baud 921600 sweep --speeds 1 1.25 1.5 2 3 4
python3 karthik/mission4.py --port PORT --baud 921600 sweep --features-off --speeds 1 1.25 1.5 2 3 4
```

Each full-dataset speed run lasts about 144 seconds at `speed=1`; higher speeds
may finish sooner but can lose data. Record the fastest *tested* zero-loss
setting. If the coarse sweep finds a failing speed after a passing speed, the
script performs four binary-refinement runs in that interval. Add more
refinements or provide a finer explicit speed list when tighter precision is
needed. If every supplied speed passes, the result is only a lower bound; add
higher candidates to find the limit.

## Data labeling policy

The board's `first_sample` counts samples received. When a whole input packet
is skipped, that counter becomes compressed and subsequent `first_sample`
values would point earlier in the original concatenated audio. The script
uses the known skipped sequence numbers and 320-sample packet lengths to
restore the original sample timeline. It retains both corrected
`first_sample` and raw `board_first_sample`. It drops feature windows crossing
a known packet-loss seam and any window that spans two source clips. If a
loss is detected but its packet position is unknown, the run is ineligible
for dataset export; the script never guesses labels after an unlocated gap.

The canonical dataset is generated only from a complete zero-loss run. The
skip capture is diagnostic and must not be mixed into the final dataset.
