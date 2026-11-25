import sys
import json
import zlib
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
print("MISSION 2 - PERSISTENT FLASH STORAGE TEST")
print("=" * 65)

# Generate the complete Team 14 dataset
audio = np.concatenate([
    get_clip(TEAM, clip_id, fs=FS, antialias=True)
    for clip_id, label in clip_list(TEAM)
])

payload = pack(audio, BITS, SCALE)
laptop_crc = zlib.crc32(payload)

print("\nTotal clips:", len(clip_list(TEAM)))
print("Total samples:", len(audio))
print("Payload bytes:", len(payload))
print(f"Laptop CRC32: {laptop_crc:08X}")

b = Board(PORT, baud=BAUD)

try:

    info = b.info()

    print("\nInitial board information:")
    print(info)

    available_flash = info["fs_total"] - info["fs_used"]

    print("Available flash:", available_flash)

    if available_flash < len(payload):
        raise RuntimeError("Insufficient flash storage")

    b.free()

    # Stream complete dataset to PSRAM
    print("\n--- STREAMING TO PSRAM ---")

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

    assert board is not None
    assert board["why"] == "end"
    assert board["samples"] == len(audio)
    assert board["stored"] == len(payload)
    assert board["bad_crc"] == 0
    assert board["bad_len"] == 0
    assert board["seq_gaps"] == 0
    assert board["dup"] == 0
    assert board["store_full"] == 0
    assert board["uart_errors"] == 0

    # Verify PSRAM integrity
    psram_crc = b.crc("psram")

    print("\nPSRAM CRC:", psram_crc)

    assert psram_crc["crc"] == laptop_crc
    assert psram_crc["n"] == len(payload)

    print("PSRAM verification: PASS")

    # Save recording to flash
    print("\n--- SAVING TO LITTLEFS ---")

    save_result = b.save()

    print("SAVE response:", save_result)

    assert save_result["n"] == len(payload)
    assert save_result["crc"] == laptop_crc

    save_time = save_result["us"] / 1_000_000

    print(f"Save time: {save_time:.4f} seconds")

    if save_time > 0:
        write_speed = len(payload) / save_time
        print(f"Flash write speed: {write_speed:.2f} B/s")
    else:
        write_speed = None

    # Independently verify flash contents
    print("\n--- VERIFYING FLASH ---")

    flash_crc = b.crc("flash")

    print("Flash CRC:", flash_crc)

    assert flash_crc["n"] == len(payload)
    assert flash_crc["crc"] == laptop_crc

    print("Flash CRC verification: PASS")

    final_info = b.info()

    print("\nFinal board information:")
    print(final_info)

    # Save evidence for the report
    results = {
        "team": TEAM,
        "clips": len(clip_list(TEAM)),
        "sampling_rate": FS,
        "format": "int16",
        "scale": SCALE,
        "total_samples": len(audio),
        "payload_bytes": len(payload),
        "laptop_crc": laptop_crc,
        "laptop_crc_hex": f"{laptop_crc:08X}",
        "psram_crc": psram_crc,
        "flash_crc": flash_crc,
        "save_response": save_result,
        "save_time_seconds": save_time,
        "flash_write_bytes_per_second": write_speed,
        "stream_summary": board,
        "initial_info": info,
        "final_info": final_info,
        "status": "PASS"
    }

    result_path = RESULTS_DIR / "flash_test_results.json"

    with open(result_path, "w") as f:
        json.dump(results, f, indent=4)

    print("\nResults saved to:", result_path)

    print("\n" + "=" * 65)
    print("FLASH STORAGE TEST PASSED")
    print("=" * 65)

finally:
    b.close()