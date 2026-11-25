import sys
import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parents[1]

sys.path.insert(0, str(ROOT_DIR))

from team_audio import get_clip
from quantisation import quantise, pack, unpack

TEAM = 14
FS = 16000

PLOTS_DIR = BASE_DIR / "plots"
RESULTS_DIR = BASE_DIR / "results"

PLOTS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

CLIPS = {
    "Word": 0,
    "Silence": 120
}

CONFIGURATIONS = [
    (16, 1.0),
    (8, 1.0),
    (8, 0.5),
    (8, 0.25),
    (8, 0.125),
    (8, 0.0625)
]


# Calculate Signal-to-Quantisation-Noise Ratio
def calculate_sqnr(original, reconstructed):

    original = np.asarray(original, dtype=np.float64)
    reconstructed = np.asarray(
        reconstructed, dtype=np.float64
    )

    signal_power = np.mean(original ** 2)

    error = original - reconstructed
    noise_power = np.mean(error ** 2)

    if noise_power == 0:
        return np.inf if signal_power > 0 else np.nan

    if signal_power == 0:
        return -np.inf

    return 10 * np.log10(signal_power / noise_power)


# Calculate percentage of samples requiring clipping
def calculate_clipping(x, bits, scale):

    qmax = 2**(bits - 1) - 1
    qmin = -(2**(bits - 1))

    rounded = np.round(
        np.asarray(x, dtype=np.float64) / scale * qmax
    )

    clipped = (rounded < qmin) | (rounded > qmax)

    return 100 * np.mean(clipped)


results = []

print("=" * 75)
print("MISSION 2 - SQNR ANALYSIS")
print("Team:", TEAM)
print("Sampling rate:", FS)
print("Anti-aliasing: Enabled")
print("=" * 75)


# Perform experiments
for clip_type, clip_id in CLIPS.items():

    x = get_clip(
        TEAM,
        clip_id,
        fs=FS,
        antialias=True
    )

    print(f"\n--- {clip_type} Clip (ID {clip_id}) ---")
    print(f"Samples: {len(x)}")
    print(f"Peak amplitude: {np.max(np.abs(x)):.6f}")
    print(f"RMS amplitude: {np.sqrt(np.mean(x**2)):.6f}")

    for bits, scale in CONFIGURATIONS:

        payload = pack(x, bits, scale)
        reconstructed = unpack(payload, bits, scale)

        sqnr = calculate_sqnr(x, reconstructed)

        clipping = calculate_clipping(
            x, bits, scale
        )

        error = x - reconstructed

        mse = np.mean(error ** 2)
        max_error = np.max(np.abs(error))

        result = {
            "team": TEAM,
            "clip_type": clip_type,
            "clip_id": clip_id,
            "sampling_rate": FS,
            "bits": bits,
            "scale": scale,
            "sqnr_db": float(sqnr),
            "clipping_percent": float(clipping),
            "mse": float(mse),
            "max_error": float(max_error),
            "payload_bytes": len(payload)
        }

        results.append(result)

        print(
            f"int{bits:2d} | "
            f"S={scale:<7} | "
            f"SQNR={sqnr:8.2f} dB | "
            f"Clipping={clipping:8.4f}% | "
            f"Bytes={len(payload)}"
        )


# Save measurements to CSV
csv_path = RESULTS_DIR / "sqnr_results.csv"

with open(csv_path, "w", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(results[0].keys())
    )

    writer.writeheader()
    writer.writerows(results)

print(f"\nResults saved to: {csv_path}")


# Graph 1: SQNR comparison
labels = [
    f"int{bits}\nS={scale}"
    for bits, scale in CONFIGURATIONS
]

word_sqnr = [
    r["sqnr_db"]
    for r in results
    if r["clip_type"] == "Word"
]

silence_sqnr = [
    r["sqnr_db"]
    for r in results
    if r["clip_type"] == "Silence"
]

positions = np.arange(len(labels))
width = 0.35

plt.figure(figsize=(12, 6))

plt.bar(
    positions - width / 2,
    word_sqnr,
    width,
    label="Word clip"
)

plt.bar(
    positions + width / 2,
    silence_sqnr,
    width,
    label="Silence clip"
)

plt.xticks(positions, labels)
plt.ylabel("SQNR (dB)")
plt.title("Team 14 - Quantisation SQNR Comparison")
plt.legend()
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

plt.savefig(
    PLOTS_DIR / "sqnr_comparison.png",
    dpi=200
)


# Graph 2: Clipping comparison
word_clipping = [
    r["clipping_percent"]
    for r in results
    if r["clip_type"] == "Word"
]

silence_clipping = [
    r["clipping_percent"]
    for r in results
    if r["clip_type"] == "Silence"
]

plt.figure(figsize=(12, 6))

plt.bar(
    positions - width / 2,
    word_clipping,
    width,
    label="Word clip"
)

plt.bar(
    positions + width / 2,
    silence_clipping,
    width,
    label="Silence clip"
)

plt.xticks(positions, labels)
plt.ylabel("Clipped samples (%)")
plt.title("Effect of Quantisation Scale on Clipping")
plt.legend()
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

plt.savefig(
    PLOTS_DIR / "clipping_comparison.png",
    dpi=200
)


# Graph 3: Original vs reconstructed waveform
x = get_clip(
    TEAM, 0, fs=FS, antialias=True
)

x8 = unpack(pack(x, 8, 1.0), 8, 1.0)
x16 = unpack(pack(x, 16, 1.0), 16, 1.0)

# Select a short region around the strongest sample
peak = np.argmax(np.abs(x))
start = max(0, peak - 200)
end = min(len(x), peak + 200)

time = np.arange(start, end) / FS * 1000

plt.figure(figsize=(12, 6))

plt.plot(
    time, x[start:end],
    label="Original float32"
)

plt.plot(
    time, x8[start:end],
    "--", label="int8"
)

plt.plot(
    time, x16[start:end],
    ":", label="int16"
)

plt.xlabel("Time (ms)")
plt.ylabel("Amplitude")
plt.title("Original vs Reconstructed Audio")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

plt.savefig(
    PLOTS_DIR / "waveform_comparison.png",
    dpi=200
)


# Graph 4: Quantisation error
plt.figure(figsize=(12, 6))

plt.plot(
    time,
    x[start:end] - x8[start:end],
    label="int8 error"
)

plt.plot(
    time,
    x[start:end] - x16[start:end],
    label="int16 error"
)

plt.xlabel("Time (ms)")
plt.ylabel("Reconstruction error")
plt.title("Int8 vs Int16 Quantisation Error")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

plt.savefig(
    PLOTS_DIR / "quantisation_error.png",
    dpi=200
)


# Identify best tested zero-clipping int8 scale
print("\n--- BEST INT8 SCALE PER CLIP ---")

for clip_type in CLIPS:

    valid = [
        r for r in results
        if r["clip_type"] == clip_type
        and r["bits"] == 8
        and r["clipping_percent"] == 0
    ]

    if valid:

        best = max(valid, key=lambda r: r["sqnr_db"])

        print(
            f"{clip_type}: "
            f"S={best['scale']}, "
            f"SQNR={best['sqnr_db']:.2f} dB"
        )

    else:
        print(f"{clip_type}: No zero-clipping scale found")

print("\nAll SQNR experiments completed.")
print(f"Graphs saved to: {PLOTS_DIR}")

plt.show()