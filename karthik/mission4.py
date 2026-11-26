"""Mission 4 loss accounting and labelled-feature dataset tools.

Run from the repository root. Hardware commands require the ESP32-S3 and the
board_link.py serial dependencies. No hardware result is implied by this code.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import team_audio
from srijan.mission2.quantisation import pack

OUT = Path(__file__).resolve().parent
TEAM = 14
FS = 16_000
SAMPLES_PER_PACKET = 320
WIN = 480
HOP = 320
NFFT = 512
MELS = 40
SCALE = 1.0
SKIP_CASE = (10, 11, 200)
CLIPS = team_audio.clip_list(TEAM)
LABELS = tuple(team_audio.CLASSES)


def expected_counts():
    total_samples = len(CLIPS) * FS
    total_bytes = total_samples * 2
    data_packets = math.ceil(total_samples / SAMPLES_PER_PACKET)
    feature_frames = 0 if total_samples < WIN else 1 + (total_samples - WIN) // HOP
    straddling_clip_frames = len(CLIPS) - 1  # 1-second boundaries align to hop; one frame crosses each.
    return {
        "team": TEAM, "clip_count": len(CLIPS), "classes": list(LABELS),
        "samples_per_clip": FS, "total_samples": total_samples,
        "raw_int16_bytes": total_bytes, "data_packets": data_packets,
        "frames_ok_including_end": data_packets + 1,
        "full_stream_feature_frames": feature_frames,
        "frames_straddling_clip_boundaries": straddling_clip_frames,
        "labelled_frames_after_straddle_drop": feature_frames - straddling_clip_frames,
        "expected_labelled_frames_per_class": (feature_frames - straddling_clip_frames) // len(LABELS),
        "skip_packets": list(SKIP_CASE),
        "skip_total_missing_samples": len(SKIP_CASE) * SAMPLES_PER_PACKET,
        "skip_expected_host_data_packets": data_packets - len(SKIP_CASE),
        "skip_expected_board_frames_including_end": data_packets - len(SKIP_CASE) + 1,
        "skip_received_samples": total_samples - len(SKIP_CASE) * SAMPLES_PER_PACKET,
        "baseline_stream_seconds": total_samples / FS,
        "stream_settings": {
            "fs": FS, "fmt": "i16", "scale": SCALE, "antialias": True,
            "win": WIN, "hop": HOP, "nfft": NFFT, "mels": MELS, "mfcc": 0,
            "feat": True, "store": "none", "speed": 1.0,
            "samples_per_packet": SAMPLES_PER_PACKET,
        },
    }


def build_payload():
    clips = []
    for clip_id, label in CLIPS:
        x = team_audio.get_clip(TEAM, clip_id, fs=FS, antialias=True)
        if len(x) != FS:
            raise ValueError(f"clip {clip_id} has {len(x)} samples; expected {FS}")
        clips.append(np.asarray(x, dtype=np.float32))
    x = np.concatenate(clips)
    return x, pack(x, 16, S=SCALE)


def _input_gap_map(n_samples: int, samples_per_packet: int, skipped_packets):
    """Map known omitted packet runs to seams in the board's compact timeline."""
    n_packets = math.ceil(n_samples / samples_per_packet)
    skip = sorted(set(int(s) for s in skipped_packets))
    if any(s < 0 or s >= n_packets for s in skip):
        raise ValueError("skip packet index is outside the transmitted stream")
    packet_lengths = [min(samples_per_packet, n_samples - i * samples_per_packet)
                      for i in range(n_packets)]
    gaps = []
    skipped_before = 0
    for seq in skip:
        original_start = seq * samples_per_packet
        compact_seam = original_start - skipped_before
        gaps.append({"seq": seq, "original_start": original_start,
                     "samples": packet_lengths[seq], "compact_seam": compact_seam})
        skipped_before += packet_lengths[seq]
    # Adjacent omitted packets form one discontinuity seam on the compact stream.
    seams = sorted(set(g["compact_seam"] for g in gaps))
    return gaps, seams


def label_frames(features, board_first_sample, frame_numbers, *, n_samples,
                 skipped_packets=(), fs=FS, win=WIN, samples_per_packet=SAMPLES_PER_PACKET):
    """Label frames without allowing omitted packets to shift later clip labels.

    `board_first_sample` is the counter reported by firmware; after a missing
    packet it counts only received samples. Known skipped packet lengths are
    restored to produce timeline-correct `first_sample`. Frames that cross a
    packet-loss seam or a clip boundary are dropped as ambiguous. If a loss
    position is unknown, callers must reject labeling rather than guessing.
    """
    feats = np.asarray(features)
    raw_first = np.asarray(board_first_sample, dtype=np.int64)
    nums = np.asarray(frame_numbers, dtype=np.int64)
    if feats.ndim != 2 or len(feats) != len(raw_first) or len(feats) != len(nums):
        raise ValueError("features, first_sample and frame_numbers must have matching rows")
    gaps, seams = _input_gap_map(n_samples, samples_per_packet, skipped_packets)
    sample_offsets = []
    for t in raw_first:
        sample_offsets.append(sum(g["samples"] for g in gaps if g["compact_seam"] <= t))
    corrected = raw_first + np.asarray(sample_offsets, dtype=np.int64)
    clip_ids, labels = [], []
    keep = np.ones(len(feats), dtype=bool)
    reason_gap = np.zeros(len(feats), dtype=bool)
    reason_clip = np.zeros(len(feats), dtype=bool)
    for i, start in enumerate(raw_first):
        # Any output frame mixing samples from opposite sides of a lost-packet seam is invalid.
        if any(start < seam < start + win for seam in seams):
            keep[i] = False
            reason_gap[i] = True
            continue
        absolute_start = int(corrected[i])
        absolute_end = absolute_start + win
        cid = absolute_start // fs
        if absolute_start < 0 or cid >= len(CLIPS) or absolute_end > (cid + 1) * fs:
            keep[i] = False
            reason_clip[i] = True
            continue
        expected_id, lab = CLIPS[cid]
        if expected_id != cid:
            raise ValueError("clip IDs must be contiguous and ordered by sample timeline")
        clip_ids.append((i, cid, lab))
    kept_indices = np.flatnonzero(keep)
    # Build labels from kept frame positions; the earlier pass left one record per kept row.
    kept_records = {i: (cid, lab) for i, cid, lab in clip_ids}
    out_ids = np.asarray([kept_records[i][0] for i in kept_indices], dtype=np.int32)
    out_labels = np.asarray([kept_records[i][1] for i in kept_indices], dtype="U16")
    return {
        "features": feats[kept_indices].astype(np.float32, copy=False),
        "label": out_labels,
        "clip_id": out_ids,
        "first_sample": corrected[kept_indices].astype(np.int64),
        "board_first_sample": raw_first[kept_indices].astype(np.int64),
        "frame_number": nums[kept_indices].astype(np.int64),
        "kept_source_index": kept_indices,
        "dropped_gap_frames": int(reason_gap.sum()),
        "dropped_clip_straddles": int(reason_clip.sum()),
        "known_packet_gaps": gaps,
    }


def _board_summary(result, n_samples, skipped_packets, speed, feat):
    board = result.get("board") or {}
    data_packets = math.ceil(n_samples / SAMPLES_PER_PACKET)
    expected_frames = 0 if n_samples < WIN else 1 + (n_samples - WIN) // HOP
    observed_input_gaps = int(board.get("seq_gaps", 0))
    known_gap_count = len(set(skipped_packets))
    summary = {
        "speed": speed, "features_enabled": feat,
        "samples_expected": n_samples,
        "packets_expected": data_packets,
        "packets_sent": int(result.get("packets_sent", 0)),
        "bytes_sent": int(result.get("bytes_sent", 0)),
        "send_seconds": float(result.get("send_seconds", 0)),
        "board_summary": board,
        "frames_ok_including_end": board.get("frames_ok"),
        "seq_gaps": observed_input_gaps,
        "expected_seq_gaps_from_deliberate_skip": known_gap_count,
        "bad_crc_in": board.get("bad_crc"), "bad_len_in": board.get("bad_len"),
        "duplicates_in": board.get("dup"), "uart_errors": board.get("uart_errors"),
        "samples_received": board.get("samples"), "stored_bytes": board.get("stored"),
        "expected_features_by_original_timeline": expected_frames if feat else 0,
        "expected_features_reported_by_host": int(result.get("expected_features", 0)),
        "features_received": len(result.get("features", [])),
        "features_lost_by_host": int(result.get("lost_features", 0)),
        "bad_crc_back": int(result.get("bad_crc_back", 0)),
        "board_features": board.get("features"),
        "summary_present": bool(board),
    }
    expected_sent = data_packets - known_gap_count
    summary["host_packet_count_matches"] = summary["packets_sent"] == expected_sent
    summary["board_gap_count_matches"] = observed_input_gaps == known_gap_count
    summary["sample_count_matches_known_skip"] = (
        board.get("samples") == n_samples - sum(
            min(SAMPLES_PER_PACKET, n_samples - s * SAMPLES_PER_PACKET)
            for s in set(skipped_packets))
    )
    return summary


def run_stream(port, baud=921600, speed=1.0, skipped_packets=(), feat=True,
               save_dataset=False):
    from board_link import Board

    x, payload = build_payload()
    board = Board(port, baud=baud, timeout=5)
    try:
        started = time.perf_counter()
        result = board.stream(payload, fs=FS, fmt="i16", scale=SCALE,
                              win=WIN, hop=HOP, nfft=NFFT, mels=MELS, mfcc=0,
                              feat=feat, store="none", max_bytes=0, speed=speed,
                              samples_per_packet=SAMPLES_PER_PACKET,
                              skip=tuple(skipped_packets))
        elapsed = time.perf_counter() - started
    finally:
        board.close()

    summary = _board_summary(result, len(x), skipped_packets, speed, feat)
    summary["elapsed_seconds"] = elapsed
    summary["port"] = port
    summary["baud"] = baud
    summary["stream_settings"] = expected_counts()["stream_settings"]
    summary["stream_settings"]["speed"] = speed
    summary["deliberately_skipped_packets"] = list(skipped_packets)

    features = result["features"]
    if feat:
        labelled = label_frames(features, result["first_sample"], result["frame_numbers"],
                               n_samples=len(x), skipped_packets=skipped_packets)
        summary["labelled_rows"] = len(labelled["features"])
        summary["dropped_gap_straddles"] = labelled["dropped_gap_frames"]
        summary["dropped_clip_straddles"] = labelled["dropped_clip_straddles"]
        summary["dataset_feature_width"] = int(labelled["features"].shape[1])
        summary["nonfinite_feature_values"] = int(np.size(labelled["features"]) -
                                                  np.count_nonzero(np.isfinite(labelled["features"])))
        summary["invalid_clip_ids"] = int(np.count_nonzero(
            (labelled["clip_id"] < 0) | (labelled["clip_id"] >= len(CLIPS))))
        summary["frames_per_class"] = {
            lab: int(np.count_nonzero(labelled["label"] == lab)) for lab in LABELS
        }
        summary["dataset_integrity_pass"] = (
            summary["dataset_feature_width"] == MELS
            and summary["nonfinite_feature_values"] == 0
            and summary["invalid_clip_ids"] == 0
            and set(np.unique(labelled["label"])).issubset(set(LABELS))
        )
        summary["loss_free_dataset_eligible"] = (
            not skipped_packets and summary["summary_present"]
            and summary["seq_gaps"] == 0 and summary["bad_crc_in"] == 0
            and summary["bad_len_in"] == 0 and summary["duplicates_in"] == 0
            and summary["bad_crc_back"] == 0
            and summary["samples_received"] == len(x)
            and summary["packets_sent"] == summary["packets_expected"]
            and summary["frames_ok_including_end"] == summary["packets_expected"] + 1
            and summary["features_received"] == summary["expected_features_by_original_timeline"]
            and summary["board_features"] == summary["features_received"]
            and summary["host_packet_count_matches"]
            and summary["board_gap_count_matches"]
            and summary["dataset_integrity_pass"]
            and len(labelled["features"]) == expected_counts()["labelled_frames_after_straddle_drop"]
        )
    else:
        labelled = None
        summary["loss_free_dataset_eligible"] = False

    OUT.mkdir(parents=True, exist_ok=True)
    mode = "skip" if skipped_packets else ("feat" if feat else "nofeat")
    stem = f"mission4_{mode}_{port.replace('/', '_')}_speed{str(speed).replace('.', 'p')}"
    (OUT / f"{stem}.json").write_text(json.dumps(summary, indent=2) + "\n")
    if feat:
        np.savez_compressed(
            OUT / f"{stem}_capture.npz",
            features=features,
            frame_numbers=result["frame_numbers"],
            board_first_sample=result["first_sample"],
            compute_us=result["compute_us"], lag_s=result["lag_s"],
        )
    if save_dataset:
        if not summary["loss_free_dataset_eligible"]:
            raise RuntimeError("refusing to export dataset: run is incomplete or has unaccounted loss")
        np.savez_compressed(
            OUT / "team14_mission4_dataset.npz",
            features=labelled["features"], label=labelled["label"],
            clip_id=labelled["clip_id"], first_sample=labelled["first_sample"],
            board_first_sample=labelled["board_first_sample"],
            frame_number=labelled["frame_number"],
        )
    return summary


def _zero_loss(run, feat):
    return bool(
        run["summary_present"] and run["seq_gaps"] == 0
        and run["bad_crc_in"] == 0 and run["bad_crc_back"] == 0
        and run["bad_len_in"] == 0 and run["duplicates_in"] == 0
        and run["features_lost_by_host"] == 0
        and run["samples_received"] == run["samples_expected"]
        and run["packets_sent"] == run["packets_expected"]
        and run["frames_ok_including_end"] == run["packets_expected"] + 1
        and run["host_packet_count_matches"] and run["board_gap_count_matches"]
        and (not feat or run["board_features"] == run["features_received"])
    )


def speed_sweep(port, baud=921600, speeds=(1.0, 1.25, 1.5, 2.0, 3.0, 4.0), feat=True,
                refinements=4):
    """Measure full data at coarse speeds, then refine the last pass/fail interval."""
    runs = []
    last_pass = None
    first_fail = None
    for speed in speeds:
        run = run_stream(port, baud=baud, speed=float(speed), feat=feat)
        runs.append(run)
        if _zero_loss(run, feat):
            last_pass = float(speed)
        else:
            first_fail = float(speed)
            break
    if last_pass is not None and first_fail is not None:
        for _ in range(max(0, refinements)):
            speed = (last_pass + first_fail) / 2
            run = run_stream(port, baud=baud, speed=speed, feat=feat)
            runs.append(run)
            if _zero_loss(run, feat):
                last_pass = speed
            else:
                first_fail = speed
    for run in runs:
        run["zero_loss"] = _zero_loss(run, feat)
    sweep_summary = {
        "port": port, "baud": baud, "features_enabled": feat,
        "fastest_verified_zero_loss_speed": last_pass,
        "lowest_tested_failing_speed": first_fail,
        "runs": runs,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"mission4_sweep_{port.replace('/', '_')}_{'feat' if feat else 'nofeat'}.json").write_text(
        json.dumps(sweep_summary, indent=2) + "\n")
    return sweep_summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=921600)
    sub = ap.add_subparsers(dest="action", required=True)
    p = sub.add_parser("predict")
    p = sub.add_parser("stream")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--skip", type=int, nargs="*", default=[])
    p.add_argument("--features-off", action="store_true")
    p.add_argument("--export-dataset", action="store_true")
    p = sub.add_parser("sweep")
    p.add_argument("--speeds", type=float, nargs="+", default=[1.0, 1.25, 1.5, 2.0, 3.0, 4.0])
    p.add_argument("--features-off", action="store_true")
    a = ap.parse_args()
    if a.action == "predict":
        print(json.dumps(expected_counts(), indent=2))
    elif a.action == "stream":
        if not a.port:
            ap.error("--port is required for stream")
        print(json.dumps(run_stream(a.port, a.baud, a.speed, a.skip,
                                    not a.features_off, a.export_dataset), indent=2))
    else:
        if not a.port:
            ap.error("--port is required for sweep")
        print(json.dumps(speed_sweep(a.port, a.baud, a.speeds,
                                     not a.features_off), indent=2))


if __name__ == "__main__":
    main()
