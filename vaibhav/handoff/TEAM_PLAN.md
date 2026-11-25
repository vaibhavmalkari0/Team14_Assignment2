# Team Saura — Sequential Assignment Plan

**Team:** 14 — Saura  
**Team number:** 14  
**Members:** Vaibhav, Sumadhwa, Srijan, Karthik  
**Final deadline:** Monday, 30 November 2026

The assignment is completed in **one continuous handoff chain**:

```text
Vaibhav finishes his work
        |
        v
Sumadhwa finishes his work
        |
        v
Srijan finishes his work
        |
        v
Karthik finishes his work
        |
        v
Final team review and live submission
```

This plan gives each person a complete block of responsibility. A person should not leave a partial task for the next person. Each handoff must include every result, file, plot, measurement, command, and known issue.

---

# 1. Vaibhav — Board setup, pipe tests, and integration

**Order:** First  
**Handoff to:** Sumadhwa

## Vaibhav's tasks

### Set up the board and laptop

- Install Python 3.10 or newer.
- Install NumPy, pyserial, and matplotlib.
- Install Arduino IDE.
- Install ESP32 board package `esp32 by Espressif Systems`, version 3.x.
- Set:
  - Board: **ESP32S3 Dev Module**
  - USB CDC On Boot: **Enabled**
- Upload [doorbell_board_starter.ino](/C:/Users/vaibh/Downloads/projects-ong/edge_ai_assignment2/doorbell_board_starter/doorbell_board_starter.ino).
- Run `python board_link.py ports`.
- Test `python board_link.py --port <PORT> info` on both ports.
- Run `python team_audio.py 14`.
- Listen to `team_14_preview.wav`.

### Record required predictions

- Calculate how many bytes 16 kHz float32, int16, and int8 audio carry per second.
- Calculate bytes per second for 8 kHz int16 and int8.
- Calculate capacity for 115,200 baud, including 10 bits per UART byte.
- Ask an LLM how many bytes per second can be sent to an ESP32-S3 over USB.
- Record the question and answer in the LLM log.

### Complete Mission 1: The pipe

- Measure `speed=0, feat=False, store="none"` on:
  - COM at 115,200 baud
  - COM at 921,600 baud
  - COM at 2,000,000 baud
  - Native USB
- Test `samples_per_packet`:
  - 8
  - 64
  - 320
  - 1024
- Account for 13 header/CRC bytes per frame.
- Create the real-time table for all required formats and ports.
- Calculate feature bytes sent back per second.
- Plot:
  - COM speed against baud
  - USB speed for comparison
  - Packet size against effective throughput
- Explain the difference between the USB-UART bridge and native USB CDC.

### Prepare the initial integration structure

- Create the working Python project structure.
- Create a log for measurements and commands.
- Confirm that team number 14 loads the correct 144 clips.
- Verify the board and laptop both work before handing over.

## Vaibhav handoff package

Vaibhav must give Sumadhwa:

- [ ] Board setup record
- [ ] Board `INFO` results
- [ ] Team 14 preview WAV
- [ ] Mission 1 prediction table
- [ ] Mission 1 measured results
- [ ] COM/USB real-time table
- [ ] Packet-size measurements
- [ ] Mission 1 plots
- [ ] Mission 1 report, following the eight headings
- [ ] LLM log entry
- [ ] Working `board_link.py` environment

**Vaibhav's work is complete after this handoff. He does not continue working on Mission 1 or these setup tasks.**

---

# 2. Sumadhwa — Quantisation, NumPy features, and classifier

**Order:** Second  
**Starts after:** Vaibhav completes and hands over  
**Handoff to:** Srijan

## Sumadhwa's tasks

### Quantise and pack audio

- Implement `quantise()` for int16 and int8.
- Implement `pack()` and `unpack()`.
- Use:

  ```python
  q = clip(round(x / S * (2**(b-1) - 1)),
           -2**(b-1), 2**(b-1) - 1)
  xhat = q * S / (2**(b-1) - 1)
  ```

- Test 16 kHz int16 and int8.
- Test int8 with scale `S=1`.
- Test int8 with at least one smaller scale.
- Save pack and unpack tests.

### Complete sampling and filtering tests

- Plot spectra of a silence clip at 48 kHz and 8 kHz without an anti-alias filter.
- Identify and calculate the extra peak frequency.
- Repeat at 8 kHz with `antialias=True`.
- Explain why filtering must occur before downsampling.
- Calculate SQNR for:
  - int16 on a word clip
  - int16 on a silence clip
  - int8 on a word clip
  - int8 on a silence clip
  - smaller int8 scale
- Recommend one sampling rate, format, filter, and scale.
- Explain how a scale could be chosen before hearing anything.

### Implement NumPy features

- Implement `features(x, fs, win, hop, nfft, mels, mfcc)`.
- Start with:
  - win = 30 ms
  - hop = 20 ms
  - nfft = 512
  - mels = 40
- Apply a symmetric NumPy Hann window.
- Use the assignment mel filterbank recipe.
- Return log-mel features and optional 13-coefficient MFCCs.
- Plot log-mel features for one clip of each class.
- Produce NumPy reference features for board comparison.

### Complete the dataset and classifier work

- Label feature frames using `clip_list(team=14)`.
- Decide and document what to do with frames that straddle two clips.
- Generate a labelled `.npz` or `.csv` dataset.
- Include:
  - features
  - label
  - clip ID
  - `first_sample`
- Compare original float32 laptop features with board features.
- Perform the int8, smaller-scale, and 8 kHz comparisons.
- Create difference heat maps.
- Standardise per-clip mean and standard-deviation bands using the training set.
- Train a nearest-centroid classifier using two thirds of the clips.
- Test laptop features and board features with the remaining third.

### Complete NumPy-side reports

- Write Mission 2 report.
- Write Mission 3 NumPy part.
- Write Mission 5 report data and analysis.

## Sumadhwa handoff package

Sumadhwa must give Srijan:

- [ ] Quantisation and packing code
- [ ] Int16 and int8 unpacked test data
- [ ] 48 kHz/8 kHz spectra
- [ ] SQNR measurements
- [ ] Recommended sampling rate, format, filter, and scale
- [ ] NumPy feature implementation
- [ ] Log-mel plots for all classes
- [ ] NumPy reference dataset
- [ ] DCT/MFCC implementation
- [ ] Laptop-versus-board comparison code
- [ ] Classifier and accuracy results
- [ ] Heat maps
- [ ] Mission 2, NumPy Mission 3, and Mission 5 results
- [ ] LLM log entries

**Sumadhwa's work is complete after this handoff. He does not continue modifying NumPy code unless Srijan reports a specific board mismatch that points to a NumPy reference error.**

---

# 3. Srijan — Board firmware, storage, and feature optimisation

**Order:** Third  
**Starts after:** Sumadhwa completes and hands over  
**Handoff to:** Karthik

## Srijan's tasks

### Storage and Mission 2

- Identify the longest recording that fits in SRAM.
- Allocate and test PSRAM.
- If PSRAM fails:
  - Identify the Tools setting that enabled or disabled it.
  - Check ESP32-S3 N16R8 OPI PSRAM requirements.
- Finish `cmdSave()` in [doorbell_board_starter.ino](/C:/Users/vaibh/Downloads/projects-ong/edge_ai_assignment2/doorbell_board_starter/doorbell_board_starter.ino).
- Implement LittleFS saving:
  - open `/rec.bin`
  - write `storeBuf` in chunks
  - close the file
  - return CRC and byte count
- Check `INFO` for `fs_total` and `fs_used`.
- Change the required Tools settings until all 144 clips fit.
- Record flash capacity and remaining room.
- Stream, run `SAVE`, unplug, replug, and prepare the flash copy.
- Do not alter data that is needed for CRC comparison.

### Board features and Mission 3

- Ask an LLM how long a 512-point FFT takes on an ESP32-S3.
- Record the question and answer in the LLM log.
- Measure starter feature compute time.
- **Resolve Vaibhav's incomplete feature-return test before reporting feature throughput:** reproduce it on COM at 921600 baud using a one-second Team 14 clip, 16 kHz int16, `feat=True`, `store="none"`, `speed=0`, `win=480`, `hop=320`, `nfft=512`, `mels=40`, `mfcc=0`, and `samples_per_packet=320. The initial result was 6 of 49 frames, 43 lost, `bad_crc_back=0`, and no board summary after 11.416 s.
- Re-run that case and confirm all 49 expected frames are returned (`lost_features == 0`) and the board summary is present. Keep the result marked incomplete until both checks pass; only then measure and report feature-return bytes per second.
- Count calls to `cosf` and `sinf` in the starter DFT.
- Optimise [features.h](/C:/Users/vaibh/Downloads/projects-ong/edge_ai_assignment2/doorbell_board_starter/features.h).
- Consider a radix-2 FFT or twiddle-factor table.
- Optionally use ESP-DSP only if the operation can be explained.
- Make board output match Sumadhwa's NumPy output within 0.05 dB.
- Test:
  - 40 log-mel values
  - 13 MFCC values
  - win = 25 ms, hop = 10 ms
- Record compute time before and after.
- Record output bytes per frame.

### Streaming and loss behaviour

- Stream 10 seconds at `speed=1` with features enabled.
- Record `compute_us` and `lag_s`.
- Test native USB and COM.
- Find the fastest feature-off speed.
- Find the fastest feature-on speed.
- Stream all 144 clips at `speed=1`.
- Test `skip=(10, 11, 200)`.
- Verify sequence gaps, bad CRC frames, duplicates, sample count, and feature count.
- Explain `first_sample` after a gap.
- Check UART receive-buffer overflow behaviour.
- Increase COM speed until loss appears.
- Find the fastest zero-loss setting for COM and USB.

### Build the final board package

- Remove debugging-only changes.
- Verify the final sketch and `features.h` compile.
- Save exact Arduino Tools settings.
- Produce board feature and timing output for the dataset.

## Srijan handoff package

Srijan must give Karthik:

- [ ] Finished `cmdSave()`
- [ ] Final board sketch
- [ ] Optimised `features.h`
- [ ] SRAM, PSRAM, and flash capacity results
- [ ] Arduino Tools settings
- [ ] Flash persistence and CRC evidence
- [ ] Before-and-after feature timing
- [ ] Reproduced and resolved the incomplete 16 kHz int16 feature-return case: 49/49 frames and board summary present
- [ ] Board-versus-NumPy 0.05 dB check
- [ ] 40-band and 13-MFCC timing
- [ ] USB versus COM real-time test
- [ ] Feature-off and feature-on maximum speeds
- [ ] Full 144-clip board summary
- [ ] `skip=(10, 11, 200)` evidence
- [ ] Missing-feature accounting
- [ ] Fastest verified zero-loss settings
- [ ] Mission 2, Mission 3, and Mission 4 board results
- [ ] LLM log entries

**Srijan's work is complete after this handoff. He does not continue changing board code unless Karthik finds a reproducible board-side defect.**

---

# 4. Karthik — Verification, data card, reports, and final archive

**Order:** Fourth  
**Starts after:** Srijan completes and hands over  
**Handoff to:** Vaibhav for final live check

## Karthik's tasks

### Audit the delivered work

- Independently repeat the final stream test.
- Verify:
  - packet count
  - sample count
  - feature frame count
  - `packets_sent`
  - `seq_gaps`
  - `bad_crc`
  - `lost_features`
  - board `frames_ok`
- Verify that skip accounting finds exactly skipped packets.
- Check that labels do not shift after a lost packet.
- Confirm that `first_sample` is correct.
- Check that frames straddling clips follow the documented rule.

### Build and validate the dataset

- Export the complete labelled `.npz` or `.csv`.
- Include:
  - features
  - label
  - clip ID
  - `first_sample`
- Count frames for all six classes.
- Check dimensions and missing values.
- Verify that every clip ID maps to a valid team 14 label.
- Produce a final dataset-integrity summary.

### Complete Mission 4

- Verify full 144-clip stream at `speed=1`.
- Record fastest zero-loss COM and USB settings.
- Distinguish:
  - sequence gaps
  - bad CRC frames
  - missing feature frames
- Explain buffer filling as a possible source of loss.
- Write the Mission 4 report.

### Complete the data card

Write a half-page data card covering:

- source
- stream settings
- frames per class
- lost data and loss evidence
- known problems
- what the data should not be used for

### Complete Mission records

Produce one PDF for each mission. Every mission PDF must use:

1. Aim
2. Background
3. Prediction
4. Method
5. Observations
6. Analysis
7. What we learnt
8. LLM log

Mission reports required:

- Mission 1
- Mission 2
- Mission 3
- Mission 4
- Mission 5

### Assemble the LLM and team records

- Merge all LLM log entries.
- Add the team-role record.
- Record who completed each sequential handoff.
- Keep failed LLM claims only if they were later tested and explained.

### Assemble the submission folder

Create `team_14_module2/` containing:

- All Python code
- Final `.ino`
- Final `features.h`
- Arduino Tools settings
- Final dataset
- Five mission PDFs
- Data card
- Commitment memo
- LLM log
- Team handoff record

## Karthik handoff package

Karthik must give Vaibhav:

- [ ] Final audited dataset
- [ ] Mission 1–5 PDFs
- [ ] Data card
- [ ] Full loss report
- [ ] Final accuracy and comparison charts
- [ ] Consolidated LLM log
- [ ] Consolidated team-role record
- [ ] Complete `team_14_module2/` folder
- [ ] A ZIP file ready for final review

**Karthik's work is complete after this handoff. He does not continue report editing unless Vaibhav finds a reproducible evidence gap.**

---

# Final ownership — Vaibhav

**Order:** Final review and live submission  
**Before deadline:** Monday, 30 November 2026

Vaibhav receives the complete package and owns all final decisions.

## Final Vaibhav tasks

- Choose and justify the final:
  - sampling rate
  - filter
  - format
  - scale
  - scale-selection rule
  - port
  - stream speed
  - feature settings
  - storage location
- Write the one-page commitment memo.
- State in the memo:
  - real-time margin
  - storage size and remaining room
  - feature compute time against budget
  - feature bytes sent back
  - what was lost and how it was detected
  - laptop-versus-board difference
  - whether the difference matters
  - the design's most likely point of failure
- Run the live demonstration.
- Stream all 144 clips using the memo settings.
- Run `SAVE`.
- Unplug and replug the board.
- Run `dump("flash")`.
- Verify the flash CRC.
- Show loss counts and open the final dataset.
- Practice a one-number-change question for every design parameter.
- Confirm all team members can explain the final design without a laptop.
- Submit the ZIP.

## Final submission folder

```text
team_14_module2/
├── mission_records/
│   ├── mission_1.pdf
│   ├── mission_2.pdf
│   ├── mission_3.pdf
│   ├── mission_4.pdf
│   └── mission_5.pdf
├── python/
├── board/
│   ├── doorbell_board_starter.ino
│   ├── features.h
│   └── tools_settings.txt
├── dataset/
│   └── labelled_dataset.npz
├── data_card.md
├── commitment_memo.pdf
├── llm_log.md
└── team_handoff_record.md
```

---

# Date sequence

| Date | Active member | Completion target |
|---|---|---|
| 24–25 November | Vaibhav | Setup and Mission 1 complete |
| 26–27 November | Sumadhwa | Quantisation, features, and dataset code complete |
| 28–29 November | Srijan | Storage, optimisation, and board tests complete |
| 29 November | Karthik | Dataset, reports, data card, and ZIP complete |
| 30 November | Vaibhav | Live run and final hand-in |
