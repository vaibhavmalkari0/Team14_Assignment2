# Srijan Handover Record — Mission 2

**Team:** 14 — Saura  
**Assignment:** AI255TBD Edge AI, Module 2 — The Doorbell's Ears  
**Hardware owner:** Srijan Kumar GS  
**Handoff:** To the teammate continuing Mission 3; coordinate with Sumadhwa (NumPy reference) and Karthik (dataset and final packaging)  
**Date:** 26 November 2026  
**Status:** Mission 2 Python and hardware experiments passed; both pushes reported successful. Mission 3 feature work is **not** complete.  
**Repository:** https://github.com/vaibhavmalkari0/Team14_Assignment2

## 1. Start here — current status

Mission 2 has established a reproducible audio representation, successful real-time reception and permanent storage on the ESP32-S3. The full 144-second recording was retrieved after a physical power cycle and matched the original laptop payload byte for byte.

The next teammate should reuse this working baseline, rather than repeat the sampling, quantisation or storage experiments unless a regression occurs. The next priority is the unresolved feature-return issue, followed by a matching NumPy reference, feature optimisation and integrated streaming measurements.

| Mission | Status at handover |
|---|---|
| 1 — The pipe | Vaibhav's main throughput results available; feature-return test and other open items in his handover remain unresolved |
| 2 — What to send and where to keep it | Python and hardware experiments completed; final PDF consolidation/review remains |
| 3 — Features on the board | Pending reference implementation, return-path diagnosis, timing and optimisation |
| 4 — Nothing lost | Storage-only loss checks passed; feature-enabled stream, deliberate loss, labels and data card pending |
| 5 — Laptop vs board | Feature comparisons, classifier and final design decision pending |

**Role clarification:** `TEAM_PLAN.md` assigns the Python portion of Mission 2 and later NumPy/classifier work to Sumadhwa, and storage/board feature optimisation to Srijan. The Mission 2 Python and hardware files produced during this session are both under `srijan/mission2/`. This handover does not reassign the remaining tasks or claim that Srijan's whole original workstream is finished. The team should reconcile authorship and ownership in the final role record. Karthik is the planned recipient of the completed board package, but that package still needs Mission 3 work.

## 2. Working audio configuration — reuse this first

| Parameter | Value |
|---|---|
| Team number | `14` |
| Source | `team_audio.py`, `speech_pool.npz` (do not modify) |
| Clip count | 144 mono clips, one second each |
| Classes | `on`, `off`, `stop`, `go`, `_unknown`, `_silence` |
| Clip ordering | `clip_list(14)`; concatenate in returned order |
| Sampling rate | `16000` Hz |
| Anti-aliasing | `True` |
| Representation | Signed little-endian int16 (`<i2`, protocol `i16`) |
| Quantisation scale | `S=1.0`, fixed before hearing the signal |
| Samples per packet | `320` (640 audio payload bytes) |
| Stream speed | `1.0` (real time) |
| Tested port | USB-UART CH343, COM6, 921600 baud |
| Storage during reception | `psram` |
| Storage after SAVE | LittleFS, `/rec.bin` |
| Total samples | 2,304,000 |
| Raw payload rate | 32,000 B/s |
| Total audio bytes | 4,608,000 (4.608 MB, about 4.395 MiB) |
| Reference CRC32 | `0x50527154` = `1347580244` |
| Feature extraction during Mission 2 hardware tests | `feat=False` |

Quantisation uses the assignment's rounding, clipping and reconstruction formula. Import `pack` and `unpack` from `srijan/mission2/quantisation.py`; keep the scale and datatype consistent on both ends. Generate the reference on the same quantised samples (unpack the exact transmitted bytes) for Mission 3; retain original float32 clips for Mission 5.

Why this baseline: at 16 kHz int16, full-dataset mean SQNR was 77.56 dB, minimum 72.92 dB, with zero clipped clips. 48 kHz int16 improved mean SQNR by only 0.05 dB while tripling storage; 8 kHz loses bandwidth, and int8 substantially reduces fidelity. This is a storage-tested baseline, not a final classifier-validated shipping decision. The 5,695 Hz whine is still in-band at 16 kHz; do not claim the 8 kHz anti-alias experiment removed it at 16 kHz.

## 3. Board setup and port reconciliation

| Setting | Working value / note |
|---|---|
| Module | ESP32-S3 N16R8, 16 MiB flash, 8 MiB embedded PSRAM |
| Arduino board | ESP32S3 Dev Module |
| ESP32 Arduino package | 3.3.12 (observed in upload log) |
| CPU frequency | 240 MHz |
| Flash size | 16 MB (128 Mb) |
| PSRAM | OPI PSRAM |
| Upload speed | 921600 |
| USB CDC On Boot | Enabled in original team plan; confirm actual setting before changing USB configuration |
| Flash mode | DIO in boot log; preserve working configuration |
| Partition | Custom sketch-local `partitions.csv`, 8 MiB LittleFS |
| Erase All Flash Before Sketch Upload | Keep disabled to protect existing data, unless a deliberate clean flash is required |
| Python | 3.11.9, project `.venv` |
| Dependencies | numpy, pyserial, matplotlib |

COM numbers change between computers and cable reconnections. Vaibhav used COM5 for UART and COM6 for native USB; in the Mission 2 session **COM6 was the CH343 USB-UART bridge**, as confirmed by `ports`. Do not assume a COM number identifies a physical port. The native USB port was not retested in Mission 2.

From repository root (Windows PowerShell):

```powershell
git pull --ff-only origin main
python --version
# Only create the environment if it does not already exist
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install numpy pyserial matplotlib
python board_link.py ports
python board_link.py --port COM6 --baud 921600 ping
python board_link.py --port COM6 --baud 921600 info
```

Replace COM6 with the actual port. Close Arduino Serial Monitor/Plotter before Python opens the port. Do not reflash or change the partition just to start Mission 3; first check the existing board. Record the actual USB mode, flash mode, partition and remaining Tools settings in the final `tools_settings.txt`.

## 4. Verified Mission 2 evidence

### Sampling and quantisation

| Test | Measured result |
|---|---|
| int8 five-sample round trip | 5 bytes; maximum reconstruction error 0.003937006 |
| int16 five-sample round trip | 10 bytes; maximum reconstruction error 0.000015258789 |
| 48 kHz silence clip 120 | Dominant frequency 5695 Hz |
| 8 kHz unfiltered | Dominant frequency 2305 Hz (exact predicted alias) |
| 8 kHz filtered | Dominant frequency 50 Hz; alias magnitude 204.719757 → 0.472255 |
| Attenuation at 2305 Hz | 52.74 dB |
| Full dataset validation | 144 clips × 3 rates × 6 configurations = 2592 evaluations |
| 16 kHz int16 S=1.0 | Mean SQNR 77.56 dB, minimum 72.92 dB, zero clipping |
| 16 kHz int8 S=1.0 | Mean SQNR 29.34 dB, minimum 24.72 dB, zero clipping |
| 16 kHz int8 S=0.5 | Mean SQNR 31.49 dB, 78/144 clips with clipping |

For the two representative clips: int16 SQNR 78.07 dB (word) and 72.99 dB (silence); int8 at S=1.0 29.85 and 24.78 dB. Silence improved to 42.83 dB at S=0.125 without clipping, but the word clip clipped 4.6% of samples. A silence-only scale is not appropriate for all clips.

### Memory capacity

| Parameter | Original board | After PSRAM and partition configuration |
|---|---:|---:|
| CPU | 240 MHz | 240 MHz |
| Free heap (idle snapshot) | 256208 B | 336060 B (post-partition snapshot) |
| Largest heap block | 204788 B | 278516 B |
| PSRAM size | 0 B | 8388608 B |
| Free PSRAM (idle) | 0 B | 8351220 B |
| Largest PSRAM block (idle) | 0 B | 8257524 B |
| Physical flash | 16777216 B | 16777216 B |
| LittleFS capacity | 1441792 B | 8388608 B |

SRAM at 16 kHz int16: 1 s (32000 B), 3 s (96000 B) and 5 s (160000 B) passed with matching CRC. 6 s (192000 B) failed: `ERR alloc sram want=192000 largest=163828`. Initial theoretical limit was about 6.40 s, allocation-time limit about 5.12 s, and largest successfully tested whole-second duration was **5 s**. No fractional-second maximum was measured.

PSRAM tests:

| Duration | Stored bytes | CRC32 | Outcome |
|---|---:|---|---|
| 10 s | 320000 | `1833511D` | PASS |
| 60 s | 1920000 | `D656CC6E` | PASS |
| 144 s | 4608000 | `50527154` | PASS |

Full 144-second recording left 3632624 B free PSRAM; absolute maximum PSRAM capacity was not measured. The `psram_test.py` script frees RAM after successful tests, so do not expect its buffer to remain available for SAVE.

### Full persistent-storage run

| Metric | Actual result |
|---|---:|
| Data packets | 7200 |
| Board frames_ok (includes end frame) | 7201 |
| Samples received | 2304000 |
| Bytes stored | 4608000 |
| Bad CRC, bad length, seq gaps, duplicates, UART errors, store_full | All 0 |
| Board stream time | 143.989 s |
| SAVE time | 10.317019 s |
| Effective flash write speed (SAVE timing) | 446640.64 B/s |
| LittleFS used after SAVE | 4628480 B |
| Remaining reported LittleFS space | 3760128 B |
| PSRAM CRC and flash CRC before power loss | `50527154` |
| Flash CRC after physical unplug/replug | `50527154` |
| Retrieved bytes after power loss | 4608000 |
| Retrieval time | 50.358 s |
| Retrieval speed | 91505.24 B/s |
| Exact byte comparison | True |
| Mismatched bytes | 0 |

The after-reconnect INFO snapshot showed `stored=0`, `where=none`, free PSRAM 8351220 B, and LittleFS used unchanged at 4628480 B. PSRAM did not survive power loss; the flash file did. The retrieval test compared every byte and therefore provides stronger evidence than CRC agreement alone. The storage tests did **not** exercise feature computation or simultaneous feature returns.

## 5. Shared firmware changes and troubleshooting

### Changes to retain

- `doorbell_board_starter/doorbell_board_starter.ino`: implemented `cmdSave()` with filesystem/buffer checks, 4096-byte chunked writes, incomplete-write detection, flush/close, file length verification, elapsed microseconds and original-buffer CRC. `CRC flash` and `DUMP flash` independently check the saved file.
- `doorbell_board_starter/partitions.csv`: custom partition table; `spiffs` label is used for LittleFS. Keep the working file with the sketch.
- OPI PSRAM enabled in Arduino Tools. This setting is not guaranteed to follow a Git clone.
- `.gitignore` updated to exclude `.venv/`, `__pycache__/`, `*.pyc`, and `team_14_preview.wav`.

Working partition table used in the successful session:

```csv
# Name, Type, SubType, Offset, Size, Flags
nvs,data,nvs,0x9000,0x5000,
otadata,data,ota,0xe000,0x2000,
app0,app,ota_0,0x10000,0x300000,
app1,app,ota_1,0x310000,0x300000,
spiffs,data,spiffs,0x610000,0x800000,
coredump,data,coredump,0xFF0000,0x10000,
```

Do not casually erase flash, resize partitions or overwrite `/rec.bin`; these can destroy the saved reference. SAVE currently overwrites the recording and is not proven atomic under power loss during writing. The verified case was a completed SAVE followed by unplugging.

| Problem encountered | Resolution / lesson |
|---|---|
| PSRAM size 0 | Enabled OPI PSRAM and reuploaded; INFO then reported 8388608 bytes |
| SRAM 192000-byte allocation failed | Contiguous memory available at allocation was only 163828 B; use PSRAM for the full recording |
| LittleFS too small | Custom partition layout expanded it to 8388608 bytes |
| No PONG after partition upload | Boot log showed `No bootable app partitions in the partition table`; rewrote complete CSV in ASCII, verified board settings and uploaded again; PONG and INFO recovered. Exact original binary/encoding failure was not independently established |
| `PermissionError(13, Access is denied)` | Release COM port (close Serial Monitor/other users), retry; no firmware change required |
| `Hard resetting via RTS pin...` | Normal final upload stage; verified hash means flash write completed, but PING/INFO are still required to confirm runtime boot |
| `ERR SAVE no recording` after fresh boot | Expected negative test; stream data to PSRAM before SAVE |
| Quiet terminal during download | UART transfer of 4608000 B takes at least 50 s at 921600 baud with 8N1; wait for test result rather than interrupting a normal download |

## 6. Reproduction commands and file inventory

Place this handover at `srijan/SRIJAN_HANDOVER.md`. Links below are relative to that location.

| File | Purpose |
|---|---|
| [Mission 2 Python report](mission2/TEAM14_MISSION2_PYTHON_REPORT.md) | Eight-heading experiment report, spectra, SQNR, scale decision |
| [Mission 2 hardware report](mission2/TEAM14_MISSION2_HARDWARE_REPORT.md) | Eight-heading hardware experiment report and troubleshooting |
| [quantisation.py](mission2/quantisation.py) | Reusable int8/int16 `quantise`, `pack`, `unpack` |
| [test_quantisation.py](mission2/test_quantisation.py) | Unit and reconstruction tests; NPZ export |
| [sampling_analysis.py](mission2/sampling_analysis.py) | FFT, aliasing and attenuation; linear/dB spectra |
| [sqnr_analysis.py](mission2/sqnr_analysis.py) | Two-clip SQNR, clipping and waveform plots |
| [dataset_validation.py](mission2/dataset_validation.py) | All 144 clips, configurations and storage comparison |
| [sram_test.py](mission2/hardware/sram_test.py) | SRAM whole-second capacity test |
| [psram_test.py](mission2/hardware/psram_test.py) | PSRAM tests including full dataset |
| [flash_test.py](mission2/hardware/flash_test.py) | Stream, SAVE and pre-power-cycle CRC |
| [persistence_test.py](mission2/hardware/persistence_test.py) | Post-power-cycle dump and exact byte comparison |
| [plots/](mission2/plots/) | Sampling, quantisation, SQNR and storage evidence |
| [results/](mission2/results/) | CSV, NPZ and JSON experiment evidence |
| [Firmware](../doorbell_board_starter/doorbell_board_starter.ino) | Shared sketch |
| [partitions.csv](../doorbell_board_starter/partitions.csv) | Custom LittleFS allocation |
| [features.h](../doorbell_board_starter/features.h) | Starter feature maths; Mission 3 target |
| [board_link.py](../board_link.py) | Host protocol and loss counters |
| [Vaibhav handover](../vaibhav/handoff/VAIBHAV_HANDOVER.md) | Throughput evidence and unresolved Mission 1 items |
| [Team plan](../TEAM_PLAN.md) | Original role assignments and submission requirements |

Known result filenames: `sqnr_results.csv`, `configuration_summary.csv`, `dataset_validation.csv`, `quantisation_test_data.npz`, `psram_test_results.csv`, `flash_test_results.json`, `persistence_test_results.json`. SRAM measurements are preserved in the hardware report and terminal history. See the detailed reports for plot names.

### Quick read-only smoke test

If using the same physical board after handover, verify the saved file before overwriting it:

```powershell
python board_link.py ports
python board_link.py --port COM6 --baud 921600 info
python -c "from board_link import Board; b=Board('COM6', baud=921600); r=b.crc('flash'); print(r); assert r['n']==4608000 and r['crc']==0x50527154; b.close()"
```

Expected CRC result: `{'where': 'flash', 'n': 4608000, 'crc': 1347580244}`. A different physical board may not contain the file; this is not automatically a code regression. Update hard-coded `PORT` in hardware scripts if needed.

### Rerun only if necessary

```powershell
python srijan/mission2/test_quantisation.py
python srijan/mission2/sampling_analysis.py
python srijan/mission2/sqnr_analysis.py
python srijan/mission2/dataset_validation.py
python srijan/mission2/hardware/sram_test.py
python srijan/mission2/hardware/psram_test.py
python srijan/mission2/hardware/flash_test.py
# Unplug all board power, reconnect, check current port, then:
python srijan/mission2/hardware/persistence_test.py
```

Close plot windows when scripts pause at `plt.show()`. `flash_test.py` writes/replaces the saved file; its free-space check may reject a repeat when the old file is already present, even though replacement would fit. Preserve the verified file and use `persistence_test.py` if only retrieval is needed; do not delete existing evidence just to rerun. All commands assume repository root. Tests use real-time audio streaming and may take several minutes. Do not mistake theoretical durations for measured results.

## 7. Current blocker — feature-return pipeline (Mission 3)

Vaibhav's handover recorded an incomplete test: 6 of 49 expected frames arrived, 43 missing, `bad_crc_back=0`, no board summary after 11.416 s. The 960 bytes of feature values are only a partial result, not valid full throughput. Mission 2 left this untouched (`feat=False`).

**Reproduce on the UART bridge at 921600 baud**, using one Team 14 clip and these exact settings:

| Parameter | Value |
|---|---|
| `fs`, `fmt`, `scale` | 16000, `i16`, 1.0 |
| `feat`, `store`, `speed` | True, `none`, 0 |
| `win`, `hop`, `nfft` | 480, 320, 512 |
| `mels`, `mfcc` | 40, 0 |
| `samples_per_packet` | 320 |

Reuse the existing Board API: `b.stream(payload, fs=..., fmt=..., ...)`. The one-second payload is 32000 bytes, 50 data packets plus one end packet, and 49 complete feature frames. Record the entire board summary, received feature shape, `lost_features`, `bad_crc_back`, and elapsed time. The pass condition is **49/49 frames, zero lost_features and a present board summary**; inspect CRC/sequence/sample counts as well. If it still fails, record the baseline, then inspect the slow starter DFT, receive buffer saturation and host reader/summary timeout. Do not assume any single root cause or merely hide loss by increasing the timeout. Try paced `speed=1` as a separate diagnostic, not a replacement for the required reproduction.

Vaibhav also listed open native USB repeat plotting, first-run slowdown measurements, and both-ports-connected repeat evidence. Refer to his handover and coordinate who closes those items; do not mark Mission 1 fully closed on the basis of Mission 2.

## 8. Recommended Mission 3 continuation order

1. Pull latest changes, record the Git revision, identify ports and run the smoke test. Coordinate firmware edits to avoid overlapping changes.
2. Ask and log the required LLM prediction about 512-point FFT timing on ESP32-S3 (Vaibhav already recorded a claim; consult his log). Measure rather than rely on that claim.
3. Reproduce the feature-return blocker above and preserve the starter baseline timing/failure evidence.
4. Implement or obtain Sumadhwa's independent NumPy reference following README section 5 exactly:
   - Whole frames only, `x[k*hop:k*hop+win]`; no implicit padding at signal boundaries.
   - Symmetric Hann (`np.hanning(win)`), zero-pad to 512 initially.
   - One-sided FFT power `abs(X)**2/nfft`.
   - 40 triangular mel filters with edges spaced on `2595*log10(1+f/700)`, from 20 Hz to fs/2, matching the starter's bin weighting.
   - `10*log10(max(band,1e-10))`; optional orthonormal DCT-II, first 13 MFCC values.
   - Produce a log-mel plot for one clip per class. Compare board and NumPy using **the same decoded quantised samples**.
5. Run the starter with features on for 10 seconds at `speed=1`; save `compute_us`, `lag_s`, loss counters and results on UART and native USB. If the starter cannot complete, document this rather than inventing a timing.
6. Optimise `features.h`: count `cosf`/`sinf` calls in starter DFT, then evaluate twiddle precomputation or radix-2 FFT (ESP-DSP optional). Preserve the exact feature math. Every log-mel output must agree with NumPy within 0.05 dB; report mean and maximum absolute difference and timing before/after. Investigate indexing or numeric mismatches rather than relaxing the requirement. Validate optional MFCCs too.
7. Repeat the failed one-second test and ensure 49 frames and summary. Measure feature throughput only after a complete result. Measure fastest zero-loss `speed` with features off and on; compare both physical ports. Record timing, lag, loss and whether pipe or compute is the bottleneck.
8. Try 25 ms window / 10 ms hop and 13 MFCCs, and record compute time and returned bytes. Keep sampling/quantisation fixed for the baseline comparison.
9. Run the complete 144-clip feature-enabled stream at real time and validate integrated storage if using it. Save board features, `first_sample`, frame numbers, timings and summary for Mission 4. Repeat deliberate skips and complete loss-accounting work according to the team plan.

### Predicted counts and budgets (not measurements)

| Metric | Baseline prediction |
|---|---:|
| Frame duration | 30 ms |
| Hop / steady-state compute budget | 20 ms / 20000 us per frame |
| Features per second (steady state) | 50 |
| 40 float32 log-mel values per frame | 160 B |
| Feature payload incl. first_sample and compute_us | 168 B |
| Feature wire frame incl. 13 B overhead | 181 B |
| Steady-state feature-value rate | 8000 B/s |
| Steady-state feature wire rate | 9050 B/s (excludes summary) |
| Audio wire rate | 32650 B/s (640 + 13 B at 50 packets/s; excludes end frame) |
| Full continuous stream expected feature frames | 7199 |
| If independently framed per clip | 49 × 144 = 7056 |

The full continuous count is `1 + (2304000 - 480)//320`. Do not confuse this with independently framed clips. UART is full duplex; evaluate each direction, buffering and CPU load. Vaibhav measured receive-only UART throughput 89992 B/s at 921600, native USB 456798 B/s with 320 samples/packet; those are not integrated feature-on results. For 13 MFCC values, feature values occupy 52 B/frame, and the corresponding wire frame is 73 B. At 10 ms hop the compute budget becomes 10000 us per frame, not 20000.

## 9. Mission 4/5 handover notes

- In Mission 4, predict 7200 data packets and 7201 including the end frame for the baseline full stream. Track host packets and board counts separately. `skip=(10, 11, 200)` deliberately omits three zero-based packets (960 samples, 1920 int16 bytes with 320 samples per packet); expected host data packets actually sent: 7197. Do not assume correct `first_sample` after a gap: test and fix label alignment; missing audio must not silently shift subsequent clip IDs.
- `first_sample` is the board's reported original sample position only if the loss handling preserves it; verify that property before using `first_sample // 16000` to label frames. Decide how to handle cross-clip windows. A reasonable proposed policy is to drop any frame not wholly inside one clip, leaving 7056 frames for the lossless baseline; 143 cross-boundary frames are excluded. Record actual counts and policy, not just predictions.
- Build the labelled dataset with feature array, label, clip ID and `first_sample` per frame. Provide a half-page data card with synthetic source, settings, counts per class, loss evidence and limitations. This dataset is not real household microphone validation.
- Mission 5: compare board versus original float32 laptop features, and board versus NumPy on identical quantised input. Repeat int8 S=1, smaller S and 8 kHz without anti-aliasing (against filtered 8 kHz laptop reference). Save heat maps and per-band/per-class differences. Train nearest centroid on two thirds of **clips**, test on the other third; standardise with training data only, never split adjacent frames from one clip across train/test. Report both laptop and board accuracy on the same test clips and justify final settings.
- Do not call the Mission 2 baseline the final shipped configuration until the feature, loss and classifier evidence is available.

## 10. Git status, evidence and handoff checklist

The Python commit `964c9a3` was pushed to `origin/main` and `git status` showed a clean tree. The hardware push was subsequently reported successful by the operator; the exact hardware commit hash and latest remote tree were not provided. The prior reports may still contain pre-push or pre-persistence status wording because they were written earlier; this handover records the later results.

- [x] Python analysis and experiments completed
- [x] Pack/unpack data and dB plots exported (operator confirmation)
- [x] SRAM and PSRAM measurements completed
- [x] 8 MiB LittleFS configured and boot issue resolved
- [x] SAVE implemented and tested
- [x] Full 144-clip storage stream verified with zero detected loss
- [x] Physical power cycle and exact byte recovery verified
- [x] Python and hardware Markdown reports prepared
- [x] Python push verified from terminal output; hardware push reported successful
- [ ] Handover file added to repository and pushed
- [ ] Exact hardware revision and full Tools settings captured
- [ ] Outstanding Mission 1 feature-return and repeat items resolved or explicitly documented
- [ ] Mission 3 reference, feature return, optimisation and integrated timing tests
- [ ] Mission 4 deliberate loss, labels, dataset and data card
- [ ] Mission 5 domain shift and classifier
- [ ] Five final mission PDFs, commitment memo, team/LLM record, ZIP and live demo

**LLM disclosure:** The operator used ChatGPT for implementation guidance, debugging, full Python and C++ reference code, report drafting and this handover. The operator executed the experiments and supplied actual terminal results/screenshots. README section 6 permits explanations and hints but says not to use LLMs for finished code; disclose the full extent of assistance and review/reimplement as required by the instructor rather than representing all code as independently authored. Merge the detailed mission logs before submission.

**Evidence limitations:** This record is based on the original supplied ZIP (`README.md`, `TEAM_PLAN.md`, Vaibhav's handover and starter `board_link.py`), the two Mission 2 report drafts and the operator's terminal outputs in the conversation. The current remote repository, final Arduino Tools menu and modified local source files were not independently inspected or rerun. All results marked measured are operator-reported; predicted counts and continuation steps are not completed experiments. The team plan's final deadline is Monday, 30 November 2026.
