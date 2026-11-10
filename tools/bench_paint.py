"""Measures how long the window takes to paint one mirrored frame.

Usage:  python tools/bench_paint.py [frames]
"""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from iphone_mirror.config import Settings  # noqa: E402
from iphone_mirror.ui import PhoneWindow  # noqa: E402


def main(n=300):
    app = QApplication(sys.argv[:1])
    settings = Settings(Path(tempfile.mkdtemp()) / "s.json")
    win = PhoneWindow(settings, None)
    win.show()
    w, h = win.phone_size()
    frame = np.random.randint(0, 255, (h, w, 4), dtype=np.uint8)
    win.on_frame(frame, 1179, 2556)
    app.processEvents()
    win.hover = True
    win.repaint()  # warm up: the first text drawn loads the font database (one-off, slow)
    for hover in (False, True):
        win.hover = hover
        t = time.perf_counter()
        for _ in range(n):
            win.on_frame(frame, 1179, 2556)
            app.processEvents()  # paints what the frame made dirty, like the running app
        ms = (time.perf_counter() - t) * 1000 / n
        print(f"hover={hover}: {ms:.2f} ms per frame ({w}x{h} phone)")
    win.close()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
