# Plot frequencies against magnitude
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

# Add project root to the import path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from team_audio import get_clip

TEAM = 14
CLIP_ID = 120
FS = 48000

# Load original silence clip
x = get_clip(TEAM, CLIP_ID, fs=FS, antialias=False)

# Calculate FFT magnitude
magnitude = np.abs(np.fft.rfft(x))

# Calculate corresponding frequencies
frequencies = np.fft.rfftfreq(len(x), d=1 / FS)
peak_index = np.argmax(magnitude[1:]) + 1

peak_frequency = frequencies[peak_index]
peak_magnitude = magnitude[peak_index]

print(f"Dominant frequency: {peak_frequency:.2f} Hz")
print(f"Peak magnitude: {peak_magnitude:.4f}")
print(f"Nyquist frequency: {FS / 2:.2f} Hz")
plt.figure(figsize=(10, 5))
plt.plot(frequencies, magnitude)

# Label both axes
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")

# Add a title and grid
plt.title(f"FFT Magnitude Spectrum of Silence Clip (Team {TEAM}, Clip {CLIP_ID})")
plt.grid(True)

# Optional: show full FFT range clearly
plt.xlim(0, 24000)

# Save the plot
plt.tight_layout()
plt.savefig("srijan/mission2/plots/spectrum_48000.png", dpi=150)

# Display the plot
# Experiment 2: Downsampling without anti-aliasing
FS_LOW = 8000

x_low = get_clip(
    TEAM, CLIP_ID, fs=FS_LOW, antialias=False
)

# Calculate FFT
magnitude_low = np.abs(np.fft.rfft(x_low))
frequencies_low = np.fft.rfftfreq(
    len(x_low), d=1 / FS_LOW
)

# Find the dominant frequency
peak_index_low = np.argmax(magnitude_low[1:]) + 1

print("\n--- 8 kHz Without Anti-aliasing ---")
print("Total samples:", len(x_low))
print("Nyquist frequency:", FS_LOW / 2)
print("Dominant frequency:", frequencies_low[peak_index_low])
print("Peak magnitude:", magnitude_low[peak_index_low])
# Plot the 8 kHz spectrum
plt.figure(figsize=(10, 5))
plt.plot(frequencies_low, magnitude_low)

plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.title("8 kHz Spectrum Without Anti-aliasing")
plt.grid(True)
plt.xlim(0, 4000)

# Save the plot
plt.tight_layout()
plt.savefig(
    "srijan/mission2/plots/spectrum_8000_no_filter.png",
    dpi=150
)
# Experiment 3: Downsampling with anti-aliasing

x_filtered = get_clip(
    TEAM, CLIP_ID, fs=FS_LOW, antialias=True
)

# Calculate FFT
magnitude_filtered = np.abs(np.fft.rfft(x_filtered))

frequencies_filtered = np.fft.rfftfreq(
    len(x_filtered), d=1 / FS_LOW
)

# Find dominant frequency
peak_index_filtered = np.argmax(magnitude_filtered[1:]) + 1

print("\n--- 8 kHz With Anti-aliasing ---")
print("Total samples:", len(x_filtered))
print("Dominant frequency:", frequencies_filtered[peak_index_filtered])
print("Peak magnitude:", magnitude_filtered[peak_index_filtered])
# Plot the 8 kHz filtered spectrum
plt.figure(figsize=(10, 5))
plt.plot(frequencies_filtered, magnitude_filtered)

plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.title("8 kHz Spectrum With Anti-aliasing")
plt.grid(True)
plt.xlim(0, 4000)

# Save the filtered spectrum
plt.tight_layout()
plt.savefig(
    "srijan/mission2/plots/spectrum_8000_filtered.png",
    dpi=150
)
# Experiment 4: Measure anti-aliasing filter attenuation

alias_frequency = abs(FS_LOW - peak_frequency)

# Find the FFT bin corresponding to the alias frequency
alias_index = np.argmin(
    np.abs(frequencies_low - alias_frequency)
)

# Magnitude at the alias frequency before filtering
before = magnitude_low[alias_index]

# Magnitude at the same frequency after filtering
after = magnitude_filtered[alias_index]

# Calculate attenuation in decibels
attenuation_db = 20 * np.log10(
    before / max(after, 1e-12)
)

print("\n--- Anti-aliasing Filter Performance ---")
print(f"Alias frequency: {alias_frequency:.2f} Hz")
print(f"Magnitude before filtering: {before:.6f}")
print(f"Magnitude after filtering: {after:.6f}")
print(f"Filter attenuation: {attenuation_db:.2f} dB")
for signal, fs, name in [
    (x, FS, "48000"),
    (x_low, FS_LOW, "8000_no_filter"),
    (x_filtered, FS_LOW, "8000_filtered")
]:
    amplitude = 2 * np.abs(np.fft.rfft(signal)) / len(signal)
    amplitude[0] /= 2
    amplitude[-1] /= 2

    db = 20 * np.log10(np.maximum(amplitude, 1e-12))
    freq = np.fft.rfftfreq(len(signal), 1 / fs)

    plt.figure(figsize=(10, 5))
    plt.plot(freq, db)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude (dBFS)")
    plt.title(f"Team 14 - Spectrum {name}")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(
        f"srijan/mission2/plots/spectrum_{name}_db.png",
        dpi=200
    )
plt.show()