# Mission 3 handoff — remaining work

This note is for the next person or agent continuing Mission 3. The requested
software work is staged in `sumadhwa/`; the board-dependent portion has not
been completed. Do not report Mission 3 as passed until the hardware evidence
below is collected and saved.

## Current workspace state

- `sumadhwa/mission3.py` implements the NumPy log-mel/MFCC reference, six-class
  plot generation, and a 10-second board capture with same-quantized-input
  comparison. It saves capture `.npz` and summary `.json` files in this folder.
- `sumadhwa/features.h` is a radix-2 FFT implementation intended to replace
  the slow direct DFT while preserving the starter's `FeaturePipeline` API.
- `sumadhwa/MISSION3_REPORT.md` contains the report draft, predictions, known
  evidence, and pending hardware section.
- The shared starter files were not changed. The optimized header is not yet
  integrated into or compiled with the board sketch.
- At the time this handoff was written, `python3 board_link.py ports` listed
  no serial devices. No new board measurements or code tests were run.
- The required 512-point FFT LLM estimate is already in
  `vaibhav/mission1/mission1_llm_log.md`: 44,594 cycles (about 0.186 ms at
  240 MHz) for the FFT kernel. It is an estimate, not a full feature-pipeline
  measurement.

## Known prior failure

`vaibhav/handoff/VAIBHAV_HANDOVER.md` records the required one-second starter
test on the COM UART port at 921600 baud: 16 kHz int16, scale 1, 480-sample
window, 320-sample hop, 512 FFT, 40 mel bands, `feat=True`, `store="none"`,
`speed=0`, and 320 samples per packet. That attempt returned **6 of 49**
features, reported 43 missing and zero bad return CRCs, and produced no board
summary after 11.416 seconds. This is historical, student-reported evidence;
it has not been reproduced in this workspace. Do not treat it as a successful
throughput measurement or assume its root cause.

## Required order when the ESP32 is available

1. **Identify the board and ports.** Run `python3 board_link.py ports`, then
   `info`/`ping` on each connected port. Port names can change. Identify the
   USB-UART bridge (COM) and native USB physically; do not rely on an old COM
   number. Close Arduino Serial Monitor/Plotter before opening the port.
2. **Record the current revision and starter settings.** Use the known board
   setup from `srijan/SRIJAN_HANDOVER.md` (ESP32-S3 N16R8, ESP32 Arduino 3.x,
   240 MHz, 16 MB flash, OPI PSRAM, 921600 UART). Verify the actual Tools
   settings before upload and capture them for the final record.
3. **Reproduce the starter failure before optimization.** With the starter
   `features.h`, run the exact one-second case above. Record elapsed time,
   returned feature shape, `lost_features`, `bad_crc_back`, board summary,
   sequence/CRC/sample counts and port. If it still fails, preserve the
   failure and investigate sender/receiver timing, serial buffering, compute,
   and summary handling separately. A larger timeout alone is not evidence of
   a fix.
4. **Build and upload the optimized implementation.** Integrate
   `sumadhwa/features.h` with the board sketch for the upload. Keep the source
   in this separate folder as the authoritative work copy; if a temporary
   shared-sketch replacement is used, record it and restore or clearly retain
   the intended final version afterward. Verify compilation and record the
   build/board settings.
5. **Verify numerical parity and baseline timing.** Run the 10-second 16 kHz
   int16 baseline at `speed=1` on both COM and native USB with features on.
   `mission3.py board --port PORT --baud 921600 --seconds 10 --speed 1
   --config baseline` captures features and compares them with NumPy over the
   exact decoded int16 stream. Save the JSON/NPZ outputs. Pass requires all
   expected frames, a board summary, and maximum absolute log-mel difference
   **≤ 0.05 dB**. Record mean and max difference, compute time mean/max, lag
   mean/max, all board counters, and elapsed time. At baseline, a continuous
   10-second stream predicts 499 frames.
6. **Measure the requested alternate configuration.** Run
   `mission3.py board --port PORT --baud 921600 --seconds 10 --speed 1
   --config mfcc13` on both ports. This uses a 400-sample (25 ms) window,
   160-sample (10 ms) hop, 512 FFT, and 13 MFCC outputs. Record compute time
   and returned bytes/s. The hop allows 10 ms per frame. The report's
   predicted output rates are 5,200 feature-value B/s and approximately
   7,300 wire B/s (including the 8-byte metadata and 13-byte framing per
   feature frame); replace predictions with measured rates.
7. **Find the pipe/compute limits.** Measure feature-off and feature-on
   throughput/speed separately on COM and native USB. Increase offered speed
   until loss occurs; record the highest zero-loss setting and the first
   failing setting, plus packet/sample/frame counters and CRCs. Include a
   feature-on 10-second real-time run's `compute_us` and `lag_s`. Explain
   whether input transport, feature compute, or output transport limits each
   case. Do not infer feature-on results from the old receive-only throughput
   numbers.
8. **Update the report and hand off artifacts.** Put raw `.npz` and `.json`
   captures in `sumadhwa/`; update `MISSION3_REPORT.md` with the actual values,
   analysis, remaining caveats, tested revision, port identity and Tools
   settings. Reconcile any conflicting older handover claims. Include the
   final feature header and any required sketch changes in the handoff.

## Pass criteria checklist

- [ ] Reproduced starter one-second case and preserved its complete result or
  diagnosed failure, without hiding missing output.
- [ ] Optimized sketch builds and runs on the target board.
- [ ] Baseline 10-second feature run complete on both physical ports; summary
  present, no unaccounted missing features.
- [ ] NumPy comparison uses the same transmitted/decoded quantized samples;
  max log-mel error is at most 0.05 dB.
- [ ] 25 ms / 10 ms / 13-MFCC results recorded, including returned bytes/s.
- [ ] Feature-off and feature-on speed limits measured on both ports; fastest
  verified zero-loss speed reported.
- [ ] Timing (`compute_us`, `lag_s`), board/host loss counters, and port/board
  settings recorded in the report and raw artifacts saved.

Until these boxes are supported by saved hardware evidence, label Mission 3
**software prepared; hardware verification pending**.
