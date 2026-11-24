# Module 2: The Doorbell's Ears

**AI255TBD Edge AI · Module 2 assignment: Sensor Data Acquisition on the Board**
Team of four · one ESP32-S3-DevKitC-1 N16R8 per team

Your laptop plays the doorbell's microphone. You stream your team's audio from
Python to the ESP32-S3. The board keeps the recording, turns it into features
as the sound arrives, and sends those features back. You prove that nothing was
lost, build a labelled dataset, and measure how different the board's features
are from the laptop's.

This README is everything you need: the story, what to do in each mission, clues, and what
to hand in. **Find your team number in `TEAMS.csv`**; your audio is made from that number, so
always pass your own number to `team_audio.py`.

**The story.** The smart doorbell from Unit I must hear a spoken command. Before anyone trains
a model, the company needs to know the doorbell can take sound in fast enough, keep it safely,
and describe it in numbers a small model can use. Your team gets 144 one-second clips (24 each
of "on", "off", "stop", "go", other words and silence). The client's brief: *stream all 144
clips into the doorbell; keep the whole recording in a way that survives a power cut; compute
log-mel features on the board as the sound arrives and send them back; give us a labelled
feature dataset; show us what was lost; and tell us how different the board's features are
from a laptop's, and whether that matters.*

---

## 1. What is in this folder

| File | What it is | May you edit it? |
|---|---|---|
| `team_audio.py` | Your team's audio: 144 one-second clips (24 each of `on`, `off`, `stop`, `go`, `_unknown`, `_silence`). | **No** |
| `speech_pool.npz` | The recorded words `team_audio.py` uses (780 recordings, many voices). Keep it in the same folder | **No** |
| `board_link.py` | Talks to the board: `info()`, `stream()`, `save()`, `dump()`, `crc()`. | Yes, you may extend it |
| `doorbell_board_starter/doorbell_board_starter.ino` | The board sketch. Receives, stores in SRAM or PSRAM, computes features, sends them back. | Yes (Mission 2) |
| `doorbell_board_starter/features.h` | The board's feature maths. Correct, but slow. | Yes (Mission 3) |

You write everything else yourself: the quantiser and packer, the NumPy feature
pipeline, the loss accounting, the labelling, the dataset file and the comparison.

---

## 2. Set up (do this first, about 30 minutes)

1. Install Python 3.10 or newer, then:
   ```
   pip install numpy pyserial matplotlib
   ```
2. Install the **Arduino IDE** and the board package **esp32 by Espressif Systems, version 3.x**
   (Boards Manager).
3. Open `doorbell_board_starter/doorbell_board_starter.ino`. In **Tools**, set:
   - Board: **ESP32S3 Dev Module**
   - USB CDC On Boot: **Enabled**
   - Leave everything else alone for now. Some of these settings will matter later;
     working out which ones is part of the assignment.
4. Upload. The board has two USB-C ports, marked **USB** and **COM** (or UART). The sketch
   listens on both at once. Plug in both and list them:
   ```
   python board_link.py ports
   ```
5. Check the board answers, on each port:
   ```
   python board_link.py --port <PORT> info
   ```
   A line of memory numbers means you are ready.
6. Check your audio:
   ```
   python team_audio.py <TEAM_NUMBER>
   ```
   It writes `team_NN_preview.wav` with one clip of each class. Listen to it.

**Before Mission 1:** ask an LLM how many bytes per second you can send to an
ESP32-S3 over USB. Write its answer in your LLM log.

---

## 3. What you need to do

Every mission follows the same loop:
**write a prediction with a number → measure → explain the gap.**
Rotate the roles (Builder, Measurer, Skeptic, Scribe) for each mission.

### Mission 1: The pipe (data rate and data type)

Stream with `feat=False, store="none"` so the board only receives.

- [ ] Predict the bytes per second of 16 kHz audio as float32, int16 and int8, and what a 115,200 baud UART can carry.
- [ ] Measure the speed with `speed=0` on the **COM** port at 115,200, 921,600 and 2,000,000 baud, and on the **USB** port.
- [ ] Plot speed against baud for each port and explain the difference between the two ports.
- [ ] Fill in the real-time table: for 16 kHz f32/i16/i8 and 8 kHz i16/i8, can each port carry it at `speed=1`?
- [ ] Measure the effect of `samples_per_packet` = 8, 64, 320 and 1,024 (each frame carries 13 bytes of header and CRC).
- [ ] Work out the bytes per second the board sends back as features.

> **Clues.** A UART sends 10 bits per byte (start, 8 data, stop). One port goes through a USB-to-UART bridge chip; the other is USB built into the ESP32-S3. Look up "USB CDC" and ask what a baud rate means to it. pyserial's `write()` can return before the bytes have left your laptop. The first run of anything is often slower.

### Mission 2: What to send, and where to keep it (sampling, quantisation, storage)

- [ ] Write `quantise()` and `pack()` / `unpack()` in NumPy for int16 and int8 with a scale S.
- [ ] Plot spectra of a silence clip at 48 kHz and at 8 kHz without the filter. Find where the extra peak comes from and calculate its true frequency.
- [ ] Repeat at 8 kHz with `antialias=True`, and explain why the filter must come before sampling.
- [ ] Measure SQNR for int16 and int8, on a word clip and on a silence clip. Try a smaller S for int8.
- [ ] Choose your sampling rate, format and scale, and justify them.
- [ ] Find the longest recording that fits with `store="sram"`, then use `store="psram"`. If PSRAM refuses, find out why first.
- [ ] **Code:** finish `cmdSave()` in the sketch so `SAVE` writes the recording to flash with LittleFS.
- [ ] Make all 144 clips fit in flash (check `fs_total` in `info()`; find the Tools settings that decide it).
- [ ] Unplug, replug, `dump("flash")` and check the CRC against what you sent. Did the PSRAM copy survive?

> **Clues.** A tone at f, sampled at fs, shows up at its distance from the nearest whole multiple of fs. `np.fft.rfft` and `np.fft.rfftfreq` give a spectrum; plot it in dB. SQNR = 10·log10(signal power / error power). Your module is an **N16R8**: look up what the letters mean, and what "OPI" has to do with PSRAM. The Arduino default for this board assumes a 4 MB flash chip.

### Mission 3: Features on the board (windowing, log-mel/MFCC, speed of compute)

**Before Mission 3:** ask an LLM how long a 512-point FFT takes on an ESP32-S3. Log its answer.

- [ ] Write `features(x, fs, win, hop, nfft, mels, mfcc)` in NumPy, following the recipe in section 5.
- [ ] Plot the log-mel features of one clip of each class.
- [ ] Stream 10 s at `speed=1` with features on, using the starter. Read `compute_us` and `lag_s`. Is the board keeping up? Compare what happens on the USB port and on the COM port.
- [ ] **Code:** make `features.h` fast enough. Every output must stay within **0.05 dB** of your NumPy version. Record the time per frame before and after.
- [ ] Find the fastest `speed` with features off and with features on. Which is the bottleneck: the pipe or the compute?
- [ ] Try win 25 ms / hop 10 ms, and 13 MFCCs instead of 40 log-mel values. Report the compute time and the bytes sent back.

> **Clues.** Count how many times the starter calls `cosf` and `sinf` per frame. Look up "twiddle factor table" and "radix-2 FFT". Espressif ships a DSP library for this chip (ESP-DSP); you may use it if you can explain what it does. Compare the board and NumPy on the **same quantised** samples.

### Mission 4: Nothing lost (loss accounting, labelled dataset, data card)

- [ ] Predict how many packets, samples and feature frames there will be for all 144 clips.
- [ ] Stream all 144 clips at `speed=1`. Check every count: `packets_sent`, `board["frames_ok"]`, `seq_gaps`, `bad_crc`, `samples`, `expected_features` vs received.
- [ ] Run again with `skip=(10, 11, 200)`. Show that your accounting finds exactly those three packets, and explain what happens to `first_sample` after the gap.
- [ ] **Code:** make sure a lost packet cannot shift the labels of everything after it.
- [ ] On the COM port, raise `speed` until data goes missing. Find the fastest zero-loss setting on each port.
- [ ] Label every feature frame using `first_sample` and `clip_list()`. Decide, and explain, what to do with frames that straddle two clips.
- [ ] Save the dataset (`.npz` or `.csv`): features, label, clip id and `first_sample` for every frame.
- [ ] Write the **data card** (half a page): source, stream settings, frames per class, what was lost and how you know, known problems, and what the data should not be used for.

> **Clues.** A sequence number tells you a packet is missing; a CRC tells you a packet is damaged. They catch different failures. Think about what happens when the board's receive buffer fills faster than it reads.

### Mission 5: Laptop vs board (domain shift)

- [ ] Compute laptop features from the **original** float32 clips (16 kHz, filter on) and compare them frame by frame with the board's. Report the mean and worst difference in dB, per band and per class.
- [ ] Separate the causes: compare the board with NumPy run on the **same quantised** samples.
- [ ] Repeat for at least two more settings: int8 with S = 1, int8 with a smaller S, and 8 kHz without the filter (compare that one against 8 kHz laptop features from the filtered clips). Show each as a heat map of the difference.
- [ ] Train a nearest-centroid classifier on laptop features (per-clip mean and standard deviation of each band) using two thirds of the clips. Test it on the other third with laptop features, then with board features, for each setting.
- [ ] Choose the setting you would ship, and defend it with your numbers.


> **Clues.** Nearest centroid: average the training vectors of each class, then label each test vector by the closest average. Standardise each dimension with the training set's mean and spread first. Quantisation noise sets a floor under the quietest bands; clipping moves the loudest.
---

## 4. What to hand in

**Last date of submission: Monday, 30 November 2026.** How to submit will be announced.
Put everything in one folder named `team_NN_module2/` and zip it.

| # | Item | Format |
|---|---|---|
| 1 | Mission records for Missions 1 to 5, each using the eight headings below | PDF |
| 2 | All your Python code | `.py` or `.ipynb` |
| 3 | Your finished board sketch (`.ino` + `features.h`) and the Tools settings you used | folder |
| 4 | Your dataset | `.npz` or `.csv` |
| 5 | The data card | inside the PDF or as `data_card.md` |
| 6 | The one-page commitment memo to the client | inside the PDF |
| 7 | LLM log and team reflection (who held which role in each mission) | inside the PDF |

**The eight headings for every mission record:**
1. Aim · 2. Background · 3. Prediction · 4. Method · 5. Observations · 6. Analysis · 7. What we learnt · 8. LLM log

**The commitment memo must state:** sampling rate, filter, format and scale (and how the
doorbell would choose the scale before hearing anything); port, speed and margin over real
time; where the recording lives, its size, the Tools settings and the room left; feature
settings, compute time against its budget, and bytes per second sent back; what was lost and
how you know; the laptop-vs-board difference and whether it matters; and the one thing most
likely to break your design.

**Live run and live check:** on the day, stream all 144 clips with your memo's settings,
`SAVE`, unplug and replug, `dump` and check the CRC, and show your loss counts and dataset.
Then any one of you will be asked how the design changes when one number changes. Everyone
must be able to answer without a laptop.

---

## 5. Quick reference

### The feature recipe (board and NumPy must match)
1. **Frame:** frame k = samples `k*hop` to `k*hop + win - 1`, whole frames only. Start with win = 30 ms, hop = 20 ms.
2. **Window:** multiply by `np.hanning(win)`.
3. **Spectrum:** zero-pad to `nfft` (a power of 2, at least `win`), FFT, then `P[k] = |X[k]|^2 / nfft` for k = 0 … nfft/2.
4. **Mel bands:** `mels` triangles with edges evenly spaced on mel = 2595·log10(1 + f/700), from 20 Hz to fs/2.
5. **Log:** `10*log10(max(band, 1e-10))`.
6. **MFCC (optional):** orthonormal DCT-II of the log-mel vector, keeping the first `mfcc` values.

### Quantisation
```
q    = clip(round(x / S * (2**(b-1) - 1)), -2**(b-1), 2**(b-1) - 1)
xhat = q * S / (2**(b-1) - 1)
```
int16: `astype("<i2")`, int8: `astype(np.int8)`, float32: `astype("<f4")`, then `.tobytes()`.

### `team_audio.py`
```python
from team_audio import CLASSES, clip_list, get_clip
clips = clip_list(team)                         # [(clip_id, label), ...] 144 entries
x = get_clip(team, clip_id, fs=16000, antialias=True)   # float32, 1 s, values in -1..1
```
Allowed `fs`: 48000, 24000, 16000, 12000, 8000, 6000, 4000.

### `board_link.py`
```python
from board_link import Board
b = Board("COM5", baud=921600)
b.info()                       # memory, PSRAM, flash and file-system sizes
b.set_baud(2000000)            # COM port only
r = b.stream(payload, fs=16000, fmt="i16", scale=1.0,
             win=480, hop=320, nfft=512, mels=40, mfcc=0,
             feat=True, store="psram", max_bytes=0,
             speed=1.0, samples_per_packet=320, skip=())
b.save()                       # needs your SAVE code in the sketch
data = b.dump("psram")         # or "sram" / "flash"
b.crc("flash")
```
What `stream()` returns:

| Key | Meaning |
|---|---|
| `features` | (frames × mels or mfcc) array, computed **on the board** |
| `first_sample` | index of each frame's first sample, as the board counted it |
| `compute_us` | board time per frame, in microseconds |
| `lag_s` | how late each frame arrived after its last sample was due (only when `speed > 0`) |
| `expected_features`, `lost_features` | how many frames should have come back, and how many did not |
| `packets_sent`, `bytes_sent`, `send_seconds` | the laptop's side of the stream |
| `bad_crc_back` | damaged frames on the way back |
| `board` | the board's own summary: `frames_ok`, `bad_crc`, `seq_gaps`, `dup`, `samples`, `stored`, `store_full`, `features`, `max_us`, `avg_us`, `uart_errors`, `ms` |

`speed=1.0` is real time, `4.0` is four times faster, and `0` is as fast as the link allows.
`feat=False` makes the board only receive and store.

### Wire format (if you extend the code)
```
laptop -> board : A5 5A | type | seq u32 | len u16 | payload | crc32     type 'D' samples, 'E' end
board -> laptop : B5 5B | type | seq u32 | len u16 | payload | crc32     'F' features, 'S' summary
```
Little-endian. The CRC is `zlib.crc32` over type, seq, len and payload. A frame carries at most 4,096 payload bytes.

---

## 6. Rules for using an LLM

- Use it to explain, to check your reasoning, to explain error messages, and for hints. Do not use it for finished code.
- **The board is the judge.** If an LLM makes a claim you can test, test it.
- Everyone must be able to explain every line you submit.
- Keep an LLM log for every mission. Using an LLM costs you nothing; hiding it will.

## 7. When things go wrong

| Problem | Try |
|---|---|
| No port appears | The other USB-C port; a different cable (some carry power only) |
| Upload fails: "Failed to connect" | Hold **BOOT** while the IDE says "Connecting..." |
| `info()` times out | Right port? On COM, does your baud match the board's? Press **RST** |
| `stream()` returns no features | Read `r["board"]["why"]`; a stream with no END stops after 3 s of silence |
| `ERR no psram` | Read the clues in Mission 2. Don't change code until you know why |
| `ERR flash full` / `no filesystem` | Check `fs_total` in `info()` and your Tools settings |
| Board restarts in a loop | Read the serial monitor message before changing anything |
| A result looks impossible | Good: that is the Skeptic's job. Find another explanation and test it |

Still stuck? Ask a teammate, then an LLM (and check what it says), then your instructor.

*Predict honestly. Measure carefully. Explain everything.*
