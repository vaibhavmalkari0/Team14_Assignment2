import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from board_link import Board
from team_audio import get_clip
from quantisation import pack

TEAM = 14
PORT = "COM6"
BAUD = 921600
FS = 16000
BITS = 16
SCALE = 1.0

DURATIONS = [1, 3, 5, 6, 7, 10]

b = Board(PORT, baud=BAUD)

print("=" * 65)
print("MISSION 2 - SRAM CAPACITY TEST")
print("=" * 65)

try:
    print("\nInitial board information:")
    print(b.info())

    for duration in DURATIONS:

        print(f"\n--- Testing {duration} seconds ---")

        audio = np.concatenate([
            get_clip(TEAM, i, fs=FS, antialias=True)
            for i in range(duration)
        ])

        payload = pack(audio, BITS, SCALE)

        print("Required memory:", len(payload), "bytes")

        try:
            b.free()

            r = b.stream(
                payload,
                fs=FS,
                fmt="i16",
                scale=SCALE,
                feat=False,
                store="sram",
                max_bytes=len(payload),
                speed=1.0,
                samples_per_packet=320
            )

            print("Board response:", r["board"])

            # Compare laptop and board CRC32
            laptop_crc = zlib.crc32(payload)
            board_crc = b.crc("sram")

            print(f"Laptop CRC: {laptop_crc:08X}")
            print("Board CRC:", board_crc)

            if (
                board_crc.get("crc") == laptop_crc
                and board_crc.get("n") == len(payload)
            ):
                print("RESULT: PASS - Data stored correctly")
            else:
                print("RESULT: FAIL - Data mismatch")
                break

            b.free()

        except RuntimeError as e:
            print("RESULT: FAIL")
            print("Reason:", e)
            break

finally:
    b.close()

print("\nSRAM capacity experiment completed.")