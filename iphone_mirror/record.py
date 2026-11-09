"""Screen recording to MP4 (H.264 + AAC).

The iPhone sends a key frame only when mirroring starts or the format changes, so the
incoming H.264 stream cannot simply be copied into a file from the middle. Decoded frames
are re-encoded instead (libx264 'ultrafast', at most MAX_FPS) on a thread of their own;
when the encoder falls behind, frames are dropped rather than queued. PCM audio from the
player is encoded as AAC into the same file. When the video size changes (the iPhone
rotates), the current file is finished and a new part is started, because an MP4 track
cannot change its size.

    rec = Recorder(folder, audio=True)
    rec.video(av_frame)      # decoder thread
    rec.audio(pcm_int16x2)   # audio thread
    paths = rec.stop()
"""
import logging
import queue
import threading
import time
from fractions import Fraction
from pathlib import Path

import av

log = logging.getLogger(__name__)

MAX_FPS = 30
RATE = 44100
QUEUE = 90  # video frames + audio chunks waiting for the encoder thread
MS = Fraction(1, 1000)


class Recorder:
    def __init__(self, folder: Path, audio: bool = True, stamp: str = None):
        self.folder = Path(folder)
        self.with_audio = audio
        self.stamp = stamp or time.strftime("%Y-%m-%d %H-%M-%S")
        self.paths = []  # finished or current files
        # perf_counter, not monotonic: monotonic() only ticks every ~16 ms on Windows
        self.t0 = time.perf_counter()
        self._part_t0 = self.t0  # pts 0 of the current file
        self.dropped = 0
        self.frames = 0
        self._q = queue.Queue(maxsize=QUEUE)
        self._last_video = -1.0
        self._last_pts = -1
        self._out = self._vs = self._as = None
        self._size = None
        self._audio_next = None  # pts (in samples) the next audio chunk would have
        self._thread = threading.Thread(target=self._run, name="recorder", daemon=True)
        self._thread.start()

    @property
    def seconds(self) -> float:
        return time.perf_counter() - self.t0

    # ------------------------------------------------------------ producers (any thread)
    def video(self, frame):
        now = time.perf_counter()
        if now - self._last_video < 1 / MAX_FPS:
            return
        self._last_video = now
        self._put(("v", frame, now))

    def audio(self, pcm):
        if self.with_audio:
            self._put(("a", pcm, time.perf_counter()))

    def _put(self, item):
        try:
            self._q.put_nowait(item)
        except queue.Full:
            self.dropped += 1

    def stop(self) -> list:
        self._q.put(None)  # blocks briefly if full: the encoder thread is draining it
        self._thread.join(timeout=10)
        return [p for p in self.paths if p.exists()]

    # ------------------------------------------------------------ encoder thread
    def _run(self):
        try:
            while True:
                item = self._q.get()
                if item is None:
                    break
                kind, data, t = item
                if kind == "v":
                    self._encode_video(data, t)
                elif self._out is not None:
                    self._encode_audio(data, t)
        except Exception:
            log.exception("recording failed")
        finally:
            self._close()
            log.info("recording stopped: %d frames, %d dropped, %s", self.frames, self.dropped,
                     ", ".join(str(p) for p in self.paths))

    def _open(self, w, h, t):
        part = len(self.paths) + 1
        name = f"iPhone {self.stamp}" + (f" ({part})" if part > 1 else "") + ".mp4"
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / name
        out = av.open(str(path), "w")
        vs = out.add_stream("libx264", rate=MAX_FPS, options={"preset": "ultrafast", "crf": "23"})
        vs.width, vs.height = w, h
        vs.pix_fmt = "yuv420p"
        vs.time_base = vs.codec_context.time_base = MS  # millisecond pts: frames arrive at a variable rate
        a = None
        if self.with_audio:
            a = out.add_stream("aac", rate=RATE, layout="stereo")
            a.time_base = Fraction(1, RATE)
        self._out, self._vs, self._as, self._size = out, vs, a, (w, h)
        self._audio_next = None
        self._last_pts = -1
        self._part_t0 = t
        self.paths.append(path)
        log.info("recording to %s (%dx%d)", path, w, h)

    def _close(self):
        out, self._out = self._out, None
        if out is None:
            return
        try:
            for p in self._vs.encode():
                out.mux(p)
            if self._as is not None:
                for p in self._as.encode():
                    out.mux(p)
        except Exception:
            log.exception("could not finish the recording")
        out.close()

    def _encode_video(self, frame, t):
        w, h = frame.width & ~1, frame.height & ~1  # yuv420p needs even sizes
        if self._size != (w, h):
            self._close()
            self._open(w, h, t)
        f = frame.reformat(width=w, height=h, format="yuv420p")
        f.pts = self._last_pts = max(int((t - self._part_t0) * 1000), self._last_pts + 1)
        f.time_base = MS
        for p in self._vs.encode(f):
            self._out.mux(p)
        self.frames += 1

    def _encode_audio(self, pcm, t):
        start = int((t - self._part_t0) * RATE) - len(pcm)  # the chunk ends about now
        if self._audio_next is None or start > self._audio_next + RATE // 4:
            self._audio_next = max(0, start)  # first chunk, or a gap (audio paused)
        f = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format="s16", layout="stereo")
        f.sample_rate = RATE
        f.pts = self._audio_next
        f.time_base = self._as.time_base
        self._audio_next += len(pcm)
        for p in self._as.encode(f):
            self._out.mux(p)
