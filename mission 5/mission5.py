"""Mission 5 laptop/board domain comparison and clip-level classifier.

Commands are run from the repository root. See README.md in this folder.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import team_audio
from srijan.mission2.quantisation import pack, unpack
from sumadhwa.mission3 import features as numpy_features

TEAM = 14
CLIPS = team_audio.clip_list(TEAM)
CLASS_NAMES = tuple(team_audio.CLASSES)
WIN_HOP = {
    "baseline_i16": (480, 320),
    "int8_s1": (480, 320),
    "int8_s05": (480, 320),
    "8k_unfiltered_i16": (240, 160),
}
SETTINGS = {
    "baseline_i16": {"fs": 16000, "fmt": "i16", "scale": 1.0,
                      "reference_antialias": True, "board_antialias": True},
    "int8_s1": {"fs": 16000, "fmt": "i8", "scale": 1.0,
                "reference_antialias": True, "board_antialias": True},
    # S=0.5 is the smaller scale quantified in the Mission 2 full-dataset report.
    "int8_s05": {"fs": 16000, "fmt": "i8", "scale": 0.5,
                 "reference_antialias": True, "board_antialias": True},
    "8k_unfiltered_i16": {"fs": 8000, "fmt": "i16", "scale": 1.0,
                           "reference_antialias": True, "board_antialias": False},
}
NFFT = 512
MELS = 40
DATA_DIR = HERE / "artifacts"
REFS_PATH = DATA_DIR / "laptop_references.npz"


def _classes():
    return np.asarray([label for _, label in CLIPS], dtype="U16")


def _clip_features(config_name: str, clip_id: int, antialias: bool, quantized: bool):
    cfg = SETTINGS[config_name]
    fs = cfg["fs"]
    win, hop = WIN_HOP[config_name]
    signal = team_audio.get_clip(TEAM, clip_id, fs=fs, antialias=antialias).astype(np.float32)
    pack_bits = 16 if cfg["fmt"] == "i16" else 8
    payload = pack(signal, pack_bits, S=cfg["scale"])
    reconstructed = unpack(payload, pack_bits, S=cfg["scale"])
    x = reconstructed if quantized else signal
    return numpy_features(x, fs=fs, win=win, hop=hop, nfft=NFFT, mels=MELS)


def prepare_references():
    """Create float32 and same-wire-quantized NumPy references for every clip."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_data = {"clip_id": np.asarray([cid for cid, _ in CLIPS], dtype=np.int32),
                "label": _classes()}
    metadata = {}
    laptop_classifier_results = {}
    for name, cfg in SETTINGS.items():
        original_rows, wire_rows = [], []
        n_clipped_samples = 0
        n_clipped_clips = 0
        for clip_id, _ in CLIPS:
            # Domain reference: original float32 laptop clip, using the requested reference filter.
            original_rows.append(_clip_features(name, clip_id, cfg["reference_antialias"], False))
            # Board math reference: decode exactly the quantized bytes that will be transmitted.
            wire_rows.append(_clip_features(name, clip_id, cfg["board_antialias"], True))
            signal = team_audio.get_clip(TEAM, clip_id, fs=cfg["fs"],
                                         antialias=cfg["board_antialias"])
            maxq = 32767 if cfg["fmt"] == "i16" else 127
            qmin = -32768 if cfg["fmt"] == "i16" else -128
            raw = np.rint(np.asarray(signal, dtype=np.float64) / cfg["scale"] * maxq)
            clipped_here = int(np.count_nonzero((raw < qmin) | (raw > maxq)))
            n_clipped_samples += clipped_here
            n_clipped_clips += int(clipped_here > 0)
        original = np.stack(original_rows).astype(np.float32)
        wire_ref = np.stack(wire_rows).astype(np.float32)
        all_data[f"{name}__laptop_original"] = original
        all_data[f"{name}__numpy_wire"] = wire_ref
        laptop_classifier_results[name] = nearest_centroid(
            original, original, _classes(), seed=2026)["laptop_test"]
        metadata[name] = {
            **cfg, "win": WIN_HOP[name][0], "hop": WIN_HOP[name][1],
            "nfft": NFFT, "mels": MELS, "frames_per_clip": int(original.shape[1]),
            "clipped_input_samples": n_clipped_samples,
            "clips_with_clipping": n_clipped_clips,
        }
    all_data["metadata_json"] = np.asarray(json.dumps(metadata, sort_keys=True))
    np.savez_compressed(REFS_PATH, **all_data)
    (DATA_DIR / "settings.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (DATA_DIR / "laptop_classifier_results.json").write_text(
        json.dumps(laptop_classifier_results, indent=2) + "\n")
    return metadata


def capture_board(config_name: str, port: str, baud: int = 921600):
    """Stream all 144 clips for one setting; preserve raw capture and counters."""
    from board_link import Board

    if config_name not in SETTINGS:
        raise ValueError(f"unknown setting: {config_name}")
    cfg = SETTINGS[config_name]
    fs, fmt, scale = cfg["fs"], cfg["fmt"], cfg["scale"]
    win, hop = WIN_HOP[config_name]
    signals = [team_audio.get_clip(TEAM, cid, fs=fs, antialias=cfg["board_antialias"])
               for cid, _ in CLIPS]
    full_signal = np.concatenate(signals).astype(np.float32)
    bits = 16 if fmt == "i16" else 8
    payload = pack(full_signal, bits, S=scale)
    board = Board(port, baud=baud, timeout=5)
    try:
        start = time.perf_counter()
        result = board.stream(payload, fs=fs, fmt=fmt, scale=scale,
                              win=win, hop=hop, nfft=NFFT, mels=MELS, mfcc=0,
                              feat=True, store="none", speed=1.0,
                              samples_per_packet=320)
        elapsed = time.perf_counter() - start
    finally:
        board.close()

    samples_per_clip = fs
    total_samples = len(full_signal)
    expected_packets = total_samples // 320
    expected_features = 1 + (total_samples - win) // hop
    summary = result.get("board") or {}
    complete = bool(
        summary
        and result["packets_sent"] == expected_packets
        and summary.get("frames_ok") == expected_packets + 1
        and summary.get("samples") == total_samples
        and summary.get("seq_gaps") == 0 and summary.get("bad_crc") == 0
        and summary.get("bad_len") == 0 and summary.get("dup") == 0
        and result["bad_crc_back"] == 0
        and result["expected_features"] == expected_features
        and len(result["features"]) == expected_features
        and summary.get("features") == expected_features
    )
    if complete:
        features_per_clip = [[] for _ in CLIPS]
        frames_dropped_at_clip_edges = 0
        for row, start_sample in enumerate(result["first_sample"]):
            clip_id = int(start_sample // samples_per_clip)
            local_start = int(start_sample % samples_per_clip)
            if clip_id >= len(CLIPS) or local_start + win > samples_per_clip:
                frames_dropped_at_clip_edges += 1
                continue
            features_per_clip[clip_id].append(result["features"][row])
        expected_per_clip = 1 + (samples_per_clip - win) // hop
        if any(len(rows) != expected_per_clip for rows in features_per_clip):
            complete = False
        if complete:
            by_clip = np.stack([np.stack(rows) for rows in features_per_clip]).astype(np.float32)
    else:
        frames_dropped_at_clip_edges = 0
        by_clip = np.empty((0, 0, MELS), dtype=np.float32)

    record = {
        "config": config_name, "port": port, "baud": baud,
        "settings": {**cfg, "win": win, "hop": hop, "nfft": NFFT, "mels": MELS,
                     "speed": 1.0, "samples_per_packet": 320},
        "elapsed_seconds": elapsed, "complete_zero_loss": complete,
        "packets_sent": int(result["packets_sent"]),
        "packets_expected": expected_packets,
        "board": summary,
        "expected_features": int(result["expected_features"]),
        "features_received": len(result["features"]),
        "features_lost": int(result["lost_features"]),
        "bad_crc_back": int(result["bad_crc_back"]),
        "frames_dropped_at_clip_edges": frames_dropped_at_clip_edges,
        "features_per_clip": int(by_clip.shape[1]) if complete else None,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    safe_port = port.replace('/', '_').replace('\\', '_')
    stem = f"{config_name}_{safe_port}"
    np.savez_compressed(DATA_DIR / f"board_{stem}.npz",
                        features_by_clip=by_clip,
                        raw_features=result["features"],
                        frame_numbers=result["frame_numbers"],
                        first_sample=result["first_sample"],
                        compute_us=result["compute_us"], lag_s=result["lag_s"],
                        clip_id=np.asarray([cid for cid, _ in CLIPS], dtype=np.int32),
                        label=_classes())
    (DATA_DIR / f"board_{stem}.json").write_text(json.dumps(record, indent=2) + "\n")
    if not complete:
        raise RuntimeError(f"capture {config_name} incomplete; raw evidence saved to {DATA_DIR}")
    return record


def _per_clip_vectors(features_by_clip):
    means = np.mean(features_by_clip, axis=1)
    stds = np.std(features_by_clip, axis=1)
    return np.concatenate([means, stds], axis=1)


def _stratified_split(labels, seed=2026):
    rng = np.random.default_rng(seed)
    train, test = [], []
    for lab in CLASS_NAMES:
        ids = np.flatnonzero(labels == lab)
        if len(ids) != 24:
            raise ValueError(f"expected 24 clips for {lab}; found {len(ids)}")
        ids = rng.permutation(ids)
        train.extend(ids[:16]); test.extend(ids[16:])
    return np.asarray(sorted(train)), np.asarray(sorted(test))


def nearest_centroid(laptop_features, board_features, labels, seed=2026):
    """Train on 96 laptop clip vectors; evaluate laptop and board on same 48 clips."""
    if laptop_features.shape != board_features.shape:
        raise ValueError("laptop and board clip-feature arrays must have matching shapes")
    if laptop_features.shape[0] != len(labels):
        raise ValueError("one feature row is required per clip")
    laptop_vec = _per_clip_vectors(laptop_features)
    board_vec = _per_clip_vectors(board_features)
    train, test = _stratified_split(labels, seed)
    mean = laptop_vec[train].mean(axis=0)
    spread = laptop_vec[train].std(axis=0)
    spread[spread == 0] = 1.0
    train_z = (laptop_vec[train] - mean) / spread
    laptop_test_z = (laptop_vec[test] - mean) / spread
    board_test_z = (board_vec[test] - mean) / spread
    train_labels = labels[train]
    centroids = np.stack([train_z[train_labels == lab].mean(axis=0) for lab in CLASS_NAMES])

    def score(x):
        predicted = np.asarray(CLASS_NAMES)[np.argmin(
            np.sum((x[:, None, :] - centroids[None, :, :]) ** 2, axis=2), axis=1)]
        truth = labels[test]
        confusion = np.zeros((len(CLASS_NAMES), len(CLASS_NAMES)), dtype=np.int32)
        for actual, guess in zip(truth, predicted):
            confusion[CLASS_NAMES.index(actual), CLASS_NAMES.index(guess)] += 1
        per_class = {lab: float(np.mean(predicted[truth == lab] == lab)) for lab in CLASS_NAMES}
        return {"accuracy": float(np.mean(predicted == truth)),
                "per_class_accuracy": per_class,
                "confusion_matrix": confusion.tolist(),
                "predicted": predicted.tolist(), "truth": truth.tolist()}

    return {
        "train_clip_count": int(len(train)), "test_clip_count": int(len(test)),
        "train_clips_by_class": {lab: int(np.count_nonzero(labels[train] == lab)) for lab in CLASS_NAMES},
        "test_clips_by_class": {lab: int(np.count_nonzero(labels[test] == lab)) for lab in CLASS_NAMES},
        "laptop_test": score(laptop_test_z), "board_test": score(board_test_z),
    }


def _difference_rows(config_name, comparison, board, reference, labels):
    diff = np.abs(board - reference)
    if diff.shape != board.shape or diff.ndim != 3:
        raise ValueError(f"unexpected feature array shape for {config_name}/{comparison}: {diff.shape}")
    rows, heat = [], []
    for lab in CLASS_NAMES:
        selected = diff[labels == lab]
        mean_band = selected.mean(axis=(0, 1))
        worst_band = selected.max(axis=(0, 1))
        heat.append(mean_band)
        for band in range(diff.shape[-1]):
            rows.append({"setting": config_name, "comparison": comparison,
                         "class": lab, "band": band,
                         "mean_abs_difference_db": float(mean_band[band]),
                         "worst_abs_difference_db": float(worst_band[band])})
    overall = {"setting": config_name, "comparison": comparison,
               "mean_abs_difference_db": float(diff.mean()),
               "worst_abs_difference_db": float(diff.max())}
    return rows, overall, np.asarray(heat)


def analyze():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not REFS_PATH.exists():
        raise FileNotFoundError(f"run prepare first: {REFS_PATH}")
    refs = np.load(REFS_PATH, allow_pickle=False)
    labels = refs["label"]
    clip_ids = refs["clip_id"]
    all_rows, overall_rows, classifier_results = [], [], {}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    plots = DATA_DIR / "plots"
    plots.mkdir(exist_ok=True)

    for name in SETTINGS:
        capture_paths = sorted(DATA_DIR.glob(f"board_{name}_*.npz"))
        if len(capture_paths) != 1:
            raise FileNotFoundError(f"expected exactly one board capture for {name}, found {len(capture_paths)}")
        capture_path = capture_paths[0]
        meta_path = capture_path.with_suffix(".json")
        meta = json.loads(meta_path.read_text())
        if not meta.get("complete_zero_loss"):
            raise ValueError(f"capture is not complete and loss-free: {capture_path}")
        capture = np.load(capture_path, allow_pickle=False)
        board = capture["features_by_clip"]
        if board.shape != refs[f"{name}__laptop_original"].shape:
            raise ValueError(f"clip/frame/band shape mismatch for {name}: {board.shape}")
        if not np.array_equal(capture["clip_id"], clip_ids) or not np.array_equal(capture["label"], labels):
            raise ValueError(f"clip order or labels do not match source for {name}")

        comparisons = [
            ("original_laptop", refs[f"{name}__laptop_original"]),
            ("same_quantized_numpy", refs[f"{name}__numpy_wire"]),
        ]
        for comp, reference in comparisons:
            rows, overall, heat = _difference_rows(name, comp, board, reference, labels)
            all_rows.extend(rows); overall_rows.append(overall)
            fig, ax = plt.subplots(figsize=(12, 4.5), constrained_layout=True)
            vmax = max(float(np.max(heat)), 1e-6)
            im = ax.imshow(heat, origin="lower", aspect="auto", cmap="magma", vmin=0, vmax=vmax)
            ax.set_yticks(range(len(CLASS_NAMES)), CLASS_NAMES)
            ax.set_xlabel("Feature band"); ax.set_title(f"{name}: |board − {comp}| mean dB")
            fig.colorbar(im, ax=ax, label="Mean absolute difference (dB)")
            fig.savefig(plots / f"{name}_{comp}_heatmap.png", dpi=160)
            plt.close(fig)

        # The classifier is trained on the setting's laptop reference (original float32,
        # filtered where specified) and evaluated on the held-out clips with both domains.
        classifier_results[name] = nearest_centroid(
            refs[f"{name}__laptop_original"], board, labels, seed=2026)

    with (DATA_DIR / "feature_differences_per_band_class.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        writer.writeheader(); writer.writerows(all_rows)
    (DATA_DIR / "feature_difference_summary.json").write_text(json.dumps(overall_rows, indent=2) + "\n")
    (DATA_DIR / "nearest_centroid_results.json").write_text(json.dumps(classifier_results, indent=2) + "\n")
    return {"comparisons": overall_rows, "classifier": classifier_results,
            "per_band_csv": str(DATA_DIR / "feature_differences_per_band_class.csv"),
            "plots": str(plots)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="generate laptop original and quantized feature references")
    p = sub.add_parser("capture", help="capture one complete board setting")
    p.add_argument("--config", choices=tuple(SETTINGS), required=True)
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=921600)
    sub.add_parser("analyze", help="make difference metrics/heatmaps and classifier results")
    a = ap.parse_args()
    if a.command == "prepare":
        print(json.dumps(prepare_references(), indent=2))
    elif a.command == "capture":
        print(json.dumps(capture_board(a.config, a.port, a.baud), indent=2))
    else:
        print(json.dumps(analyze(), indent=2))


if __name__ == "__main__":
    main()
