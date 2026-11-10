"""Measures H.264 decoding and the scale/convert step per frame at an iPhone-like resolution.

Usage:  python tools/bench_decode.py [frames]
"""
import sys
import time
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from av.video.reformatter import VideoReformatter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from iphone_mirror.video import to_bgra  # noqa: E402

W, H = 886, 1920  # 1080p AirPlay stream of a portrait iPhone


def make_clip(n):
    enc = av.CodecContext.create("libx264", "w")
    enc.width, enc.height, enc.pix_fmt = W, H, "yuv420p"
    enc.time_base = Fraction(1, 60)
    enc.options = {"preset": "ultrafast", "tune": "zerolatency"}
    y, x = np.mgrid[0:H, 0:W]
    packets = []
    for i in range(n):
        img = np.stack([(x + i * 6) % 256, (y + i * 3) % 256, ((x ^ y) + i) % 256], -1).astype(np.uint8)
        f = av.VideoFrame.from_ndarray(img, format="rgb24").reformat(format="yuv420p")
        f.pts = i
        packets += [bytes(p) for p in enc.encode(f)]
    packets += [bytes(p) for p in enc.encode()]
    return packets


def main(n=120):
    packets = make_clip(n)
    dec = av.CodecContext.create("h264", "r")
    dec.thread_type = "SLICE"
    frames = []
    t = time.perf_counter()
    for p in packets:
        frames += dec.decode(av.Packet(p))
    print(f"decode: {(time.perf_counter() - t) * 1000 / len(frames):.2f} ms/frame ({W}x{H})")
    scaler = VideoReformatter()
    for target in ((242, 524), (480, 1040), (886, 1920)):  # small window, large window, full size
        t = time.perf_counter()
        for f in frames:
            to_bgra(f, target, scaler)
        ms = (time.perf_counter() - t) * 1000 / len(frames)
        print(f"scale to {target[0]}x{target[1]}: {ms:.2f} ms/frame")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 120)
