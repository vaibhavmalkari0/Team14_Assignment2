"""Mission 3 reference features, plots, and reproducible board measurements.

Run from the repository root. Requires numpy, matplotlib and the project's
board_link.py dependencies for hardware commands.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
CLASSES = ("on", "off", "stop", "go", "_unknown", "_silence")


def _mel_edges(fs: int, mels: int) -> np.ndarray:
    hz2mel = lambda f: 2595.0 * np.log10(1.0 + f / 700.0)
    mel2hz = lambda m: 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    return np.asarray([mel2hz(v) for v in np.linspace(hz2mel(20.0), hz2mel(fs / 2), mels + 2)])


def mel_filterbank(fs: int, nfft: int, mels: int) -> np.ndarray:
    """HTK triangles sampled at rFFT bin frequencies, matching features.h."""
    hz = np.arange(nfft // 2 + 1, dtype=np.float64) * fs / nfft
    edges = _mel_edges(fs, mels)
    bank = np.zeros((mels, len(hz)), dtype=np.float64)
    for m in range(mels):
        lo, center, hi = edges[m:m + 3]
        left = (hz > lo) & (hz <= center)
        right = (hz > center) & (hz < hi)
        bank[m, left] = (hz[left] - lo) / (center - lo)
        bank[m, right] = (hi - hz[right]) / (hi - center)
    return bank


def features(x, fs=16000, win=480, hop=320, nfft=512, mels=40, mfcc=0):
    """Return whole-frame log-mel or orthonormal DCT-II MFCC features.

    Follows README section 5 exactly: symmetric Hann, zero padding, one-sided
    power divided by nfft, HTK triangular bands, and a -100 dB power floor.
    Returns shape (frames, mels) or (frames, mfcc).
    """
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    if (fs <= 0 or win < 2 or hop < 1 or nfft < win or nfft & (nfft - 1)
            or mels < 1 or mfcc < 0 or mfcc > mels):
        raise ValueError("invalid feature configuration")
    nframes = max(0, 1 + (len(x) - win) // hop)
    if nframes == 0:
        return np.empty((0, mfcc or mels), dtype=np.float32)
    starts = np.arange(nframes)[:, None] * hop
    frames = x[starts + np.arange(win)] * np.hanning(win)[None, :]
    spectrum = np.fft.rfft(frames, n=nfft, axis=1)
    power = (spectrum.real ** 2 + spectrum.imag ** 2) / nfft
    mel = power @ mel_filterbank(fs, nfft, mels).T
    logmel = 10.0 * np.log10(np.maximum(mel, 1e-10))
    if not mfcc:
        return logmel.astype(np.float32)
    q = np.arange(mfcc)[:, None]
    m = np.arange(mels)[None, :]
    scale = np.full((mfcc, 1), math.sqrt(2.0 / mels))
    scale[0, 0] = math.sqrt(1.0 / mels)
    dct = scale * np.cos(np.pi * q * (2 * m + 1) / (2.0 * mels))
    return (logmel @ dct.T).astype(np.float32)


def plot_class_examples(team=14, fs=16000, win=480, hop=320, nfft=512, mels=40):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import team_audio

    OUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(CLASSES), 1, figsize=(11, 12), constrained_layout=True)
    for ax, label in zip(axes, CLASSES):
        clip_id = next(cid for cid, lab in team_audio.clip_list(team) if lab == label)
        x = team_audio.get_clip(team, clip_id, fs=fs, antialias=True)
        z = features(x, fs, win, hop, nfft, mels)
        im = ax.imshow(z.T, origin="lower", aspect="auto", interpolation="nearest",
                       extent=(0, len(x) / fs, 0, mels), cmap="magma")
        ax.set(title=f"{label} (clip {clip_id})", ylabel="Mel band")
        fig.colorbar(im, ax=ax, label="dB", fraction=0.02)
    axes[-1].set_xlabel("Time (s)")
    path = OUT / "logmel_class_examples.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def _packed_baseline(team=14, seconds=10):
    import team_audio
    from srijan.mission2.quantisation import pack

    clips = team_audio.clip_list(team)[:seconds]
    x = np.concatenate([team_audio.get_clip(team, cid, fs=16000, antialias=True)
                        for cid, _ in clips]).astype(np.float32)
    payload = pack(x, 16, S=1.0)
    # Decode the exact bytes sent to the board for a fair numerical comparison.
    qx = np.frombuffer(payload, dtype="<i2").astype(np.float32) / 32767.0
    return x, qx, payload, clips


def run_board(port, baud=921600, seconds=10, speed=1.0, config="baseline", team=14):
    """Capture one real board run and save raw results plus a concise summary."""
    from board_link import Board

    _, qx, payload, clips = _packed_baseline(team, seconds)
    if config == "baseline":
        win, hop, nfft, mels, mfcc = 480, 320, 512, 40, 0
    elif config == "mfcc13":
        win, hop, nfft, mels, mfcc = 400, 160, 512, 40, 13
    else:
        raise ValueError(config)
    b = Board(port, baud=baud, timeout=5)
    try:
        started = time.perf_counter()
        result = b.stream(payload, fs=16000, fmt="i16", scale=1.0, win=win, hop=hop,
                          nfft=nfft, mels=mels, mfcc=mfcc, feat=True, store="none",
                          speed=speed, samples_per_packet=320)
        elapsed = time.perf_counter() - started
    finally:
        b.close()
    ref = features(qx, 16000, win, hop, nfft, mels, mfcc)
    n = min(len(ref), len(result["features"]))
    diff = np.abs(ref[:n] - result["features"][:n]) if n else np.empty((0, mfcc or mels))
    values_per_frame = mfcc or mels
    summary = {
        "port": port, "baud": baud, "config": config, "speed": speed,
        "clip_ids": [int(cid) for cid, _ in clips], "samples": len(qx),
        "audio_seconds": len(qx) / 16000, "elapsed_seconds": elapsed,
        "features_expected": int(result["expected_features"]),
        "features_received": len(result["features"]),
        "features_lost": int(result["lost_features"]),
        "bad_crc_back": int(result["bad_crc_back"]),
        "board_summary": result["board"],
        "compute_us_mean": float(np.mean(result["compute_us"])) if len(result["compute_us"]) else None,
        "compute_us_max": int(np.max(result["compute_us"])) if len(result["compute_us"]) else None,
        "lag_s_mean": float(np.mean(result["lag_s"])) if len(result["lag_s"]) else None,
        "lag_s_max": float(np.max(result["lag_s"])) if len(result["lag_s"]) else None,
        "feature_value_bytes_per_second": values_per_frame * 4 * 16000 / hop,
        "wire_bytes_per_second_estimate": (values_per_frame * 4 + 21) * 16000 / hop,
        "numpy_board_abs_diff_mean_db": float(np.mean(diff)) if n else None,
        "numpy_board_abs_diff_max_db": float(np.max(diff)) if n else None,
        "parity_pass_0_05_db": bool(n == len(ref) and n > 0 and np.max(diff) <= 0.05),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"capture_{config}_{port.replace('/', '_')}"
    np.savez_compressed(OUT / f"{stem}.npz", features=result["features"],
                        frame_numbers=result["frame_numbers"], first_sample=result["first_sample"],
                        compute_us=result["compute_us"], lag_s=result["lag_s"], numpy_reference=ref)
    (OUT / f"{stem}.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plot"); p.add_argument("--team", type=int, default=14)
    p = sub.add_parser("board")
    p.add_argument("--port", required=True); p.add_argument("--baud", type=int, default=921600)
    p.add_argument("--seconds", type=int, default=10); p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--config", choices=("baseline", "mfcc13"), default="baseline")
    p.add_argument("--team", type=int, default=14)
    a = ap.parse_args()
    if a.command == "plot":
        print(plot_class_examples(a.team))
    else:
        print(json.dumps(run_board(a.port, a.baud, a.seconds, a.speed, a.config, a.team), indent=2))


if __name__ == "__main__":
    main()
