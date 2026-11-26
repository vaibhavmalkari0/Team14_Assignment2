# Mission 5 handoff — remaining board work

Laptop feature references are generated. Mission 5 is not complete until the
four board captures, comparisons, heat maps, classifier results, and a
numbers-based design choice are produced. No physical serial devices were
available during this preparation. This note tells the next person exactly
what to do when the board is available.

## Work already prepared

- `mission5.py prepare` creates original-float32 and exact-wire-quantized
  NumPy feature arrays for every Team 14 clip and setting, plus laptop-only
  nearest-centroid test baselines.
- `mission5.py capture` performs a full real-time board capture for one
  setting and saves its configuration, counters, raw frames, and per-clip
  feature matrix. It marks a capture complete only when all expected samples
  and features arrive without CRC, sequence, length, or duplicate errors.
- `mission5.py analyze` produces per-band/per-class mean and worst absolute
  differences, heat maps, and nearest-centroid results.
- The same fixed stratified split is used for every setting: 16 train clips
  and 8 test clips per class. Standardization uses the training laptop clips
  only. No clip's frames are split across train and test.
- The shared sketch was not edited. No Mission 5 firmware source change is
  required; each condition changes the parameters of the existing `STREAM`
  command. However, the optimized Mission 3 feature firmware must be built and
  numerically verified before the final domain-shift result is trusted.

## Board/setup actions

1. Confirm current Git revision and build/upload the Mission 3-verified sketch
   with its optimized `features.h`. Record the revision, board package, CPU,
   flash/PSRAM options, flash mode, and other actual Arduino Tools settings.
2. Connect the board. Identify its physical USB-UART bridge and native USB
   port using `python3 board_link.py ports` and ping/info; port names vary.
   Close Arduino Serial Monitor/Plotter. Use the verified UART baud for the
   bridge; native USB does not use UART baud.
3. From the repository root, prepare laptop references:

   ```sh
   python3 "mission 5/mission5.py" prepare
   ```

4. Use the **same physical port** and firmware revision for these four
   full-dataset captures. Each lasts about 144 seconds at speed 1.0:

   ```sh
   python3 "mission 5/mission5.py" capture --config baseline_i16 --port PORT --baud 921600
   python3 "mission 5/mission5.py" capture --config int8_s1 --port PORT --baud 921600
   python3 "mission 5/mission5.py" capture --config int8_s05 --port PORT --baud 921600
   python3 "mission 5/mission5.py" capture --config 8k_unfiltered_i16 --port PORT --baud 921600
   ```

   Replace baud if the chosen connection requires it. Record which physical
   port was used. Do not compare captures from different firmware revisions
   without documenting the change.

## Effective hardware settings per capture

Every setting uses `nfft=512`, `mels=40`, `mfcc=0`, `feat=True`, `store=none`,
`speed=1.0`, and 320 samples per packet. Vary these parameters exactly:

| Config | fs | fmt | scale | win | hop | Input made with |
|---|---:|---|---:|---:|---:|---|
| baseline_i16 | 16000 | i16 | 1.0 | 480 | 320 | anti-alias filter on |
| int8_s1 | 16000 | i8 | 1.0 | 480 | 320 | anti-alias filter on |
| int8_s05 | 16000 | i8 | 0.5 | 480 | 320 | anti-alias filter on |
| 8k_unfiltered_i16 | 8000 | i16 | 1.0 | 240 | 160 | filter off; compare to filtered laptop reference |

The anti-alias filter is applied on the laptop in `team_audio.get_clip()`
before downsampling/packing; this board setup receives already sampled audio.
No additional board filter switch is needed. S=0.5 has known clipping from
Mission 2; `settings.json` reports exact clip/sample counts from regenerated
Team 14 data and must be cited when interpreting that condition.

## Acceptance and next steps

- Each capture JSON must say `complete_zero_loss: true`; expected packet,
  sample, feature, board-summary and return-CRC counts must match. Failed raw
  evidence is saved, but the capture command exits with an error and `analyze`
  refuses it.
- All four captures must exist exactly once in `mission 5/artifacts/`. If
  recapturing, move old artifacts out of the analysis folder or remove them
  only after preserving the evidence, because analyze deliberately rejects
  multiple captures for one setting.
- Run analysis:

  ```sh
  python3 "mission 5/mission5.py" analyze
  ```

- Review `feature_difference_summary.json`,
  `feature_differences_per_band_class.csv`, all PNG heat maps, and
  `nearest_centroid_results.json`. Report mean and worst dB error by class and
  band, laptop and board accuracy on the same held-out clips, and clipping for
  each setting.
- Update `MISSION5_REPORT.md` with measured evidence and choose a shipped
  setting using those results. Mission 2's higher int16 SQNR makes it an
  initial candidate only; it does not settle the Mission 5 classifier/domain
  shift decision.

## Expected generated artifacts

- `artifacts/laptop_references.npz`, `artifacts/settings.json`,
  `artifacts/laptop_classifier_results.json`
- `artifacts/board_<setting>_<port>.npz` and matching `.json` for all four
  settings
- `artifacts/feature_differences_per_band_class.csv`
- `artifacts/feature_difference_summary.json`
- `artifacts/nearest_centroid_results.json`
- Eight per-class/per-band heat maps under `artifacts/plots/`
- Updated report with hardware revision/settings, actual results, and final
  design decision
