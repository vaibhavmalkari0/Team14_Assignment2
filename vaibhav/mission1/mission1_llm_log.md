# Mission 1 LLM Log

## USB throughput claim

**Question:** How quickly can data move between a laptop and an ESP32-S3 over native USB CDC?

**Claim recorded:** Native USB uses USB 2.0 Full-Speed signalling at 12 Mbps (1.5 MB/s theoretical); application throughput must be measured because it depends on USB CDC firmware and transfer size. USB-UART bridges are limited by their configured baud rate.

**Board result:** USB CDC through COM6 measured 456,798 bytes/s with 320-sample int16 packets and 513,312 bytes/s with 1,024-sample int16 packets, with no loss in those tests.

## 512-point FFT claim

**Question:** How long does a 512-point FFT take on an ESP32-S3?

**Claim recorded:** Espressif ESP-DSP reports 44,594 CPU cycles for a 512-point 32-bit floating-point complex FFT (`dsps_fft2r_fc32`) at 240 MHz, approximately 0.186 ms for the optimized FFT kernel.

**Caveat:** This cycle count may exclude windowing, input preparation, bit reversal, magnitude calculation, and mel-bank processing. Mission 3 must measure the complete board feature pipeline.
