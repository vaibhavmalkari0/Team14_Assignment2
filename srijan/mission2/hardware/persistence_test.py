import sys
import json
import zlib
import time
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR.parents[2]))
sys.path.insert(0, str(BASE_DIR.parent))

from board_link import Board
from team_audio import get_clip, clip_list
from quantisation import pack

TEAM = 14
PORT = "COM6"
BAUD = 921600
FS = 16000
BITS = 16
SCALE = 1.0

RESULTS_DIR = BASE_DIR.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

print("=" * 65)
print("MISSION 2 - PERSISTENT DATA RETRIEVAL TEST")
print("=" * 65)

# Regenerate the original Team 14 dataset
audio = np.concatenate([
    get_clip(
        TEAM, clip_id,
        fs=FS,
        antialias=True
    )
    for clip_id, label in clip_list(TEAM)
])

original = pack(audio, BITS, SCALE)
original_crc = zlib.crc32(original)

print("\nOriginal bytes:", len(original))
print(f"Original CRC32: {original_crc:08X}")

b = Board(PORT, baud=BAUD)

try:

    info = b.info()

    print("\nBoard information after power cycle:")
    print(info)

    # Verify flash CRC
    flash_crc = b.crc("flash")

    print("\nFlash CRC:", flash_crc)

    assert flash_crc["n"] == len(original)
    assert flash_crc["crc"] == original_crc

    print("Post-power-cycle CRC verification: PASS")

    # Retrieve the complete recording
    print("\nRetrieving recording from LittleFS...")
    print("Downloading", len(original), "bytes", flush=True)

    start = time.perf_counter()

    retrieved = b.dump("flash")

    elapsed = time.perf_counter() - start

    retrieved_crc = zlib.crc32(retrieved)

    print("\n--- RETRIEVAL RESULTS ---")

    print("Original bytes:", len(original))
    print("Retrieved bytes:", len(retrieved))

    print(f"Original CRC32:  {original_crc:08X}")
    print(f"Retrieved CRC32: {retrieved_crc:08X}")

    print(f"Retrieval time: {elapsed:.3f} seconds")
    print(f"Retrieval speed: {len(retrieved)/elapsed:.2f} B/s")

    # Verify byte-by-byte equality
    same_length = len(original) == len(retrieved)
    exact_match = original == retrieved

    if same_length:

        original_array = np.frombuffer(
            original, dtype=np.uint8
        )

        retrieved_array = np.frombuffer(
            retrieved, dtype=np.uint8
        )

        mismatched_bytes = int(np.count_nonzero(
            original_array != retrieved_array
        ))

    else:
        mismatched_bytes = None

    print("\n--- DATA INTEGRITY ---")
    print("Length match:", same_length)
    print("CRC32 match:", original_crc == retrieved_crc)
    print("Mismatched bytes:", mismatched_bytes)
    print("Exact byte-by-byte match:", exact_match)

    passed = (
        same_length
        and original_crc == retrieved_crc
        and exact_match
        and mismatched_bytes == 0
    )

    # Save experimental evidence
    results = {
        "team": TEAM,
        "sampling_rate": FS,
        "format": "int16",
        "scale": SCALE,
        "original_bytes": len(original),
        "retrieved_bytes": len(retrieved),
        "original_crc32": f"{original_crc:08X}",
        "retrieved_crc32": f"{retrieved_crc:08X}",
        "retrieval_time_seconds": elapsed,
        "retrieval_speed_bytes_per_second":
            len(retrieved) / elapsed,
        "length_match": same_length,
        "crc_match": original_crc == retrieved_crc,
        "mismatched_bytes": mismatched_bytes,
        "exact_byte_match": exact_match,
        "board_info_after_power_cycle": info,
        "status": "PASS" if passed else "FAIL"
    }

    result_path = RESULTS_DIR / "persistence_test_results.json"

    with open(result_path, "w") as f:
        json.dump(results, f, indent=4)

    print("\nResults saved to:", result_path)

    print("\n" + "=" * 65)

    if passed:
        print("PERSISTENT STORAGE VERIFICATION PASSED")
        print("ALL AUDIO BYTES RECOVERED WITHOUT CORRUPTION")
    else:
        print("PERSISTENT STORAGE VERIFICATION FAILED")

    print("=" * 65)

    assert passed, "Retrieved recording does not match original"

finally:
    b.close()