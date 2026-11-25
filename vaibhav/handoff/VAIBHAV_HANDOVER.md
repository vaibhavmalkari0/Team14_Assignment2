# Vaibhav Handover Record

**Team:** 14 - Saura
**Owner:** Vaibhav Malkari
**Handoff to:** Sumadhwa J
**Status:** Partially complete - handoff should wait for the remaining COM/USB items listed below

## Port reconciliation

COM port numbers are assigned dynamically by Windows and are not permanent board identities.

Confirmed board responses:

- COM5 at 921600 baud: board `INFO` obtained earlier
- COM6 at 921600 baud: board `INFO` obtained and confirmed with the native USB cable

COM5 is the USB-UART bridge and COM6 was previously confirmed as native USB. Port visibility changes when cables are unplugged: the latest shared port listing showed COM5 only. COM5 is currently verified at 921600 baud; use `python board_link.py ports` and `info` to re-identify ports before another session.

## Completed

- [x] Python 3.12.10 is available.
- [x] NumPy, PySerial, and Matplotlib imports succeeded.
- [x] Team 14 preview WAV was generated successfully.
- [x] The ESP32-S3 board responds through native USB at COM6.
- [x] `INFO` was obtained: 256 KB heap, 16 MB flash, 1,441,792-byte LittleFS, no active PSRAM allocation.
- [x] COM5 UART speed measurements were recorded at 115200, 921600, and 2000000 baud.
- [x] COM5 16 kHz int16 real-time tests were recorded at 115200, 921600, and 2000000 baud; all 16000 samples arrived without CRC or sequence errors.
- [x] COM5 packet-size measurements were recorded at 8, 64, 320, and 1024 samples per packet.
- [x] COM6 native USB packet-size measurements were recorded at 8, 64, 320, and 1024 samples per packet.
- [x] Native USB 8-sample packets were repeated and found to lose data.
- [x] Native USB real-time tests were recorded for all five required audio formats.
- [x] LLM USB and 512-point FFT claims were recorded.
- [x] COM and USB throughput plots were generated.
- [x] Raw Mission 1 measurements were saved in CSV format.
- [x] Mission 1 report was completed with all eight required headings, the measured data, plots, and incomplete-feature caveat.
- [x] Feature-return attempt was recorded; it returned 6 of 49 expected feature frames and did not provide a board summary.

## Observations

- COM5 115200: 11,336 bytes/s
- COM5 921600: 89,992 bytes/s
- COM5 2000000: 189,174 bytes/s
- COM real-time tests: all formats arrived with 0 sequence gaps and 0 CRC errors. At 115200, 16 kHz float32 took 5.612 s, 16 kHz int8 1.460 s, and 8 kHz int16 1.452 s; these are not real-time. 8 kHz int8 took 1.028 s (borderline). At 921600 and 2000000, all five tested formats completed close to one second with no loss.
- COM5 int16 at `speed=1`: 115200 took 2.844 s; 921600 took 1.008 s; 2000000 took 1.004 s. Each run received 16000 samples with 0 sequence gaps and 0 bad CRCs. The 115200 test is loss-free but not real-time.
- Feature return: 6/49 frames, 960 feature-value bytes in 11.416 s; 43 features missing, no bad CRC on return, and no board summary. This is incomplete and is not a valid full-stream throughput result.
- A Python REPL `SyntaxError` occurred when the continuation prompt (`...`) was typed as part of the command; it was a prompt-copying error, not a board or firmware failure.
- COM6 64-sample packets: 370,809 bytes/s
- COM6 320-sample packets: 456,798 bytes/s
- COM6 1024-sample packets: 513,312 bytes/s
- Native USB repeated 8-sample test: 15936/16000 samples received, 3 bad CRC frames
- Packet overhead: 13 bytes per frame

## Not finished

- [x] COM `speed=1` tests for all five formats at 115200, 921600, and 2000000 baud; results and timing are in `mission1_results.csv`.
- [ ] Native USB throughput plotted after a final repeat of the 64/320/1024-sample tests
- [ ] Separate first-run slowdown measurements for COM and USB
- [ ] Complete feature-return throughput measurement; current attempt returned only 6/49 frames
- [ ] Two-port repeat evidence from both ports connected simultaneously
- [x] Mission 1 PDF using all eight required headings
- [x] Written explanation of 115200-baud capacity and the UART/USB CDC distinction
- [x] Updated handoff archive with Mission 1 report, data, plots, and plan.

## Current blocker

The feature test remains **incomplete**. The starter feature pipeline returned only 6 of 49 expected frames for a one-second clip, and `r["board"]` was `None` after the host's stream wait. Do not report the partial 960 feature-value bytes as a completed throughput measurement.

## Firmware follow-up for Srijan

**Owner:** Srijan Kumar GS (board firmware and feature optimization)

**Reproduction:** COM5 at 921600 baud; one Team 14 clip; 16 kHz int16; `feat=True`, `store="none"`, `speed=0`, `win=480`, `hop=320`, `nfft=512`, `mels=40`, `mfcc=0`, `samples_per_packet=320`.

**Observed:** 6 feature frames received of 49 expected, 43 lost, `bad_crc_back=0`, and no board summary after 11.416 seconds.

**Completion criteria:** Re-run the same settings and verify all 49 feature frames arrive (`lost_features == 0`) and the board summary is present. Then record the elapsed time and calculate feature-value bytes/s from the complete result. Until those checks pass, keep this task marked incomplete.

Please hand this reproduction and result to Srijan before claiming feature-return throughput. COM5 can disappear or be renamed after reconnecting; check the current port list before opening it.

## Handoff package

Vaibhav should hand these files to Sumadhwa:

- `team_14_preview.wav`
- `mission1_report.pdf`
- `mission1_results.csv`
- `mission1_llm_log.md`
- `mission1_com_throughput.png`
- `mission1_usb_throughput.png`
- `board_link.py`
- `team_audio.py`
- `doorbell_board_starter/doorbell_board_starter.ino`
- `doorbell_board_starter/features.h`
- `VAIBHAV_HANDOVER.md`

Sumadhwa should not proceed as if Vaibhav's Mission 1 section is complete. The remaining items above must be resolved or explicitly marked impossible due to unavailable COM access.
