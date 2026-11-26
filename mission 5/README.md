# Mission 5 — Laptop vs board

This folder contains the Mission 5 analysis workflow and hardware handoff. It
does not edit the shared sketch. The board firmware already accepts the audio
format and feature parameters used here; each condition is selected with the
existing `STREAM` command through `board_link.py`.

See `MISSION5_HANDOFF.md` for the board setup record, exact capture settings,
acceptance criteria, and future completion checklist.

## Settings compared

| Name | Laptop reference | Board input | Format / scale | Window / hop |
|---|---|---|---|---|
| `baseline_i16` | 16 kHz, antialias on, original float32 | same filtered audio, int16 | i16 / 1.0 | 480 / 320 |
| `int8_s1` | 16 kHz, antialias on, original float32 | same filtered audio, int8 | i8 / 1.0 | 480 / 320 |
| `int8_s05` | 16 kHz, antialias on, original float32 | same filtered audio, int8 | i8 / 0.5 | 480 / 320 |
| `8k_unfiltered_i16` | 8 kHz, antialias on, original float32 | 8 kHz without antialiasing, int16 | i16 / 1.0 | 240 / 160 |

All conditions use `nfft=512`, 40 mel bands, and board feature output. `S=0.5`
is the smaller int8 scale reported in Mission 2 and is expected to clip some
samples; Mission 5 measures the resulting feature and classifier effect.

## Workflow

From the repository root, first generate laptop references for all 144 clips:

```sh
python3 "mission 5/mission5.py" prepare
```

Then identify the physical port with `python3 board_link.py ports`, close
Arduino Serial Monitor/Plotter, and capture all settings on the same selected
port so the analysis has one capture per condition. Each capture is a 144 s
real-time stream and is rejected for analysis unless it has a complete summary,
zero packet/CRC errors, full sample and feature counts, and 49 retained frames
per clip after dropping clip-boundary frames.

```sh
python3 "mission 5/mission5.py" capture --config baseline_i16 --port PORT --baud 921600
python3 "mission 5/mission5.py" capture --config int8_s1 --port PORT --baud 921600
python3 "mission 5/mission5.py" capture --config int8_s05 --port PORT --baud 921600
python3 "mission 5/mission5.py" capture --config 8k_unfiltered_i16 --port PORT --baud 921600
```

Use the actual baud required by the port; native USB ignores UART baud, while
the UART bridge should use the verified Mission 3/4 setting. Mission 3's
optimized feature firmware must be installed and numerically validated before
the board features are treated as final evidence. Mission 5 itself requires no
new firmware source change; each capture changes `fs`, `fmt`, `scale`, `win`,
and `hop` as shown above.

After all four captures pass:

```sh
python3 "mission 5/mission5.py" analyze
```

Outputs go into `mission 5/artifacts/`: laptop references, per-setting board
captures and summaries, per-band/per-class difference CSV, overall comparison
JSON, eight heat maps, and nearest-centroid results. The classifier uses
per-clip mean and standard deviation, trains on 16 clips per class and tests on
the same held-out 8 clips per class across every configuration. Standardization
uses training clips only.

The laptop-only held-out classifier baselines are also saved by `prepare` to
`artifacts/laptop_classifier_results.json`; board test accuracy is added by
`analyze` after successful captures.

## Comparisons and interpretation

For each setting the script compares board features to the original float32
laptop reference and to NumPy features from the exact quantized samples sent
to the board. This separates signal/quantization domain shift from board
implementation error. In the 8 kHz condition, the laptop domain reference is
filtered 8 kHz audio while the board receives unfiltered 8 kHz audio; a second
comparison against NumPy on the same unfiltered quantized samples isolates
board parity.

The final design choice must use measured difference, clipping, and classifier
results. Until board captures exist, the report's int16 choice is only a
provisional candidate based on Mission 2 SQNR/storage evidence, not a completed
Mission 5 conclusion.
