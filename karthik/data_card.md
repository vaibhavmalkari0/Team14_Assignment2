# Team 14 Doorbell Audio Feature Dataset — Data Card

**Status:** Dataset not yet generated from a verified board run. Values below are the intended configuration and expected counts; replace the marked fields with observed hardware evidence before submission.

## Source and collection

The source is the assignment-provided `team_audio.py` and `speech_pool.npz` for Team 14. It contains 144 one-second mono clips, 24 per class: `on`, `off`, `stop`, `go`, `_unknown`, and `_silence`. Audio is sampled at 16 kHz with anti-alias filtering enabled, quantized to signed little-endian int16 at scale S=1.0, and streamed to the ESP32-S3 in 320-sample packets. The intended stream is real time (`speed=1`), with 480-sample windows, 320-sample hops, 512-point FFT and 40 log-mel outputs. Record the actual board revision, physical port, baud, and Arduino Tools settings in the Mission 4 report.

## Expected composition

The full raw input is 2,304,000 samples (4,608,000 audio bytes) across 7,200 data packets. Continuous feature extraction predicts 7,199 frames. Frames crossing source-clip boundaries are excluded to avoid assigning one frame to two clips, leaving 7,056 rows: 1,176 per class, or 49 per clip. Actual counts must come from the saved, integrity-checked dataset.

## Loss accounting and known issues

The final dataset must be generated only from a full run with a present board summary, 7,200 host data packets, 7,201 board frames including END, 2,304,000 samples, 7,199 received feature frames, and zero sequence gaps, input/return CRC errors, bad lengths, duplicates, or unexplained count differences. Record the measured loss counts and fastest verified zero-loss speed for COM and native USB here: **pending board run**.

The required diagnostic `skip=(10, 11, 200)` omits three known input packets. It is excluded from the final dataset. For that diagnostic, corrected timeline positions add back omitted samples after each known gap, and windows crossing a loss seam are discarded. Unlocated packet loss makes a run ineligible for labeling. The feature-return path had an earlier reported partial result (6 of 49 frames); Mission 3 must establish that the current board feature stream is reliable before these features are used.

## Intended use and limitations

This small, assignment-generated dataset supports the Module 2 streaming, feature, and loss-accounting exercises. It is not a representative field recording, a production doorbell benchmark, or evidence of general speech-recognition performance. `_unknown` and `_silence` are assignment categories, not exhaustive real-world negatives. Clip-boundary and known gap-seam frames are excluded, so the dataset does not evaluate decisions on transitions between adjacent clips. The saved metadata includes the assigned label, clip ID, corrected absolute `first_sample`, raw board `first_sample`, and feature frame number for auditability.
