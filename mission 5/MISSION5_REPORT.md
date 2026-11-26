# Mission 5 — Laptop vs board (domain shift)

**Team 14 — Saura · Mission 5 work area**  
**Status:** laptop references and laptop-only classifier baselines generated; analysis and capture workflow prepared. Board feature captures, board differences/heat maps, cross-domain classifier results, and final ship decision are pending hardware access. This report does not present predicted or missing values as measurements.

## 1. Aim

Measure how board log-mel features differ from laptop features, distinguish input quantization from board implementation error, compare the requested audio settings, and evaluate whether the feature shift changes a nearest-centroid classifier's predictions on held-out clips.

## 2. Background

The baseline is Team 14 audio at 16 kHz with antialias filtering, int16 scale 1.0, 30 ms window, 20 ms hop, 512 FFT and 40 log-mel bands. For the primary comparison, the laptop computes features from original float32 audio and the board computes features from the exact quantized/transmitted signal. A second NumPy reference is computed from those same decoded quantized samples. This separates quantization effects from board feature-math differences.

The required variants are int8 S=1, int8 with a smaller scale (S=0.5, a scale measured in Mission 2), and 8 kHz without anti-alias filtering. The 8 kHz board stream uses a 240-sample window and 160-sample hop (30 ms / 20 ms); its laptop domain reference is the corresponding filtered 8 kHz clip. The same-quantized NumPy comparison uses the board's unfiltered 8 kHz input.

The nearest-centroid classifier uses each clip's mean and standard deviation across its feature frames. Clips, not frames, are split so no frames from one recording appear in both train and test. Feature dimensions are standardized using training clips only.

## 3. Prediction

Mission 2 evidence predicts that int16 S=1 has higher SQNR and no clipping across this dataset. int8 S=1 reduces payload size but adds quantization noise. The smaller int8 S=0.5 scale should increase resolution for quieter samples and clip some loud samples; Mission 2 reported clipping in 78 of 144 clips. Unfiltered 8 kHz should alias out-of-band energy into the feature range. These are expected trade-offs, not Mission 5 measurements.

The classifier split is fixed across all settings: 16 training clips and 8 test clips per class (96 train, 48 test). There are 49 retained frames per clip after excluding the feature frame that straddles each source clip boundary. No accuracy or difference values are predicted here because those depend on the computed feature arrays and final board firmware.

## 4. Method

`mission5.py prepare` computes two laptop feature arrays per setting and all 144 clips: original float32 reference features and features from the exact quantized wire samples. The setting configuration records the anti-alias choice, scale, dtype, window, and hop. Quantized clipping counts are stored in `settings.json`.

`mission5.py capture` concatenates all clips in `clip_list(14)` order and streams one setting to the board at speed 1. It saves raw features, first-sample positions, compute times, lag, board counters, and configuration metadata. It accepts a capture for comparison only if packet, sample, feature, CRC, sequence, and summary checks pass. Continuous-stream feature frames that cross clip boundaries are excluded; each clip must retain 49 frames.

`mission5.py analyze` reports mean absolute and worst absolute difference in dB per band and class for two references: (1) original/filtered float32 laptop features and (2) NumPy features computed on the same quantized input. It creates one class-by-band heat map for each comparison and setting. It then trains the nearest-centroid model with laptop reference features and compares laptop and board predictions on the same stratified held-out clip IDs.

## 5. Observations

Laptop reference generation was run for all 144 clips and four settings. It produced 49 reference frames per clip in each condition. Quantization at 16 kHz int8 S=0.5 clipped **2,860 samples across 78 clips**; the other three generated configurations had zero clipping. These are local preprocessing results, not board measurements.

Laptop-only nearest-centroid baseline accuracy on the fixed 48-clip held-out set is 68.75% (33/48) for the 16 kHz original-float reference used by the baseline and both int8 settings. The filtered 8 kHz laptop reference scores 58.33% (28/48). These are small fixed-split baselines, not generalization estimates; all per-class scores and confusion matrices are saved in `artifacts/laptop_classifier_results.json`.

No physical serial ports or Mission 5 board capture artifacts were available in the current workspace. Therefore no board-to-laptop dB differences, board heat maps, board classifier accuracy, or measured final configuration choice can yet be reported. See `MISSION5_HANDOFF.md` for the required board work and evidence paths.

## 6. Analysis

The analysis produces separate comparison metrics because a single board-versus-float difference combines at least quantization and feature implementation effects. Board versus same-quantized NumPy isolates the feature implementation component. Board versus original float32 laptop features expresses total domain shift for the actual streamed condition.

Classifier evaluation uses per-clip summaries to avoid treating correlated frames from one clip as independent samples. The same 96/48 split is used for all four settings, and standardization parameters come from only the 96 laptop training clips. Mission 2 quantization results make int16 a reasonable provisional candidate, but Mission 5's requested classifier and board-domain measurements are needed before a final choice is justified.

## 7. What we learnt

- Four setting configurations and the full laptop/board analysis workflow are prepared.
- The smaller int8 scale is S=0.5, selected because Mission 2 measured it; its clipping must be included in the final decision.
- The 8 kHz no-filter case is compared to filtered 8 kHz laptop features, with a same-input NumPy reference to separate board error from aliasing/quantization.
- The classifier is split by clip and uses train-only standardization; all settings share a fixed test split.
- Board timing, parity, difference, accuracy, and shipping choice remain pending until valid captures are available.

## 8. LLM log

AI assistance was used to prepare the Mission 5 capture and analysis workflow and this report draft. Record that assistance accurately in the team's consolidated LLM log, review the generated code, and make sure each team member can explain the formulas, split, and results. No board experiment or independent hardware measurement is claimed here.

## Hardware measurement record

Fill from `mission 5/artifacts/board_*.json` after captures complete.

| Setting | Port / firmware revision | Feature frames | Summary / loss status | Mean / worst abs dB vs original laptop | Mean / worst abs dB vs same-quant NumPy | Laptop / board test accuracy |
|---|---|---:|---|---|---|---|
| 16 kHz i16 S=1 filtered | Pending | Pending | Pending | Pending | Pending | Pending |
| 16 kHz i8 S=1 filtered | Pending | Pending | Pending | Pending | Pending | Pending |
| 16 kHz i8 S=0.5 filtered | Pending | Pending | Pending | Pending | Pending | Pending |
| 8 kHz i16 S=1 unfiltered (laptop reference filtered) | Pending | Pending | Pending | Pending | Pending | Pending |

**Final shipping setting:** Pending measured comparisons and classifier results.
