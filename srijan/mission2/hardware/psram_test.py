import sys
import zlib
import csv
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR.parents[2]))
sys.path.insert(0, str(BASE_DIR.parent))

from board_link import Board
from team_audio import get_clip
from quantisation import pack

TEAM = 14
PORT = "COM6"
BAUD = 921600
FS = 16000
BITS = 16
SCALE = 1.0

DURATIONS = [10, 60, 144]

results = []

b = Board(PORT, baud=BAUD)

print("=" * 65)
print("MISSION 2 - PSRAM CAPACITY TEST")
print("=" * 65)

try:

    info = b.info()

    print("\nInitial board information:")
    print(info)

    if info["psram_size"] == 0:
        raise RuntimeError("PSRAM is not enabled")

    for duration in DURATIONS:

        print(f"\n--- Testing {duration} seconds ---")

        audio = np.concatenate([
            get_clip(
                TEAM, i,
                fs=FS,
                antialias=True
            )
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
                store="psram",
                max_bytes=len(payload),
                speed=1.0,
                samples_per_packet=320
            )

            board = r["board"]

            print("Board response:", board)

            laptop_crc = zlib.crc32(payload)
            board_crc = b.crc("psram")

            print(f"Laptop CRC: {laptop_crc:08X}")
            print("Board CRC:", board_crc)

            passed = (
                board_crc.get("crc") == laptop_crc
                and board_crc.get("n") == len(payload)
                and board.get("samples") == len(audio)
                and board.get("stored") == len(payload)
                and board.get("bad_crc") == 0
                and board.get("bad_len") == 0
                and board.get("seq_gaps") == 0
                and board.get("dup") == 0
                and board.get("store_full") == 0
                and board.get("uart_errors") == 0
            )

            status = "PASS" if passed else "FAIL"

            print("RESULT:", status)

            results.append({
                "duration_seconds": duration,
                "required_bytes": len(payload),
                "stored_bytes": board.get("stored"),
                "samples": board.get("samples"),
                "bad_crc": board.get("bad_crc"),
                "sequence_gaps": board.get("seq_gaps"),
                "uart_errors": board.get("uart_errors"),
                "laptop_crc": laptop_crc,
                "board_crc": board_crc.get("crc"),
                "status": status
            })

            if not passed:
                break

            print("\nMemory after recording:")
            print(b.info())

            b.free()

        except RuntimeError as e:

            print("RESULT: FAIL")
            print("Reason:", e)
            break

finally:
    b.close()


# Save experimental results

results_dir = BASE_DIR.parent / "results"
results_dir.mkdir(exist_ok=True)

if results:

    csv_path = results_dir / "psram_test_results.csv"

    with open(csv_path, "w", newline="") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(results[0].keys())
        )

        writer.writeheader()
        writer.writerows(results)

    print("\nResults saved to:", csv_path)

print("\nPSRAM capacity experiment completed.")