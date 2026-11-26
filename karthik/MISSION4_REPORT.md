# Mission 4 — Nothing lost

**Team 14 — Saura · Karthik work area**  
**Status:** Count predictions and loss-aware dataset/export code are prepared. Mission 4's physical board runs are pending. No full-stream, deliberate-skip, speed-limit, or labelled hardware dataset result is claimed. The earlier Mission 1 handover documents a feature-return failure (6/49 frames); Mission 3 hardware verification should be resolved before relying on returned board features.

## 1. Aim

Account for audio packets, samples, and feature frames across all 144 Team 14 clips; detect deliberate and observed loss; ensure a packet gap cannot silently shift clip labels; export a labelled feature dataset from a verified zero-loss run; and document its uses and limits.

## 2. Background

Team 14 has 144 one-second, mono clips: 24 examples each of `on`, `off`, `stop`, `go`, `_unknown`, and `_silence`. Mission 4 uses the storage-tested baseline: 16 kHz, antialias filtering enabled, int16 little-endian, scale 1.0, 320 samples per input packet, 480-sample feature window, 320-sample hop, 512-point FFT, 40 log-mel bands, and real-time speed 1.0.

An input sequence gap detects missing packets; CRC counters detect corrupted packets. They are different checks. The board's `first_sample` advances by samples it received, so after a missing packet it no longer matches positions in the original concatenated clips. Mapping those compact positions directly to clip IDs would shift labels after the gap. The script corrects positions from known skipped sequence IDs and refuses to export a dataset if a loss position is unknown or any full-stream integrity counter fails.

Frames that overlap two source clips are excluded because a single clip ID would be ambiguous, even when adjacent clips share a class. This gives a consistent one-label-per-frame rule.

## 3. Prediction

| Quantity | Expected result |
|---|---:|
| Clips / source classes | 144 / 6 |
| Samples per clip / all clips | 16,000 / 2,304,000 |
| Int16 payload | 4,608,000 bytes |
| Data packets (320 samples each) | 7,200 |
| Board `frames_ok`, including END | 7,201 |
| Continuous feature frames, `1 + (N-win)//hop` | 7,199 |
| Feature frames crossing clip boundaries | 143 |
| Dataset rows after dropping clip-straddling frames | 7,056 |
| Expected labelled frames per class | 1,176 (49 per clip) |

For `skip=(10, 11, 200)`, predicted missing audio is 960 samples / 1,920 int16 bytes; 7,197 data packets are sent; the board should report 3 sequence gaps, 2,303,040 samples, and 7,198 valid received frames including END. With features on, the host expects 7,199 timeline frames while the board's compact received stream should produce 7,196 feature frames. The two contiguous skips form one gap seam; packet 200 forms a second seam. These are predictions to compare with the board result, not observations.

The board's counter does not jump to the original timeline after a gap: after skipped packets 10 and 11, its `first_sample` is 640 samples behind the original audio coordinate; after skipped packet 200 it is 960 samples behind. It stays monotonic in the compact received stream. The labeler adds those known offsets back. In the skip diagnostic, two feature windows (one at each compact gap seam) are predicted to mix audio across missing regions and are dropped, in addition to the 143 source-clip straddles; predicted labelled rows are therefore 7,051. This is also a prediction, not a measured skip result.

## 4. Method

`mission4.py` builds all clips in `team_audio.clip_list(14)` order with `antialias=True`, quantizes/ packs the full concatenation as int16 with S=1, and streams through the existing `Board.stream` interface. It records host packets, board summary counters, input/return CRCs, samples, feature count, elapsed time, and whether the summary arrived.

The frame-labeler preserves the board's raw `board_first_sample`, adds back known omitted packet samples to create corrected timeline `first_sample`, and drops any feature crossing a known packet-loss seam. It then uses corrected frame positions and `clip_list(14)` to assign labels and IDs. Any frame whose 480-sample extent crosses a one-second clip boundary is dropped. Final dataset export is allowed only for an unskipped full stream with a board summary, exact packet/sample/frame counts, no input gaps, bad CRCs, bad lengths, duplicates or return CRC errors, and exactly 7,056 labelled rows.

Speed sweeps are explicit and stop at the first loss or incomplete run. The same sweep must be performed with features on and off, on both COM and native USB. Each full dataset run takes approximately 144 seconds at real-time speed.

## 5. Observations

No physical serial device was exposed in this workspace when checked. Therefore there are no measured Mission 4 board counters, no actual skip result, no COM/USB speed limits, no final dataset, and no measured per-class frame counts. The expected counts above come from the dataset dimensions and formulas only.

After a successful run, `mission4.py` writes a run JSON and raw capture NPZ in this folder. With `--export-dataset`, it writes `team14_mission4_dataset.npz` containing `features`, `label`, `clip_id`, corrected `first_sample`, raw `board_first_sample`, and `frame_number`.

## 6. Analysis

The one-second clip duration (16,000 samples) is divisible by the 320-sample hop. A continuous stream therefore has regularly aligned clip boundaries. One feature start lies 160 samples before each boundary and its 480-sample window crosses it; dropping 143 such frames leaves 49 clean frames per each of the 144 clips, or 1,176 per class.

In a deliberate skip run, two adjacent omitted packets (10 and 11) collapse into one discontinuity in the board's received-sample timeline; packet 200 creates another. The corrected timeline restores 320 samples for each skipped sequence position after its seam. The frame that combines samples from both sides of a seam is not valid and is dropped. This correction is only possible because the skipped sequence numbers are known. For an unlocated natural loss, the board summary gives a count but not positions, so that run is rejected for labeling rather than allowing labels to drift silently.

The requested fastest zero-loss speeds, input buffer behavior, and possible COM overload effects cannot be concluded without the feature-on and feature-off measurements on both physical ports. A CRC-clean result alone is insufficient if sequence, sample, or feature counts disagree.

## 7. What we learnt

- Sequence gaps, CRC failures, sample counts, and missing feature frames measure different failure modes and must be reported separately.
- The board's `first_sample` is a received-sample coordinate. Known packet sequence gaps must be restored before using it against the original clip list.
- Dataset rows must have an unambiguous source clip. This workflow drops clip-boundary frames and packet-seam frames.
- A dataset is exported only after a complete, zero-loss run; the deliberate skip capture is for accounting evidence, not training data.
- Board verification remains a prerequisite for claiming Mission 4 complete.

## 8. LLM log

AI assistance was used to prepare the accounting workflow, label correction, and report draft. The team must disclose this work accurately in the final consolidated LLM log and review/understand the submitted code. This report does not claim that hardware experiments or dataset generation were performed.

## Hardware closeout record

Fill these values from saved run JSONs; do not substitute predictions:

| Run | Port identity | Speed | Host packets | `frames_ok` | `seq_gaps` | Input bad CRC | Samples | Expected/received features | Return bad CRC | Summary present |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Full, features on | Pending | 1.0 | Pending | Pending | Pending | Pending | Pending | 7199 / pending | Pending | Pending |
| Skip (10, 11, 200) | Pending | 1.0 | 7197 predicted | 7198 predicted | 3 predicted | Pending | 2,303,040 predicted | 7199 / 7196 predicted | Pending | Pending |
| Highest zero-loss, features off | COM | Pending | Pending | Pending | Pending | Pending | Pending | n/a | Pending | Pending |
| Highest zero-loss, features on | COM | Pending | Pending | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Highest zero-loss, features off | Native USB | Pending | Pending | Pending | Pending | Pending | Pending | n/a | Pending | Pending |
| Highest zero-loss, features on | Native USB | Pending | Pending | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
