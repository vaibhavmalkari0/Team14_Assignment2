# Sumadhwa — Mission 3 work area

This folder contains the Mission 3 implementation and evidence workflow. The
assignment source remains at the repository root; this is a separate working
package, and it does not replace or edit the shared starter files.

## Contents

- `mission3.py` — NumPy feature reference, six-class plot generator, and board
  capture/comparison utility.
- `features.h` — radix-2 FFT implementation with the same `FeaturePipeline`
  interface expected by the starter sketch. Copy it over the sketch's
  `features.h` only when ready to build the Mission 3 firmware.
- `MISSION3_REPORT.md` — report following the assignment headings, known
  evidence, and hardware measurement record.
- `MISSION3_HANDOFF.md` — remaining board work, exact run order, pass criteria,
  and current status for the next person continuing this task.

## Commands

Run commands from the repository root. The plotting command saves a log-mel
image for the first clip in each class:

```sh
python3 sumadhwa/mission3.py plot --team 14
```

For each physical port, use the board command at 921600 baud for UART or the
port's normal baud for native USB. Keep the Arduino serial monitor closed.
First capture the starter baseline before replacing the sketch header. Then
upload the sketch using `sumadhwa/features.h` and repeat:

```sh
python3 sumadhwa/mission3.py board --port PORT --baud 921600 --seconds 10 --speed 1 --config baseline
python3 sumadhwa/mission3.py board --port PORT --baud 921600 --seconds 10 --speed 1 --config mfcc13
```

Each run writes an `.npz` capture and a `.json` summary in this folder. The
baseline is 16 kHz int16, 30 ms window, 20 ms hop, 512 FFT and 40 log-mel
outputs. `mfcc13` uses the requested 25 ms window, 10 ms hop and 13 MFCCs.
Repeat both commands on the USB-UART bridge and native USB. Then use the board
API to increase `speed` in separate feature-off and feature-on runs until loss
appears; record the highest zero-loss setting. Do not treat a partial capture
or missing board summary as a successful run.

The plot and capture commands require NumPy and Matplotlib; board commands also
require PySerial. No physical serial device was exposed to the current
workspace, so hardware result files are intentionally not fabricated.
