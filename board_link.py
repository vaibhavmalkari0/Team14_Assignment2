"""
board_link.py -- talk to the board running doorbell_board_starter.ino
AI255TBD Edge AI, Module 2 "The Doorbell's Ears"

This moves bytes and keeps count of what got lost. Choosing the sampling rate,
the number format, the scale, the feature settings and where to store the
recording is your job, in your own code.

    from board_link import Board
    b = Board("COM5")                    # /dev/ttyACM0 or /dev/ttyUSB0 on Linux, /dev/cu.usbmodem... on a Mac
    print(b.info())

    # you quantise and pack the samples yourself, e.g. int16:
    payload = np.round(x * 32767).astype("<i2").tobytes()
    r = b.stream(payload, fs=16000, fmt="i16", win=480, hop=320, nfft=512, mels=40,
                 store="psram", speed=1.0)
    r["features"]        # (frames, 40) numpy array computed ON THE BOARD
    r["board"]           # the board's own summary: frames received, bad CRCs, gaps, compute time...
    r["lost_features"]   # feature frames you expected but never got back

Command line:
    python board_link.py ports
    python board_link.py --port COM5 info
    python board_link.py --port COM5 --baud 115200 baud 921600

Needs:  pip install pyserial numpy
"""
import argparse
import struct
import threading
import time
import zlib

import numpy as np
import serial
import serial.tools.list_ports

_UP = b"\xA5\x5A"      # laptop -> board
_DOWN = b"\xB5\x5B"    # board -> laptop
_FMT_BYTES = {"f32": 4, "i16": 2, "i8": 1}


def _kv(text: str) -> dict:
    out = {}
    for tok in text.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            try:
                out[k] = int(v, 16) if k == "crc" else int(v)
            except ValueError:
                out[k] = v
    return out


def frame(ftype: bytes, seq: int, payload: bytes) -> bytes:
    """Build one laptop->board frame: A5 5A | type | seq u32 | len u16 | payload | crc32."""
    body = ftype + struct.pack("<IH", seq, len(payload)) + payload
    return _UP + body + struct.pack("<I", zlib.crc32(body))


class Board:
    def __init__(self, port: str, baud: int = 921600, timeout: float = 5.0):
        self.ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(0.2)
        self.ser.reset_input_buffer()

    def close(self):
        self.ser.close()

    # ------------------------------------------------------------ text commands
    def _line(self) -> str:
        raw = self.ser.readline()
        if not raw:
            raise TimeoutError("no reply from the board (right port? right baud? sketch flashed?)")
        return raw.decode(errors="replace").strip()

    def cmd(self, text: str) -> str:
        self.ser.write((text + "\n").encode())
        return self._line()

    def ping(self) -> bool:
        return self.cmd("PING") == "PONG"

    def info(self) -> dict:
        return _kv(self.cmd("INFO"))

    def set_baud(self, rate: int) -> None:
        """Changes the UART (COM) port's speed. The native USB port ignores it."""
        if not self.cmd(f"BAUD {rate}").startswith("OK"):
            raise RuntimeError("board refused BAUD")
        time.sleep(0.05)
        self.ser.baudrate = rate
        time.sleep(0.05)
        self.ser.reset_input_buffer()

    def save(self) -> dict:
        """Copy the last stored stream to flash, so it survives a power cut."""
        old = self.ser.timeout
        self.ser.timeout = max(old, 60)
        try:
            rep = self.cmd("SAVE")
        finally:
            self.ser.timeout = old
        if not rep.startswith("OK"):
            raise RuntimeError(rep)
        return _kv(rep)

    def dump(self, where: str) -> bytes:
        rep = self.cmd(f"DUMP {where}")
        if not rep.startswith("DATA"):
            raise RuntimeError(rep)
        n = int(rep.split()[1])
        old = self.ser.timeout
        self.ser.timeout = max(old, 30)
        try:
            buf = bytearray()
            while len(buf) < n:
                part = self.ser.read(n - len(buf))
                if not part:
                    raise TimeoutError(f"got {len(buf)} of {n} bytes")
                buf += part
            return bytes(buf)
        finally:
            self.ser.timeout = old

    def crc(self, where: str) -> dict:
        return _kv(self.cmd(f"CRC {where}"))

    def free(self):
        self.cmd("FREE")

    # ------------------------------------------------------------ streaming
    def stream(self, payload: bytes, fs: int, fmt: str = "i16", scale: float = 1.0,
               win: int = 480, hop: int = 320, nfft: int = 512, mels: int = 40, mfcc: int = 0,
               feat: bool = True, store: str = "none", max_bytes: int = 0,
               speed: float = 1.0, samples_per_packet: int = 320, skip: tuple = ()) -> dict:
        """Stream packed samples to the board and collect the features it sends back.

        payload            your samples, already quantised and packed in format `fmt`
        speed              1.0 = real time (one second of audio per second), 4.0 = four times
                           faster, 0 = as fast as the link allows
        samples_per_packet how many samples go in each frame (at most 4096 bytes per frame)
        store              'none', 'sram' or 'psram'; max_bytes = how much room to ask for
        skip               frame numbers to deliberately NOT send (to test your loss accounting)
        """
        bps = _FMT_BYTES[fmt]
        if len(payload) % bps:
            raise ValueError("payload length is not a whole number of samples")
        if samples_per_packet * bps > 4096:
            raise ValueError("a frame can carry at most 4096 bytes")
        n_samples = len(payload) // bps
        line = (f"STREAM fs={fs} fmt={fmt} scale={scale} win={win} hop={hop} nfft={nfft} "
                f"mels={mels} mfcc={mfcc} feat={int(feat)} store={store} max={max_bytes or len(payload)}")
        rep = self.cmd(line)
        if not rep.startswith("READY"):
            raise RuntimeError(rep)
        ready = _kv(rep)
        dim = ready.get("out", mfcc or mels)

        got = {"frames": {}, "summary": None, "bad_crc": 0, "arrive": {}}
        stop = threading.Event()

        def reader():
            buf = bytearray()
            while not stop.is_set():
                chunk = self.ser.read(self.ser.in_waiting or 1)
                if not chunk:
                    continue
                buf += chunk
                while True:
                    i = buf.find(_DOWN)
                    if i < 0:
                        del buf[:-1]
                        break
                    if len(buf) < i + 9:
                        break
                    ftype = bytes(buf[i + 2:i + 3]); seq, ln = struct.unpack_from("<IH", buf, i + 3)
                    if ln > 4096:
                        del buf[:i + 2]
                        continue
                    end = i + 9 + ln + 4
                    if len(buf) < end:
                        break
                    body = bytes(buf[i + 2:i + 9 + ln]); (crc,) = struct.unpack_from("<I", buf, i + 9 + ln)
                    del buf[:end]
                    if zlib.crc32(body) != crc:
                        got["bad_crc"] += 1
                        continue
                    pl = body[7:]
                    if ftype == b"F":
                        first, us = struct.unpack_from("<II", pl, 0)
                        got["frames"][seq] = (first, us, np.frombuffer(pl, "<f4", offset=8).copy())
                        got["arrive"][seq] = time.perf_counter()
                    elif ftype == b"S":
                        got["summary"] = _kv(pl.decode(errors="replace"))
                        stop.set()

        th = threading.Thread(target=reader, daemon=True)
        th.start()

        step = samples_per_packet * bps
        t0 = time.perf_counter()
        seq = 0
        for off in range(0, len(payload), step):
            if speed > 0:   # a packet can only leave once its last sample "exists"
                due = t0 + (off // bps + len(payload[off:off + step]) // bps) / (fs * speed)
                while time.perf_counter() < due:
                    time.sleep(min(0.002, max(0.0, due - time.perf_counter())))
            if seq not in skip:
                self.ser.write(frame(b"D", seq, payload[off:off + step]))
            seq += 1
        self.ser.write(frame(b"E", seq, b""))
        t_sent = time.perf_counter() - t0
        th.join(timeout=10 + n_samples / fs)
        stop.set()

        expected = 0 if n_samples < win or not feat else 1 + (n_samples - win) // hop
        nums = sorted(got["frames"])
        feats = np.array([got["frames"][k][2] for k in nums]).reshape(-1, dim) if nums else np.zeros((0, dim))
        first = np.array([got["frames"][k][0] for k in nums], dtype=np.int64)
        us = np.array([got["frames"][k][1] for k in nums], dtype=np.int64)
        # lag: how long after a frame's last sample existed (in real time) did its features arrive?
        if speed > 0 and nums:
            due = t0 + (first + win) / (fs * speed)
            lag = np.array([got["arrive"][k] for k in nums]) - due
        else:
            lag = np.array([])
        return dict(
            features=feats, frame_numbers=np.array(nums), first_sample=first, compute_us=us, lag_s=lag,
            expected_features=expected, lost_features=expected - len(nums), bad_crc_back=got["bad_crc"],
            packets_sent=seq - len(skip), bytes_sent=len(payload), send_seconds=t_sent,
            audio_seconds=n_samples / fs, board=got["summary"], ready=ready,
        )


def _main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=921600)
    sub = ap.add_subparsers(dest="what", required=True)
    sub.add_parser("ports"); sub.add_parser("ping"); sub.add_parser("info")
    r = sub.add_parser("baud"); r.add_argument("rate", type=int)
    a = ap.parse_args()
    if a.what == "ports":
        for p in serial.tools.list_ports.comports():
            print(f"{p.device:20s} {p.description}")
        return
    if not a.port:
        ap.error("--port is needed (python board_link.py ports lists them)")
    b = Board(a.port, a.baud)
    if a.what == "ping":
        print("PONG" if b.ping() else "no reply")
    elif a.what == "info":
        for k, v in b.info().items():
            print(f"{k:14s} {v:>12,}" if isinstance(v, int) else f"{k:14s} {v}")
    elif a.what == "baud":
        b.set_baud(a.rate)
        print(f"UART port now at {a.rate} baud; PING -> {'PONG' if b.ping() else 'nothing'}")
    b.close()


if __name__ == "__main__":
    _main()
