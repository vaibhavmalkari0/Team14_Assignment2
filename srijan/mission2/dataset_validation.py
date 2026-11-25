import sys
import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parents[1]

sys.path.insert(0, str(ROOT_DIR))

from team_audio import get_clip, clip_list
from quantisation import pack, unpack

TEAM = 14

SAMPLING_RATES = [8000, 16000, 48000]

CONFIGURATIONS = [
    (16, 1.0),
    (8, 1.0),
    (8, 0.5),
    (8, 0.25),
    (8, 0.125),
    (8, 0.0625)
]

RESULTS_DIR = BASE_DIR / "results"
PLOTS_DIR = BASE_DIR / "plots"

RESULTS_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)

clips = clip_list(TEAM)
results = []
summary = []


def calculate_sqnr(original, reconstructed):
    original = original.astype(np.float64)
    reconstructed = reconstructed.astype(np.float64)

    signal_power = np.mean(original ** 2)
    noise_power = np.mean(
        (original - reconstructed) ** 2
    )

    if noise_power == 0:
        return np.inf if signal_power > 0 else np.nan

    if signal_power == 0:
        return -np.inf

    return 10 * np.log10(signal_power / noise_power)


def count_clipped(x, bits, scale):
    qmax = 2**(bits - 1) - 1
    qmin = -(2**(bits - 1))

    q = np.round(
        x.astype(np.float64) / scale * qmax
    )

    return np.count_nonzero(
        (q < qmin) | (q > qmax)
    )


print("=" * 80)
print("MISSION 2 - FULL DATASET VALIDATION")
print("Team:", TEAM)
print("Total clips:", len(clips))
print("=" * 80)


for fs in SAMPLING_RATES:

    print(f"\nProcessing {fs} Hz...")

    audio = [
        (clip_id, label, get_clip(
            TEAM, clip_id,
            fs=fs, antialias=True
        ))
        for clip_id, label in clips
    ]

    print(
        "Dataset peak amplitude:",
        max(np.max(np.abs(x)) for _, _, x in audio)
    )

    for bits, scale in CONFIGURATIONS:

        sqnr_values = []
        clipped_samples = 0
        total_samples = 0
        clipped_clips = 0
        total_bytes = 0

        for clip_id, label, x in audio:

            payload = pack(x, bits, scale)
            reconstructed = unpack(
                payload, bits, scale
            )

            assert len(reconstructed) == len(x)
            assert len(payload) == len(x) * (bits // 8)

            sqnr = calculate_sqnr(x, reconstructed)

            clipped = count_clipped(
                x, bits, scale
            )

            sqnr_values.append(sqnr)

            clipped_samples += clipped
            total_samples += len(x)
            total_bytes += len(payload)

            if clipped > 0:
                clipped_clips += 1

            results.append({
                "team": TEAM,
                "clip_id": clip_id,
                "label": label,
                "sampling_rate": fs,
                "bits": bits,
                "scale": scale,
                "sqnr_db": sqnr,
                "clipped_samples": clipped,
                "clipping_percent":
                    100 * clipped / len(x),
                "payload_bytes": len(payload)
            })

        mean_sqnr = np.nanmean(sqnr_values)
        median_sqnr = np.nanmedian(sqnr_values)
        min_sqnr = np.nanmin(sqnr_values)

        clipping_percent = (
            100 * clipped_samples / total_samples
        )

        row = {
            "sampling_rate": fs,
            "bits": bits,
            "scale": scale,
            "mean_sqnr_db": mean_sqnr,
            "median_sqnr_db": median_sqnr,
            "min_sqnr_db": min_sqnr,
            "clipping_percent": clipping_percent,
            "clipped_clips": clipped_clips,
            "bytes_per_second": fs * (bits // 8),
            "total_storage_bytes": total_bytes
        }

        summary.append(row)

        print(
            f"int{bits:2d} | "
            f"S={scale:<7} | "
            f"Mean SQNR={mean_sqnr:7.2f} dB | "
            f"Min SQNR={min_sqnr:7.2f} dB | "
            f"Clipping={clipping_percent:7.4f}% | "
            f"Clipped clips={clipped_clips}/144"
        )


# Save all individual clip measurements
with open(
    RESULTS_DIR / "dataset_validation.csv",
    "w", newline=""
) as f:

    writer = csv.DictWriter(
        f, fieldnames=list(results[0].keys())
    )

    writer.writeheader()
    writer.writerows(results)


# Save configuration summaries
with open(
    RESULTS_DIR / "configuration_summary.csv",
    "w", newline=""
) as f:

    writer = csv.DictWriter(
        f, fieldnames=list(summary[0].keys())
    )

    writer.writeheader()
    writer.writerows(summary)


# Identify best zero-clipping int8 configurations
print("\n--- BEST ZERO-CLIPPING INT8 CONFIGURATIONS ---")

for fs in SAMPLING_RATES:

    candidates = [
        r for r in summary
        if r["sampling_rate"] == fs
        and r["bits"] == 8
        and r["clipped_clips"] == 0
    ]

    if candidates:

        best = max(
            candidates,
            key=lambda r: r["mean_sqnr_db"]
        )

        print(
            f"{fs} Hz | "
            f"Scale={best['scale']} | "
            f"Mean SQNR={best['mean_sqnr_db']:.2f} dB | "
            f"Storage={best['total_storage_bytes']} bytes"
        )

    else:
        print(f"{fs} Hz: No zero-clipping configuration")


# Plot full dataset SQNR comparison
plt.figure(figsize=(12, 6))

labels = [
    f"int{bits}\nS={scale}"
    for bits, scale in CONFIGURATIONS
]

positions = np.arange(len(labels))
width = 0.25

for i, fs in enumerate(SAMPLING_RATES):

    values = [
        r["mean_sqnr_db"]
        for r in summary
        if r["sampling_rate"] == fs
    ]

    plt.bar(
        positions + (i - 1) * width,
        values,
        width,
        label=f"{fs} Hz"
    )

plt.xticks(positions, labels)
plt.ylabel("Mean SQNR (dB)")
plt.title("Team 14 - Full Dataset SQNR Comparison")
plt.legend()
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

plt.savefig(
    PLOTS_DIR / "dataset_sqnr_comparison.png",
    dpi=200
)


# Plot storage requirements
plt.figure(figsize=(10, 6))

for bits in [8, 16, 32]:

    storage = [
        len(clips) * fs * (bits // 8) / 1e6
        for fs in SAMPLING_RATES
    ]

    label = "float32" if bits == 32 else f"int{bits}"

    plt.plot(
        SAMPLING_RATES,
        storage,
        marker="o",
        label=label
    )

plt.xlabel("Sampling rate (Hz)")
plt.ylabel("Total raw audio storage (MB)")
plt.title("Storage Requirements for 144 Audio Clips")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

plt.savefig(
    PLOTS_DIR / "storage_comparison.png",
    dpi=200
)

print("\nAll dataset validation experiments completed.")
print("Results saved to:", RESULTS_DIR)
print("Graphs saved to:", PLOTS_DIR)

plt.show()