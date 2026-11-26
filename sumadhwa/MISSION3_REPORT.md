# Mission 3 — Features on the board

**Team 14 — Saura · Separate Sumadhwa work area**  
**Report status:** NumPy reference, plotting workflow, board capture workflow, and optimized C++ implementation prepared. Live-board timing, feature parity, throughput, and loss measurements remain unverified because no serial device was available in this workspace. This is not a claim that the complete hardware mission has passed.

## 1. Aim

Implement the prescribed log-mel/MFCC pipeline, reduce the board's feature computation cost, and measure whether the ESP32-S3 can keep up with real-time audio while returning complete feature frames. Compare the board against NumPy using identical quantized input, within 0.05 dB for log-mel outputs.

## 2. Background

The shared starter in `doorbell_board_starter/features.h` computes a direct DFT. For the baseline configuration it evaluates 257 output bins × 480 window samples = **123,360 cosine calls and 123,360 sine calls per frame**, in addition to the mel calculation. The new `features.h` uses an iterative radix-2 FFT; bit-reversal indices and twiddle factors are prepared once in `begin()` and reused for each frame.

The reference follows README section 5: whole frames only; symmetric `np.hanning`; zero-pad to a power-of-two FFT; one-sided power `|X|²/nfft`; HTK mel triangles from 20 Hz to Nyquist; `10 log10(max(power, 1e-10))`; optional orthonormal DCT-II. NumPy and board comparisons must use the same decoded int16 samples, not the original unquantized audio.

The existing Mission 1 LLM log records an ESP-DSP 512-point complex FFT estimate of 44,594 cycles, or about **0.186 ms at 240 MHz**. That is an FFT-kernel estimate, not a measurement of the full feature pipeline; windowing, mel filters, and output handling add work.

## 3. Prediction

| Configuration | Frames/s | Compute budget/frame | Feature values/frame | Value bytes/s | Estimated wire bytes/s |
|---|---:|---:|---:|---:|---:|
| 30 ms / 20 ms, 40 log-mel | 50 | 20 ms | 40 float32 | 8,000 | 9,050 |
| 25 ms / 10 ms, 13 MFCC | 100 | 10 ms | 13 float32 | 5,200 | 7,300 |

Wire rate includes 8 bytes of `first_sample`/`compute_us` metadata plus the 13-byte frame header and CRC per output frame; excludes end/summary messages. The radix-2 implementation should greatly reduce computation relative to the direct DFT, but timing and numerical error must be measured on the target board before either claim is accepted.

For a continuous 10-second stream at the baseline settings, expected complete feature frames are `1 + (160000 - 480)//320 = 499`. For one second, expected frames are 49.

## 4. Method

### NumPy reference and plot

`mission3.py` supplies `features()` and saves a log-mel example for the first clip of each of the six Team 14 classes (`on`, `off`, `stop`, `go`, `_unknown`, `_silence`). It uses `team_audio.get_clip(..., fs=16000, antialias=True)` and preserves the README's framing and scaling conventions.

### Board capture and parity

The board command builds a 10-second payload from the first ten clips in `clip_list(14)`, quantizes to little-endian int16 with S=1.0, streams the actual packed bytes, and makes the NumPy reference from those same decoded bytes. It saves received features, frame indices, `first_sample`, compute times, lag, and the summary JSON. The parity pass condition is a complete frame set and maximum absolute log-mel difference no greater than 0.05 dB.

### Starter failure to reproduce

Vaibhav's handover records a previous one-second COM test at 921600 baud, `speed=0`, which returned **6/49** feature frames, 43 missing, no bad return CRC, and no board summary after 11.416 seconds. This is historical evidence only; it was not independently reproduced here. Mission instructions require reproducing this case before reporting feature throughput.

## 5. Observations

No serial devices were listed by `python3 board_link.py ports` in the current workspace. Consequently, no new ESP32 timing, lag, parity, throughput, or zero-loss speed measurements could be collected. No hardware capture files are included; the scripts are set up to create them when run with the board connected.

Existing historical observation: the starter feature return failed to provide a complete result (6 of 49 frames and no board summary). It must not be described as a completed timing or throughput measurement.

## 6. Analysis

The algorithmic change removes the direct DFT's per-frame trigonometric inner loop and replaces it with radix-2 butterflies. This is a strong reduction in operations, but it does not establish that the full pipeline fits the 20 ms baseline or 10 ms MFCC hop budget. Nor does it establish that serial/USB output is drained fast enough. Those conclusions depend on the required board measurements.

The capture code compares against the transmitted quantized input and records mean/max absolute difference. A run passes only when the expected frames arrive, a board summary is present, and max log-mel error is ≤0.05 dB. Feature-on and feature-off speed sweeps must be recorded independently on both physical ports to identify the bottleneck. COM port numbers are dynamic; identify the device by `board_link.py ports` and physical connection rather than assuming a port name.

## 7. What we learnt

- The starter DFT performs 123,360 `cosf` and the same number of `sinf` evaluations per baseline frame.
- A radix-2 FFT with precomputed twiddles is the chosen optimization and retains the handout's feature definition.
- The board-side results are still necessary: compile success, ≤0.05 dB parity, compute time, lag, returned bytes/s, and complete loss-free captures cannot be inferred from source code.
- Existing Mission 1 logs already contain the required LLM FFT estimate; Mission 3 should reference that entry rather than invent a new measurement.

## 8. LLM log

The pre-existing `vaibhav/mission1/mission1_llm_log.md` records the question and estimate: 44,594 cycles for an ESP-DSP 512-point float32 complex FFT, approximately 0.186 ms at 240 MHz. The log caveat correctly says that this excludes some or all full-pipeline work. The new implementation was prepared with AI assistance; the team must follow the assignment's LLM policy and disclose this assistance accurately. The report does not claim the code was independently authored or that hardware tests were run.

## Required hardware closeout

1. Run the 1-second starter reproduction on COM at 921600 baud and preserve all counters and the summary/failure.
2. Build/upload the sketch using `sumadhwa/features.h`; run baseline 10 seconds at `speed=1` on both COM and native USB.
3. Run 25 ms / 10 ms / 13 MFCC on both ports and record compute time and returned byte rate.
4. Verify complete features and summary; compare the board with same-quantized-sample NumPy output and confirm max error ≤0.05 dB.
5. Measure feature-off and feature-on maximum zero-loss speeds on both ports. Include `compute_us`, `lag_s`, packet/sample counters, feature counts, CRCs, and elapsed time.
6. Save the resulting `.npz` and `.json` files beside this report and update observations, analysis, and status from measured evidence.
