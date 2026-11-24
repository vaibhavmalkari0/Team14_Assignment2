"""
team_audio.py  --  AI255TBD Edge AI, Module 2 assignment "The Doorbell's Ears"

Your laptop plays the doorbell's microphone. This file makes your team's labelled
audio: one-second clips of four command words, other words, and silence, recorded
in your doorbell's own "room" (its background noise, mains hum, and the faint
high-pitched whine of its power supply).

The words come from speech_pool.npz (keep it next to this file): 780 recordings
made with a speech synthesiser in many voices (male and female; American, British,
Scottish and Caribbean accents; different speeds and pitches). Your team number
decides which speakers you get and what your room sounds like, so your numbers
will not match another team's.

Read it, but do NOT edit it. The instructor's copy makes the same audio for your
team number.

    from team_audio import CLASSES, clip_list, get_clip

    clips = clip_list(team=7)                 # [(clip_id, label), ...] 144 clips
    x = get_clip(team=7, clip_id=0, fs=16000) # float32, one second, values in -1..1
    x = get_clip(team=7, clip_id=0, fs=8000, antialias=True)  # with the mic's filter

The microphone records at up to 48 kHz. Allowed fs: 48000, 24000, 16000,
12000, 8000, 6000, 4000. With antialias=False you get exactly what an ADC
would give you with no filter in front of it.

Listen to it:  python team_audio.py 7      (writes team_07_preview.wav)
Needs: numpy
"""

import os

import numpy as np

CLASSES = ["on", "off", "stop", "go", "_unknown", "_silence"]
CLIPS_PER_CLASS = 24
FS_MIC = 48000
ALLOWED_FS = (48000, 24000, 16000, 12000, 8000, 6000, 4000)
_COMMANDS = CLASSES[:4]
_POOL = None


def _pool():
    global _POOL
    if _POOL is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "speech_pool.npz")
        if not os.path.exists(path):
            raise FileNotFoundError("speech_pool.npz must be in the same folder as team_audio.py")
        d = np.load(path)
        _POOL = {k: d[k] for k in d.files}
    return _POOL


def _rng(team, *keys):
    return np.random.default_rng([20261110, int(team)] + [int(k) for k in keys])


def _team(team):
    if not (1 <= int(team) <= 99):
        raise ValueError("team must be an integer from 1 to 99")
    r = _rng(team, 0)
    return dict(
        whine=float(r.uniform(5600.0, 7400.0)),    # the doorbell's switching regulator
        whine_amp=float(r.uniform(0.035, 0.06)),
        hum=float(r.choice([50.0, 50.0, 100.0])),  # mains hum
        noise=float(r.uniform(0.004, 0.008)),      # room noise
    )


def clip_list(team):
    """Every clip for your team: [(clip_id, label), ...] in a fixed order."""
    _team(team)
    return [(c * CLIPS_PER_CLASS + k, lab) for c, lab in enumerate(CLASSES) for k in range(CLIPS_PER_CLASS)]


def _recording(team, clip_id):
    """Which pool recording a clip uses: a team-specific shuffle, so the 24 clips of a word are 24 different recordings."""
    P = _pool()
    c, k = divmod(clip_id, CLIPS_PER_CLASS)
    lab = CLASSES[c]
    if lab in _COMMANDS:
        cand = np.flatnonzero(P["word"] == lab)
    else:
        cand = np.flatnonzero(~np.isin(P["word"], _COMMANDS))
    return int(_rng(team, 2, c).permutation(cand)[k])


def _clip48(team, clip_id):
    P = _team(team)
    if not (0 <= int(clip_id) < len(CLASSES) * CLIPS_PER_CLASS):
        raise ValueError(f"clip_id must be 0..{len(CLASSES) * CLIPS_PER_CLASS - 1}")
    lab = CLASSES[clip_id // CLIPS_PER_CLASS]
    r = _rng(team, 1, clip_id)
    n = FS_MIC
    t = np.arange(n) / FS_MIC
    x = np.zeros(n)
    if lab != "_silence":
        pool = _pool()
        i = _recording(team, clip_id)
        s = pool["audio"][pool["start"][i]: pool["start"][i] + pool["length"][i]].astype(np.float64) / 32767
        speed = r.uniform(0.93, 1.07)                               # a little faster or slower
        m = int(s.size * FS_MIC / float(pool["sr"]) / speed)
        w = np.interp(np.linspace(0, s.size - 1, m), np.arange(s.size), s)
        w = w[: int(0.9 * n)]
        start = int(r.uniform(0.04, 0.96 - w.size / n) * n)
        x[start:start + w.size] += r.uniform(0.35, 0.7) * w
    # the room: noise, mains hum, and the doorbell's own regulator whine
    x += P["noise"] * r.standard_normal(n)
    x += 0.01 * np.sin(2 * np.pi * P["hum"] * t + r.uniform(0, 6))
    x += P["whine_amp"] * (1 + 0.1 * np.sin(2 * np.pi * 3 * t)) * np.sin(2 * np.pi * P["whine"] * t + r.uniform(0, 6))
    return np.clip(x, -1, 1)


def _lowpass_decimate(x, q):
    """The microphone's anti-alias filter: windowed-sinc low-pass at 0.45*fs_out, then keep every q-th sample."""
    taps = 255
    fc = 0.45 / q
    k = np.arange(taps) - (taps - 1) / 2
    h = 2 * fc * np.sinc(2 * fc * k) * np.blackman(taps)
    h /= h.sum()
    return np.convolve(x, h, mode="same")[::q]


def get_clip(team, clip_id, fs=16000, antialias=False):
    """One second of audio for clip_id, sampled at fs. float32 in -1..1."""
    if fs not in ALLOWED_FS:
        raise ValueError(f"fs must be one of {ALLOWED_FS}")
    x = _clip48(team, clip_id)
    q = FS_MIC // fs
    if q > 1:
        x = _lowpass_decimate(x, q) if antialias else x[::q]
    return x.astype(np.float32)


def _write_wav(path, x, fs):
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fs)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    import sys
    team = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    picks = [c * CLIPS_PER_CLASS + k for c in range(len(CLASSES)) for k in range(2)]
    gap = np.zeros(4000, np.float32)
    x = np.concatenate([np.r_[get_clip(team, i, 16000, antialias=True), gap] for i in picks])
    _write_wav(f"team_{team:02d}_preview.wav", x, 16000)
    print(f"team {team}: {len(clip_list(team))} clips of 1 s; wrote two of each class "
          f"({', '.join(CLASSES)}) to team_{team:02d}_preview.wav")
