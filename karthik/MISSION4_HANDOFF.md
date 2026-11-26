# Mission 4 handoff — pending hardware work

This note is the continuation checklist for Mission 4. The loss-accounting and
dataset code is prepared in `karthik/mission4.py`; the board-dependent evidence
is **not complete**. At the time this was written, `python3 board_link.py ports`
listed no serial devices. No measurements or labelled board dataset have been
fabricated.

## Current status

- Count predictions are recorded in `expected_counts.json`.
- Stream, skip, counter-summary, sample-timeline correction, clip labeling,
  dataset export guard, and speed-sweep code are in `mission4.py`.
- The report, data card, and usage instructions are in this folder.
- The final `.npz` dataset and run evidence do not exist yet; they require the
  ESP32-S3 feature stream to work and produce complete feature frames.
- Mission 3's prior recorded feature-return attempt was incomplete (6/49
  frames, no board summary). If that issue persists, resolve Mission 3 first;
  do not label a partial feature stream as Mission 4 success.

## When the board is connected

1. Run `python3 board_link.py ports`; identify the native USB port and USB-UART
   bridge physically because COM names are not stable. Close Arduino Serial
   Monitor/Plotter. Record board revision and actual Arduino Tools settings.
2. On the COM/UART bridge at 921600 baud, run the complete 144-clip real-time
   feature stream and export only if all checks pass:

   ```sh
   python3 karthik/mission4.py --port PORT --baud 921600 stream --speed 1 --export-dataset
   ```

   Preserve the JSON and raw capture NPZ. Pass criteria: summary present;
   7,200 host data packets; board `frames_ok=7201` including END; 2,304,000
   samples; 7,199 expected and received feature frames; `seq_gaps=0`, input
   `bad_crc=0`, `bad_len=0`, `dup=0`, return `bad_crc_back=0`; no missing
   features; exactly 7,056 labelled rows after boundary-frame removal; 1,176
   rows per class; finite 40-value features and valid clip IDs.
3. Run the deliberate loss case and preserve its JSON and capture:

   ```sh
   python3 karthik/mission4.py --port PORT --baud 921600 stream --speed 1 --skip 10 11 200
   ```

   Confirm 7,197 data packets sent, `seq_gaps=3`, 2,303,040 samples received,
   and a board summary with 7,198 accepted frames including END. Compare
   expected/received feature counts. Explain from recorded `first_sample`
   values that the board counts received samples only: positions after the
   first two omissions are 640 samples behind the source timeline; after
   packet 200 the offset is 960 samples. The script restores these known
   offsets, drops windows across the two packet-gap seams, and does not export
   this diagnostic run as training data.
4. Find feature-on and feature-off loss limits on **both** physical ports:

   ```sh
   python3 karthik/mission4.py --port PORT --baud 921600 sweep --speeds 1 1.25 1.5 2 3 4
   python3 karthik/mission4.py --port PORT --baud 921600 sweep --features-off --speeds 1 1.25 1.5 2 3 4
   ```

   The sweep refines the last pass/fail interval with four binary steps. If
   all candidate speeds pass, add higher values; if the interval needs tighter
   resolution, add more refinements or a finer speed list. Record the highest
   verified zero-loss setting, the lowest failing setting, and the counters
   for both. Each real-time full-dataset run takes roughly 144 seconds.
5. Update `MISSION4_REPORT.md` and `data_card.md` with **measured** outcomes,
   port identity, Tools settings, speed limits, and paths to evidence. Replace
   pending entries only when the corresponding saved run JSON supports them.
   Keep prediction and observation columns distinct.

## Label and dataset rules

- The final dataset may come only from an unskipped, integrity-clean full run.
- Each row includes `features`, `label`, `clip_id`, corrected absolute
  `first_sample`, raw `board_first_sample`, and `frame_number`.
- Frames crossing either a known packet-loss seam or a source clip boundary
  are excluded. The source clip boundary rule gives 49 rows per one-second
  clip in a loss-free run.
- If a natural loss is detected but its packet location is unknown, do not
  infer corrected labels from the aggregate gap count. The export guard must
  reject the run.
- Keep the skip diagnostic separate from the final training dataset.

## Files expected after hardware closeout

- `mission4_feat_PORT_speed1p0.json`
- `mission4_feat_PORT_speed1p0_capture.npz`
- `mission4_skip_PORT_speed1p0.json`
- `mission4_skip_PORT_speed1p0_capture.npz`
- feature-on/feature-off speed-sweep JSON files for COM and native USB
- `team14_mission4_dataset.npz`
- updated report and data card with measured results

Replace `PORT` in this list with the actual filename generated from the
physical port name. If the tool produces a different name, document the actual
artifact path in the report.
