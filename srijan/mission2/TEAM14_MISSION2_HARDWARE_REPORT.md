# Mission 2 — What to send, and where to keep it

**AI255TBD Edge AI · Module 2: The Doorbell's Ears**  
**Team 14 — Saura · Hardware, firmware and persistent storage workstream**  
**Board:** ESP32-S3 N16R8 · **Hardware owner in team plan:** Srijan Kumar GS  
**Status:** Full recording stored and recovered after a physical power cycle; exact byte comparison passed. Hardware Git commit/push and final team PDF packaging remain to be verified.

**Evidence and scope:** This report uses the actual terminal outputs supplied during the experiments on 25–26 November 2026 and the original assignment README and TEAM_PLAN in the supplied ZIP. It complements `TEAM14_MISSION2_PYTHON_REPORT.md`. The updated firmware and local result files were not independently retrieved or executed by the report author. Measurements below are student-reported; theoretical estimates and unverified settings are labelled separately.

## 1. Aim

Determine whether the smart doorbell can receive and retain the entire Team 14 audio dataset on an ESP32-S3. Measure the practical internal SRAM capacity, enable and test PSRAM, configure enough non-volatile flash, finish the starter firmware's `cmdSave()` handler, and establish persistence by unplugging the board, retrieving the saved recording and comparing all bytes against the original laptop payload.

The Python workstream selected 16 kHz, signed little-endian int16, scale S=1.0, and anti-aliasing enabled. This hardware experiment verifies that the selected representation can be transported and stored. It does not establish real-time log-mel computation or feature-return throughput; those belong to subsequent missions.

## 2. Background

### 2.1 Audio configuration

| Parameter | Selected value |
|---|---:|
| Team | 14 |
| Number of clips | 144 |
| Duration per clip | 1 s |
| Channels | 1 |
| Sampling rate | 16,000 Hz |
| Representation | Signed int16, little-endian (`<i2`, protocol `i16`) |
| Scale | 1.0 |
| Anti-aliasing | Enabled in `get_clip()` |
| Samples per packet | 320 |
| Raw payload per packet | 640 bytes |
| Raw audio rate | 32,000 B/s |
| Total samples | 2,304,000 |
| Total raw payload | 4,608,000 bytes (4.608 MB; approximately 4.395 MiB) |
| Reference CRC32 | `0x50527154` (1347580244) |

The full dataset was generated in clip-list order, concatenated and packed with the existing Python quantisation implementation. Scale S=1.0 is a fixed choice made before hearing the audio. The earlier full-dataset validation reported mean SQNR 77.56 dB, minimum SQNR 72.92 dB and no clipped samples for this configuration.

### 2.2 Memory types

| Memory | Role | Retained without power? |
|---|---|---|
| Internal SRAM | Fast working memory and small recording buffer | No |
| PSRAM | Larger contiguous recording buffer | No |
| Flash / LittleFS | Non-volatile recording file | Yes, when successfully committed |

N16R8 denotes the module configuration with 16 MB nominal flash and 8 MB nominal PSRAM. The runtime measurements confirmed 16,777,216 bytes of flash and 8,388,608 bytes of PSRAM after activation. OPI (octal peripheral interface) is the eight-data-line memory interface selected for the board's PSRAM. SRAM and PSRAM are not persistent storage.

### 2.3 Communication and integrity

The board was connected via its CH343 USB-to-UART bridge, identified as COM6 on the test laptop. The runtime serial baud was 921600. UART 8N1 framing requires approximately ten line bits for each eight-bit byte, giving a theoretical maximum of 92,160 B/s, excluding protocol overhead. The target audio payload alone requires 32,000 B/s. Board packet CRC counters detect corrupt frames, sequence counters detect gaps and duplicates, byte/sample counts detect missing or truncated data, and the whole-recording CRC32 checks end-to-end consistency. Exact byte equality is a stronger final check than CRC32 alone.

Data path:

```text
Team 14 audio on laptop -> quantise/pack -> USB-UART
    -> ESP32-S3 PSRAM -> SAVE -> LittleFS /rec.bin
    -> remove power -> reboot -> CRC flash -> DUMP flash
    -> compare returned bytes with original laptop payload
```

## 3. Prediction

The following calculations represent theoretical predictions, not independent measurements.

- Audio storage: `144 × 16000 × 2 = 4608000 bytes`.
- Initial largest SRAM block: 204,788 bytes. Ideal recording duration: `204788 / 32000 = 6.399625 s`. Actual capacity may be lower because firmware allocates other buffers.
- With PSRAM enabled, the measured initial largest block of 8,257,524 bytes implies an ideal upper bound of `8257524 / 32000 = 258.047625 s`. The 144-second recording should fit, but this does not establish the absolute maximum PSRAM allocation.
- Original LittleFS capacity (1,441,792 bytes) cannot hold the payload. An 8 MiB filesystem should accommodate the file and filesystem overhead.
- At `speed=1.0`, the full upload should take approximately 144 seconds, excluding setup/termination overhead.
- A 4,608,000-byte raw dump over 921600 baud 8N1 requires at least 50 seconds at ideal line utilisation.
- After unplugging, the RAM recording should disappear but flash usage, file length, and CRC32 should remain unchanged. The returned bytes should match the original exactly.

## 4. Method

### 4.1 Setup and reproducibility

- Windows PowerShell in Antigravity, Python 3.11.9, virtual environment `.venv`, NumPy and PySerial.
- Arduino IDE, ESP32 Arduino core 3.3.12 (shown in upload log), esptool 5.3.1.
- ESP32-S3 board connected through CH343 USB-to-UART (COM6); Arduino Serial Monitor/Plotter closed before Python serial access.
- The following tools settings were used or instructed during the successful workflow. Verify the exact GUI values on the local machine before final submission: board `ESP32S3 Dev Module`, CPU 240 MHz, flash size 16 MB, OPI PSRAM enabled, upload speed 921600, port COM6, custom `partitions.csv` alongside the sketch. Upload logs showed DIO boot mode. Other USB/flash settings were intentionally left unchanged; their precise menu values were not captured. Full flash erase was not required in the successful troubleshooting procedure.

Run from the repository root with the virtual environment active:

```powershell
python board_link.py ports
python board_link.py --port COM6 --baud 921600 ping
python board_link.py --port COM6 --baud 921600 info
```

### 4.2 SRAM test (PSRAM disabled)

Use `srijan/mission2/hardware/sram_test.py`. Concatenate the first 1, 3, 5, 6, 7 or 10 Team 14 clips and pack them as int16. For each duration, free the previous buffer and stream at `speed=1.0`, `store="sram"`, `feat=False`, 320 samples/packet and `max_bytes` equal to payload size. Compare stored length and CRC to the laptop's original. Stop at the first allocation failure. The 7- and 10-second cases were therefore not executed.

### 4.3 PSRAM test

Enable OPI PSRAM in Arduino IDE and reupload the sketch while preserving the existing communication settings. Verify `psram_size`, `psram_free` and `psram_largest` via `INFO`. Run `srijan/mission2/hardware/psram_test.py` for 10, 60 and 144 seconds, using `store="psram"`, `feat=False`, `speed=1.0`, and 320 samples/packet. Validate sample count, byte count, whole CRC and packet error counters. Record memory after each recording and free the buffer before the next run.

### 4.4 Flash partition

Create `doorbell_board_starter/partitions.csv` alongside the `.ino`. The successful procedure rewrote the file in ASCII using PowerShell, then uploaded the sketch with the 16 MB flash setting and OPI PSRAM unchanged. The proposed and subsequently rewritten layout was:

```csv
# Name, Type, SubType, Offset, Size, Flags
nvs,data,nvs,0x9000,0x5000,
otadata,data,ota,0xe000,0x2000,
app0,app,ota_0,0x10000,0x300000,
app1,app,ota_1,0x310000,0x300000,
spiffs,data,spiffs,0x610000,0x800000,
coredump,data,coredump,0xFF0000,0x10000,
```

The filesystem partition label is `spiffs`, used by the starter's Arduino LittleFS mounting convention; the filesystem itself is LittleFS, not SPIFFS. Both OTA slots are 3 MiB each. The filesystem allocation is 8 MiB; its measured capacity after reboot confirms it is available. The partition binary itself was not independently decoded in this report. Verify the final checked-in CSV matches this layout.

### 4.5 Firmware implementation

The starter sketch's `cmdSave(Stream &s)` handler was completed. Its implemented algorithm was:

1. Check filesystem availability and a nonempty in-memory recording.
2. Start a microsecond timer and open `REC_PATH` (`/rec.bin`) for writing.
3. Write `storeBuf` in 4,096-byte chunks, checking every write and yielding between chunks.
4. On a short write, close the file, remove the incomplete recording and return an error.
5. Flush and close the file, measure elapsed write time, reopen and verify file length.
6. Calculate the CRC32 of the original in-memory recording and return `OK SAVE n=... us=... crc=...`.
7. Independently verify the flash CRC using the existing `CRC flash` handler, rather than treating the SAVE response CRC as a direct flash readback.

After uploading, `PING` returned `PONG` and `SAVE` with no recording returned `ERR SAVE no recording` as intended. This tested the guard condition before writing the full dataset.

The implementation overwrites the previous recording directly; transactional replacement and resilience to an unexpected power cut during the write were not tested. The persistence test removed power only after SAVE and independent flash CRC verification completed.

### 4.6 Full flash write and power-cycle verification

Run `srijan/mission2/hardware/flash_test.py`. Generate the complete Team 14 payload, confirm free flash, free any old RAM buffer, stream into PSRAM, compare PSRAM CRC, execute `b.save()`, record save time and verify `b.crc("flash")`. Capture `INFO` and save the result JSON.

Physically disconnect the board from power, reconnect, and do not reflash the firmware. Run PING/INFO and verify `b.crc("flash")` again. The student reported a successful physical power cycle, with RAM cleared and flash usage unchanged.

Finally run `srijan/mission2/hardware/persistence_test.py`. Regenerate the original payload, read `b.dump("flash")`, time the transfer, compare byte lengths and CRCs, count unequal uint8 values and test Python bytes equality. The script records the final results to JSON.

## 5. Observations

### 5.1 Memory baseline and PSRAM activation

| Parameter | Initial, PSRAM off | PSRAM on | After flash expansion |
|---|---:|---:|---:|
| CPU (MHz) | 240 | 240 | 240 |
| Internal heap free (B) | 256,208 | 336,168 | 336,060 |
| Largest internal block (B) | 204,788 | 278,516 | 278,516 |
| PSRAM size (B) | 0 | 8,388,608 | 8,388,608 |
| PSRAM free (B) | 0 | 8,351,220 | 8,351,220 |
| Largest PSRAM block (B) | 0 | 8,257,524 | 8,257,524 |
| Physical flash (B) | 16,777,216 | 16,777,216 | 16,777,216 |
| LittleFS total (B) | 1,441,792 | 1,441,792 | 8,388,608 |
| LittleFS used (B) | 8,192 | 8,192 | 8,192 |

Values are point-in-time INFO measurements; heap free can vary between commands and boots.

### 5.2 SRAM capacity

| Duration (s) | Samples | Required B | Stored B | Frames incl. END | Time (ms) | CRC32 | Result |
|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 16,000 | 32,000 | 32,000 | 51 | 987 | `639B7E7B` | PASS |
| 3 | 48,000 | 96,000 | 96,000 | 151 | 2,986 | `1D6646EE` | PASS |
| 5 | 80,000 | 160,000 | 160,000 | 251 | 4,986 | `7AF7318B` | PASS |
| 6 | 96,000 | 192,000 | Not allocated | — | — | — | FAIL |

All successful transfers reported no bad CRCs, bad lengths, sequence gaps, duplicates, UART errors or store overflow. Board and laptop CRCs matched for each. The failed allocation returned `ERR alloc sram want=192000 largest=163828`.

**Measured whole-second limit:** five seconds passed, six seconds failed with the tested pre-PSRAM firmware configuration. The largest reported block at failure implies 5.119625 seconds of raw int16 audio at 16 kHz. Fractional-second boundary testing was not performed, so five seconds is the longest successfully tested whole-second recording, not an exact universal SRAM maximum.

### 5.3 PSRAM capacity

| Duration (s) | Samples | Stored B | Frames incl. END | Board time (ms) | CRC32 | Result |
|---:|---:|---:|---:|---:|---|---|
| 10 | 160,000 | 320,000 | 501 | 9,986 | `1833511D` | PASS |
| 60 | 960,000 | 1,920,000 | 3,001 | 59,987 | `D656CC6E` | PASS |
| 144 | 2,304,000 | 4,608,000 | 7,201 | 143,990 | `50527154` | PASS |

| Duration (s) | PSRAM free after recording (B) | Largest free PSRAM block (B) |
|---:|---:|---:|
| 10 | 8,023,536 | 7,864,308 |
| 60 | 6,417,904 | 6,291,444 |
| 144 | 3,632,624 | 3,538,932 |

All three tests returned zero bad CRC, bad length, sequence gaps, duplicates, store overflow and UART errors. The full recording used 7,200 audio packets plus the terminating frame. Features were disabled intentionally (`features=0`, `max_us=0`, `avg_us=0`). Absolute PSRAM capacity above 144 seconds was not stress-tested.

### 5.4 Flash storage and write speed

| Metric | Measured result |
|---|---:|
| LittleFS total | 8,388,608 B |
| Used before recording | 8,192 B |
| Free before recording | 8,380,416 B |
| Audio bytes saved | 4,608,000 B |
| Used after recording | 4,628,480 B |
| Free after recording | 3,760,128 B |
| Streaming board time | 143,989 ms |
| SAVE elapsed time | 10,317,019 us (10.317019 s) |
| Reported write speed | 446,640.64 B/s |
| Whole-recording PSRAM CRC32 | `50527154` |
| Independently read flash CRC32 | `50527154` |
| Bad CRC / bad length / gaps / duplicates / UART errors / store overflow | All zero |

The SAVE response was `{'n': 4608000, 'us': 10317019, 'crc': 1347580244}`. The independent `CRC flash` response was `{'where': 'flash', 'n': 4608000, 'crc': 1347580244}`.

### 5.5 Physical power cycle

| Metric | Before unplugging | After reconnecting |
|---|---:|---:|
| Stored RAM audio (B) | 4,608,000 | 0 |
| Storage location reported | `psram` | `none` |
| PSRAM free (B) | 3,632,624 | 8,351,220 |
| LittleFS used (B) | 4,628,480 | 4,628,480 |
| Flash recording bytes | 4,608,000 | 4,608,000 |
| Flash CRC32 | `50527154` | `50527154` |

`POWER CYCLE VERIFICATION PASSED` was printed after the post-reboot flash CRC and file-length assertions succeeded. The PSRAM copy did not survive, as expected.

### 5.6 Full retrieval after power loss

```text
Original bytes: 4608000
Retrieved bytes: 4608000
Original CRC32:  50527154
Retrieved CRC32: 50527154
Retrieval time: 50.358 seconds
Retrieval speed: 91505.24 B/s
Length match: True
CRC32 match: True
Mismatched bytes: 0
Exact byte-by-byte match: True
PERSISTENT STORAGE VERIFICATION PASSED
ALL AUDIO BYTES RECOVERED WITHOUT CORRUPTION
```

All original, PSRAM, flash-before-power-cycle, flash-after-power-cycle and retrieved CRCs agree. The exact byte comparison additionally establishes that all 4,608,000 bytes of this tested recording were recovered without alteration.

## 6. Analysis

### 6.1 Practical memory limits

The largest initial contiguous SRAM block predicts 6.40 seconds, but the six-second allocation failed. The largest available block at the failure was 163,828 bytes, 40,960 bytes below the initial figure. Firmware working allocations and memory fragmentation can lower the available contiguous region; the precise attribution of this difference was not instrumented. Five seconds (160,000 bytes) passed. PSRAM, when configured correctly, held the entire 144-second dataset with 3,632,624 bytes free. The recording consumes about 54.93% of physical PSRAM, not including runtime allocation overhead.

### 6.2 Flash capacity and overhead

The original filesystem could not contain the entire dataset. After partition expansion, the 8 MiB LittleFS was sufficient. The final used capacity was 4,628,480 bytes, approximately 55.18% of the filesystem. The measured free space was 3,760,128 bytes (approximately 3.59 MiB). The increase in filesystem usage was `4,628,480 - 8,192 = 4,620,288 B`, which exceeds the raw payload by 12,288 B. This represents additional filesystem allocation/metadata overhead in this run. The final used capacity exceeds the payload by 20,480 B including baseline usage.

### 6.3 Transfer speed

The reported flash write speed of 446,640.64 B/s is about 13.96 times the real-time audio payload rate of 32,000 B/s. However, SAVE was performed after receiving the audio; this does not prove simultaneous streaming and flash writing can sustain real time.

The raw dump achieved 91,505.24 B/s, about 99.29% of the ideal 92,160 B/s UART 8N1 payload ceiling and 2.86 times the audio payload rate. The measured 50.358-second dump was close to the theoretical minimum of 50 seconds. This is a raw flash readback measurement, not a measurement of simultaneous feature-return throughput.

The tested UART port sustained real-time audio streaming with features disabled. The earlier Mission 1 native USB throughput candidate and the selected port for later integrated features remain subject to the subsequent feature-return experiments. No claim is made that this hardware run resolves the incomplete Mission 1 feature-return case.

### 6.4 Troubleshooting history

| Problem | Evidence | Action | Outcome |
|---|---|---|---|
| PSRAM not exposed | `psram_size=0`, full dataset too large for SRAM | Enabled OPI PSRAM in Arduino IDE, uploaded again | 8,388,608 B detected and 144 s stored |
| SRAM allocation failure | `ERR alloc sram want=192000 largest=163828` | Recorded actual limit rather than repeatedly forcing allocation; used PSRAM | Five-second test passed; six-second test failed as documented |
| Small flash filesystem | `fs_total=1441792` | Created 8 MiB custom filesystem partition | `fs_total=8388608` verified |
| Boot loop after first partition upload | `No bootable app partitions in the partition table`; Python PING stalled | Inspected serial boot log; rewrote CSV in ASCII, verified board settings, reuploaded | `PONG` returned and new filesystem capacity confirmed |
| COM6 access denied | PySerial `PermissionError(13, 'Access is denied.')` | Released serial-port users, retried | PING and SAVE guard worked |
| SAVE initially unfinished in starter | Starter handler lacked persistent recording write | Implemented chunked write, length checking, flush/close and response | Complete file and independent flash CRC verified |

The first partition table's exact defect was not independently diagnosed. Its unusually small compressed binary size was a clue, not proof of a particular encoding or empty-file cause. Rewriting the CSV in ASCII and reuploading resolved the observed boot issue. Similarly, the exact application holding COM6 was not recorded; serial port contention was the likely explanation, not a proven identification. Ctrl+C-related `KeyboardInterrupt` logs resulted from manually stopping a stalled command, not a separate firmware error.

### 6.5 Limitations and next steps

- A single successful completed-write power cycle and exact readback were demonstrated; power interruption during SAVE, repeated cycling/endurance, and transactional replacement were not tested.
- Five seconds is the largest successful whole-second SRAM duration, not an exact fractional-second maximum. The 144-second PSRAM result is a sufficient capacity demonstration, not a maximum-capacity search.
- The code and measurements used `feat=False`. Mission 3 must verify on-board feature extraction, resolve the feature-return defect, check numerical parity with NumPy and measure computation/transport timing with the selected feature settings.
- Keep the working partition CSV and firmware under version control. Preserve the reference CRC and existing flash file until the team has recorded the persistence evidence. Future uploads, filesystem formatting or writes may replace/delete it.
- The report is a Markdown draft; the assignment calls for the eight-heading mission records in the final PDF. Combine with the Python report, update that report's earlier pending-status text, reconcile team ownership and verify paths before submitting. No final PDF or remote repository update is asserted here.

## 7. What we learnt

- Physical chip capacity, free heap and largest contiguous allocatable block are distinct measurements.
- PSRAM must be configured and verified at runtime; it is not automatically available merely because the module includes it.
- Flash chip capacity does not equal usable filesystem capacity. The partition table and filesystem overhead determine whether a recording fits.
- Stream completion, packet accounting, RAM CRC, flash CRC, post-power-cycle CRC and byte-for-byte comparison provide different levels of evidence.
- Upload-tool success does not guarantee the firmware boots. Serial boot logs helped isolate the partition-table problem.
- A 16 kHz int16 representation at S=1.0 combines strong measured quantisation fidelity with sufficient verified memory and transport capacity for the present storage-only workflow.

### Handoff and evidence files

| Path (relative to repository root) | Purpose |
|---|---|
| `doorbell_board_starter/doorbell_board_starter.ino` | Updated SAVE handler |
| `doorbell_board_starter/partitions.csv` | Custom flash layout |
| `srijan/mission2/hardware/sram_test.py` | SRAM capacity and CRC test |
| `srijan/mission2/hardware/psram_test.py` | PSRAM streaming and CRC test |
| `srijan/mission2/hardware/flash_test.py` | Flash write and CRC test |
| `srijan/mission2/hardware/persistence_test.py` | Power-cycle readback and exact byte comparison |
| `srijan/mission2/results/psram_test_results.csv` | PSRAM measurements |
| `srijan/mission2/results/flash_test_results.json` | Full flash write evidence |
| `srijan/mission2/results/persistence_test_results.json` | Final retrieval evidence |
| `srijan/mission2/TEAM14_MISSION2_PYTHON_REPORT.md` | Complementary signal-processing report (verify present) |
| `srijan/mission2/TEAM14_MISSION2_HARDWARE_REPORT.md` | This hardware report |

Paths are based on student-reported local commands and earlier instructions. The SRAM log was supplied as terminal output; no separate SRAM CSV was produced by the script. Before handoff, confirm all files and actual Arduino Tools settings. Python work was pushed as commit `964c9a3` on `main`; the hardware commit ID was not yet supplied.

## 8. LLM log

This is a disclosure draft, not a claim that the implementation was independently authored. The conversation involved substantial LLM-generated code, exceeding the README's stated restriction on using LLMs for finished code. The team should disclose the extent accurately and consult the instructor about acceptable remediation rather than presenting this work as independently written.

| Topic / prompt summary | Assistance received | Student verification / result |
|---|---|---|
| How to determine actual SRAM capacity? | Predicted limit from contiguous heap; supplied SRAM test script | Ran on physical board: 1, 3, 5 s passed, 6 s failed; CRCs matched |
| Why does PSRAM report zero and how to enable it? | Suggested OPI PSRAM setting and runtime INFO verification | Reuploaded sketch, measured 8 MiB, passed full dataset test |
| How to fit recording in flash? | Proposed custom 8 MiB LittleFS partition layout and ASCII PowerShell rewrite | First upload resulted in boot loop; corrected/reuploaded and measured capacity |
| Why does PING stall after upload? | Suggested checking reset/baud and boot logs; interpreted no-bootable-app error | Student collected actual boot logs; recovery confirmed via PONG and INFO |
| How to finish `cmdSave()`? | Supplied full C++ implementation for chunked LittleFS writes and size validation | Compiled/uploaded on the board, tested no-recording guard and full write |
| Why is COM6 access denied? | Suggested releasing competing serial monitor/port users | Student retried and got PONG |
| How to test permanent flash storage? | Supplied full flash test script and CRC assertions | Student ran it: 4,608,000 B written, independent flash CRC matched |
| How to test survival after power loss? | Provided physical power-cycle procedure and CRC command | Student unplugged/reconnected and reported passing CRC verification |
| How to compare full recovered recording? | Provided complete persistence test script using actual Board.dump source | Student ran it: 50.358 s, zero mismatched bytes, exact match |
| How to document Mission 2? | Generated this report from supplied experimental logs and assignment materials | Student must verify report, actual source files, settings and authorship disclosure |

The tests were executed by the student on the real ESP32-S3. Numerical results were not invented by the LLM. Before submission each teammate should understand and be able to explain quantisation, memory allocation, partition layout, CRC32, packet accounting, the SAVE implementation and why the persistence test passed. Record actual role assignments and reflection in the final team submission.
