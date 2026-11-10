"""iPhone-shaped floating window (PySide6).

Control off (default): the window is a plain mirror. Drag it anywhere to move it,
double-click to switch between big and normal size.

Control on (WebDriverAgent ready, see control/): mouse and keyboard input on the
phone area goes to the iPhone. Click = tap, press and hold = long press, drag =
swipe, double-click = double tap, wheel = scroll, typing = text. The window is
then moved by dragging the top bar or with Alt+drag anywhere.
"""
import functools
import logging
import math
import os
import ctypes
import threading
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QToolTip, QWidget

from . import autostart
from .config import APP_NAME
from .control import ERROR, OFF, READY, STARTING

log = logging.getLogger(__name__)

SHADOW = 22  # px around the phone for the drop shadow
BAR = 40  # px above the phone for the hover bar
DEFAULT_ASPECT = 1179 / 2556  # iPhone portrait

# input mapping when iPhone control is on
LONG_PRESS_S = 0.5  # hold at least this long without moving = long press
TAP_SLOP = 6.0  # px the mouse may move before a press becomes a swipe
SWIPE_MIN_S, SWIPE_MAX_S = 0.06, 1.5  # swipe duration = real drag time, clamped
DOUBLE_TAP_MS = 200  # a click is held back this long in case a second click makes it a double tap
WHEEL_BATCH_MS = 120  # wheel notches are summed for this long, then sent as one scroll
TYPE_BATCH_MS = 80  # typed characters are buffered for this long, then sent together
HINT_S = 2.6  # how long a status hint stays in the top bar

# Ctrl+wheel resizing: per 120 units of wheel delta (one notch). Touchpad pinches and smooth
# scrolling send many small deltas, which are summed and applied at most every ZOOM_MS.
ZOOM_PER_NOTCH = 1.06
ZOOM_MS = 30
RESCALE_MS = 80  # after the last size change, the shown frame is scaled again from the original

# Windows virtual-key codes: shortcuts must also work with non-Latin keyboard layouts
VK_H, VK_I, VK_J, VK_M, VK_R, VK_S, VK_U = 0x48, 0x49, 0x4A, 0x4D, 0x52, 0x53, 0x55
VK_B, VK_K, VK_L, VK_N, VK_V = 0x42, 0x4B, 0x4C, 0x4E, 0x56
PASTE_MAX = 2000  # characters typed by one Ctrl+V (WDA types ~60/s: about half a minute)
VK_OEM_PLUS, VK_OEM_MINUS, VK_ADD, VK_SUBTRACT = 0xBB, 0xBD, 0x6B, 0x6D

GREEN, ORANGE, RED = QColor("#30d158"), QColor("#ff9f0a"), QColor("#ff453a")
OPACITIES = (1.0, 0.9, 0.75, 0.5)
# stream quality presets: label -> requested (width, height); the iPhone scales its screen into it
QUALITIES = (("720p", 1280, 720), ("1080p", 1920, 1080), ("1440p", 2560, 1440))
FRAME_RATES = (30, 60)

# SetThreadExecutionState flags
ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000001, 0x00000002


def keep_awake(on: bool) -> bool:
    """Keep Windows (system and display) awake, or allow sleep again. The request belongs
    to the calling thread, so it is always made from the GUI thread."""
    try:
        flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED if on else 0)
        return bool(ctypes.windll.kernel32.SetThreadExecutionState(flags))
    except (AttributeError, OSError):  # not Windows
        return False


class Bridge(QObject):
    """Carries callbacks from worker threads to the GUI thread (queued signals)."""

    frame = Signal(object, int, int)  # emitted on the GUI thread, see post_frame
    event = Signal(str, dict)
    control = Signal(str, str)  # Controller.on_state(state, message)
    _frame_posted = Signal()

    def __init__(self):
        super().__init__()
        self._latest = None  # newest frame the GUI thread has not taken yet
        self._lock = threading.Lock()
        self._frame_posted.connect(self._take_frame, Qt.QueuedConnection)

    def post_frame(self, arr, src_w, src_h):
        """Decoder thread. Only the newest frame is kept: when the GUI thread is busy it shows
        the latest picture next, instead of working through (and holding in memory) a backlog."""
        with self._lock:
            waiting = self._latest is not None
            self._latest = (arr, src_w, src_h)
        if not waiting:
            self._frame_posted.emit()

    def _take_frame(self):
        with self._lock:
            item, self._latest = self._latest, None
        if item is not None:
            self.frame.emit(*item)


@functools.lru_cache(maxsize=64)
def font(size: int, bold: bool = False) -> QFont:
    """Fonts and their metrics are cached: resolving a font (and measuring text with a new
    QFontMetrics) costs several milliseconds on Windows, far too much to do every frame."""
    return QFont("Segoe UI", size, QFont.DemiBold if bold else QFont.Normal)


@functools.lru_cache(maxsize=64)
def metrics(size: int, bold: bool = False) -> QFontMetrics:
    return QFontMetrics(font(size, bold))


@functools.lru_cache(maxsize=256)
def text_width(size: int, bold: bool, text: str) -> int:
    return metrics(size, bold).horizontalAdvance(text)


def app_icon(size: int = 64) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 64, size / 64)
    g = QLinearGradient(0, 0, 64, 64)
    g.setColorAt(0, QColor("#5e5ce6"))
    g.setColorAt(1, QColor("#bf5af2"))
    p.setBrush(g)
    p.setPen(QPen(QColor("#1c1c1e"), 3))
    p.drawRoundedRect(QRectF(16, 3, 32, 58), 9, 9)
    p.setBrush(QColor("#1c1c1e"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(26, 8, 12, 4), 2, 2)
    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------- input helpers
def clamp01(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else float(v)


def to_fraction(rect: QRectF, pos) -> tuple:
    """Window position -> (x, y) as fractions 0..1 of the phone screen rect, clamped."""
    w, h = rect.width() or 1.0, rect.height() or 1.0
    return clamp01((pos.x() - rect.x()) / w), clamp01((pos.y() - rect.y()) / h)


def swipe_seconds(held: float) -> float:
    return max(SWIPE_MIN_S, min(SWIPE_MAX_S, held))


def key_text(event) -> str:
    """Text a key press types on the iPhone: printable characters, '\\b' or '\\n' ('' = none)."""
    mods = event.modifiers()
    ctrl, alt = bool(mods & Qt.ControlModifier), bool(mods & Qt.AltModifier)
    if ctrl != alt:  # Ctrl+key / Alt+key are shortcuts; Ctrl+Alt is AltGr on Windows (still typing)
        return ""
    k = event.key()
    if k == Qt.Key_Backspace:
        return "\b"
    if k in (Qt.Key_Return, Qt.Key_Enter):
        return "\n"
    t = event.text()
    return t if t and all(c.isprintable() for c in t) else ""


def is_key(event, keys, vks=()) -> bool:
    return event.key() in keys or (bool(vks) and event.nativeVirtualKey() in vks)


class PhoneWindow(QWidget):
    notice = Signal(str, str)  # (title, text) from worker threads, shown as a notification
    def __init__(self, settings, receiver_ref, controller=None):
        super().__init__()
        self.settings = settings
        self.rx = receiver_ref  # set later by main
        self.ctrl = controller  # control.Controller (optional)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._apply_flags()
        self.setWindowOpacity(max(0.3, min(1.0, float(settings.get("opacity") or 1.0))))
        self._awake = False  # keep_awake() requested

        self.image = None  # QImage of the current frame (device pixels)
        self._array = None  # keeps the ndarray behind self.image alive
        self.src_size = None
        self.aspect = DEFAULT_ASPECT
        self.state = "starting"
        self.info = {}
        self.client = None
        self.fullscreen = False
        self._normal_pos = None  # window position to return to after full screen
        self.hover = False
        self.drag_offset = None
        self.fps = 0.0
        self.kbps = 0.0
        self.show_stats = False  # Ctrl+I overlay
        self._bytes0 = 0
        self._frames = 0
        self._fps_t = time.time()
        self._hide_bar = QTimer(self, singleShot=True, interval=1200, timeout=self._bar_off)
        self._hover_btn = None
        self._hint_text = ""
        self._hint_until = 0.0
        self._zoom_acc = 0  # Ctrl+wheel delta not applied yet
        self._zoom_timer = QTimer(self, singleShot=True, interval=ZOOM_MS, timeout=self._apply_zoom)

        # iPhone control
        self.control_state = OFF  # controller state as of the last on_control (GUI thread)
        self.control_message = ""
        self._control_serial = 0  # Controller.snapshot() serial of the shown state
        self._error_serial = None  # serial of the last error shown in a message box
        self._error_box = None
        self._g = None  # gesture in progress: dict(pos0, pos, t0, moved, done, double)
        self._long_timer = QTimer(self, singleShot=True, interval=int(LONG_PRESS_S * 1000), timeout=self._on_long_press)
        self._pending_tap = None  # (x, y) fractions of a click that may still become a double tap
        self._tap_timer = QTimer(self, singleShot=True, interval=DOUBLE_TAP_MS, timeout=self._flush_tap)
        self._wheel_acc = 0.0
        self._wheel_pos = (0.5, 0.5)
        self._wheel_timer = QTimer(self, singleShot=True, interval=WHEEL_BATCH_MS, timeout=self._flush_wheel)
        self._type_buf = ""
        self._type_timer = QTimer(self, singleShot=True, interval=TYPE_BATCH_MS, timeout=self._flush_type)
        self._preedit = ""  # text an input method is still composing
        self._ime_forced = None  # composing text sent by _commit_composition: skip it if the IME commits it too
        self._effects = []  # touch feedback: dict(kind, a, b, t, life), positions as fractions
        self._anim = QTimer(self, interval=16, timeout=self._tick)
        self._chrome_cache = None  # (key, pieces): see _chrome
        self._scaler = None  # av VideoReformatter of the GUI thread, see _rescale
        # after a resize: scale the last frame again (the iPhone sends none while its screen is still)
        self._rescale_timer = QTimer(self, singleShot=True, interval=RESCALE_MS, timeout=self._rescale)
        self._rec_timer = QTimer(self, interval=500, timeout=self._rec_tick)  # REC clock in the top bar
        self._saved_folder = None  # opened when the "saved" notification is clicked
        self._setup_win = None  # SetupWindow, created on first use
        self.notice.connect(self._show_message)

        screen = QApplication.primaryScreen().availableGeometry()
        ph = int(settings.get("phone_height") or 0) or int(screen.height() * 0.72)
        self.phone_h = max(320, min(ph, screen.height() - BAR - 2 * SHADOW))
        self._relayout(keep_center=False)
        x, y = settings.get("x"), settings.get("y")
        if x is not None and y is not None:
            c = QPoint(int(x) + self.width() // 2, int(y) + self.height() // 2)
            if QApplication.screenAt(c) is None:  # saved position is off-screen now
                x = y = None
        if x is None or y is None:
            x = screen.right() - self.width() - 40
            y = screen.top() + (screen.height() - self.height()) // 2
        self.move(int(x), int(y))

        self._tray = None
        self._setup_tray()

    # ------------------------------------------------------------ geometry
    def _apply_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Window
        if self.settings.get("always_on_top", False):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def phone_size(self):
        if self.fullscreen:
            r = self.phone_rect()
            return round(r.width()), round(r.height())
        if self.aspect <= 1:  # portrait: height is the reference
            h = self.phone_h
            w = round(h * self.aspect)
        else:  # landscape: keep the same long side
            w = self.phone_h
            h = round(w / self.aspect)
        return w, h

    def phone_rect(self) -> QRectF:
        """Where the iPhone screen is drawn. Its edges lie on whole device pixels (they would
        not at 125% or 150% display scaling), so a frame scaled to this size is copied to the
        screen 1:1 instead of being resampled, which is both sharper and much faster."""
        if self.fullscreen:  # as big as the screen allows, centred
            sw, sh = self.width(), self.height()
            w = min(sw, sh * self.aspect)
            h = w / self.aspect
            x, y = (sw - w) / 2, (sh - h) / 2
        else:
            x, y = SHADOW, SHADOW + BAR
            w, h = self.phone_size()
        dpr = self.devicePixelRatioF()
        return QRectF(round(x * dpr) / dpr, round(y * dpr) / dpr, round(w * dpr) / dpr, round(h * dpr) / dpr)

    def corner_radius(self) -> float:
        w, h = self.phone_size()
        return min(w, h) * (0.04 if self.fullscreen else 0.135)

    def _relayout(self, keep_center=True):
        if self.fullscreen:  # the window covers the screen; only the phone area changes
            self._update_target()
            self.update()
            return
        w, h = self.phone_size()
        center = self.geometry().center()
        self.setFixedSize(w + 2 * SHADOW, h + 2 * SHADOW + BAR)
        if keep_center:
            g = self.geometry()
            g.moveCenter(center)
            self.move(g.topLeft())
        self._update_target()
        self.update()

    def _target(self) -> tuple:
        """Size of the phone screen in device pixels: what frames are scaled to."""
        r, dpr = self.phone_rect(), self.devicePixelRatioF()
        return round(r.width() * dpr), round(r.height() * dpr)

    def _update_target(self):
        if self.rx is None:
            return
        target = self._target()
        if self.rx.decoder.target != target:
            self.rx.decoder.target = target
            self._rescale_timer.start()

    def _rescale(self):
        """Scale the last decoded frame to the window again. The iPhone sends a frame only when
        its screen changes, so without this a still screen stays blurry after the window grew,
        and stays empty after the window was hidden."""
        frame = getattr(self.rx.decoder, "last_frame", None) if self.rx else None
        if frame is None or self.state not in ("mirroring", "paused") or not self._on_screen():
            return
        from .video import to_bgra

        if self._scaler is None:
            from av.video.reformatter import VideoReformatter

            self._scaler = VideoReformatter()  # the decoder thread has its own
        try:
            self._set_image(to_bgra(frame, self._target(), self._scaler))
        except Exception:
            log.exception("could not rescale the frame")
        self.update()

    def _on_screen(self) -> bool:
        return self.isVisible() and not self.isMinimized()

    def _update_visible(self):
        """Tell the decoder whether anyone can see the picture (it skips scaling if not)."""
        if self.rx is None:
            return
        shown = self._on_screen()
        was = getattr(self.rx.decoder, "visible", True)
        self.rx.decoder.visible = shown
        if shown and not was:
            self._rescale()  # frames that arrived meanwhile were not scaled

    def showEvent(self, e):
        self._update_visible()

    def hideEvent(self, e):
        self._update_visible()

    def changeEvent(self, e):
        if e.type() == QEvent.WindowStateChange:  # minimized or restored
            self._update_visible()
        super().changeEvent(e)

    def set_phone_height(self, h):
        if self.fullscreen:
            return
        screen = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        self.phone_h = int(max(320, min(h, screen.height() + 400)))
        self._relayout()
        self.settings["phone_height"] = self.phone_h

    def toggle_fullscreen(self):
        if self.fullscreen:
            self.fullscreen = False
            self.showNormal()
            self._relayout(keep_center=False)
            if self._normal_pos is not None:
                self.move(self._normal_pos)
        else:
            self._normal_pos = self.pos()
            self.fullscreen = True
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX: undo setFixedSize
            self.showFullScreen()
            self.hover = False  # shown again when the mouse goes to the top
            self._hint("Full screen - press F11 or Esc to leave")
        self._update_target()
        self.update()

    def resizeEvent(self, e):
        if self.fullscreen:
            self._update_target()

    def _toggle_size(self):
        screen = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        target = int((screen.height() - BAR - 2 * SHADOW) * (0.97 if self.aspect <= 1 else 0.55))
        if abs(self.phone_h - target) < 20:
            target = int(screen.height() * 0.6)
        self.set_phone_height(target)

    # ------------------------------------------------------------ data from receiver / controller
    def _set_image(self, arr):
        """arr: BGRA ndarray (h, w, 4). video.to_bgra returns a view whose rows are padded:
        QImage reads those in place (bytes per line = the row stride), nothing is copied."""
        h, w = arr.shape[:2]
        self._array = arr
        rows = arr if arr.flags.c_contiguous else arr.base
        self.image = QImage(rows.data, w, h, arr.strides[0], QImage.Format_RGB32)

    def on_frame(self, arr, src_w, src_h):
        """A decoded frame. arr is None while the window is hidden (see _update_visible)."""
        if arr is not None:
            self._set_image(arr)
        aspect = src_w / src_h
        if self.src_size != (src_w, src_h):
            self.src_size = (src_w, src_h)
            if self.ctrl is not None:
                self.ctrl.screen_aspect = aspect  # lets the controller notice a rotation at once
            if abs(aspect - self.aspect) > 0.01:
                self.aspect = aspect
                self._relayout()
        if self.state != "mirroring":
            self.state = "mirroring"
            self._update_awake()
        self._frames += 1
        now = time.time()
        if now - self._fps_t >= 1:
            self.fps = self._frames / (now - self._fps_t)
            total = getattr(self.rx.decoder, "bytes", 0) if self.rx else 0
            self.kbps = (total - self._bytes0) * 8 / 1000 / (now - self._fps_t)
            self._bytes0 = total
            self._frames, self._fps_t = 0, now
            if self.hover:
                self.update()  # the fps in the top bar
        # only the phone screen changed: the shadow and the top bar are not painted again
        self.update(self.phone_rect().toAlignedRect())

    def on_event(self, event, info):
        log.debug("ui event %s %s", event, info)
        if event == "listening":
            self.info = info
            if self.state in ("starting", "error"):
                self.state = "waiting"
        elif event == "connecting":
            if not self.isVisible():  # started in the tray (--tray): show up when the iPhone connects
                self._show_front()
            self.client = info.get("name")
            self.state = "connecting"
            ip = info.get("ip")
            if self.ctrl is not None and ip:
                self.ctrl.device_ip = ip  # WebDriverAgent may already listen on the phone's Wi-Fi address
        elif event == "format":
            if self.state != "mirroring":
                self.state = "connecting"
        elif event == "paused":
            self.state = "paused"
            self.fps = self.kbps = 0.0  # no frames while the iPhone is locked
        elif event == "mirror_stopped":
            self.state = "waiting"
            self.fps = self.kbps = 0.0
            self.image = None
            self._array = None
            self.src_size = None
            if self.ctrl is not None:
                self.ctrl.screen_aspect = None
            self._drop_tap()  # the screen it was aimed at is gone
            self._cancel_gesture()
            if abs(self.aspect - DEFAULT_ASPECT) > 0.01:
                self.aspect = DEFAULT_ASPECT
                self._relayout()
        elif event == "decrypt_error":
            self.state = "decrypt_error"
        elif event == "error":
            self.state = "error"
            self.info = dict(self.info, message=info.get("message", ""))
        self._update_awake()  # only while frames arrive: not when paused (iPhone locked) or stopped
        self.update()

    def on_control(self, state, message):
        """Controller state change; connected through Bridge.control, so this runs on the GUI thread.

        Notifications from the control thread are queued, while stop() on the GUI thread
        notifies directly, so they can arrive out of order. The arguments are therefore only
        a wake-up call: the controller's current state is what gets shown."""
        if self.ctrl is not None:
            state, message, serial = self.ctrl.snapshot()
        else:
            serial = self._control_serial + 1
        message = message or ""
        changed = (state, message) != (self.control_state, self.control_message)
        became_ready = state == READY and self.control_state != READY
        new_error = state == ERROR and serial != self._error_serial  # each failure once, also a repeated one
        self.control_state, self.control_message = state, message
        self._control_serial = serial
        # input methods (e.g. Microsoft Vietnamese Telex, Chinese/Japanese IMEs) deliver their
        # composed text through inputMethodEvent, and only to widgets that accept it
        self.setAttribute(Qt.WA_InputMethodEnabled, state == READY)
        if state != READY:
            self._drop_tap()
            self._cancel_gesture()
            self._type_buf = ""
            self._wheel_acc = 0.0
        if new_error:
            self._error_serial = serial
            self._show_control_error(self.control_message or "iPhone control failed.")
        if became_ready:
            threading.Thread(target=self._check_expiry, name="wda-expiry", daemon=True).start()
        if changed or new_error:
            self._hint_text = ""  # the new control status replaces any older hint
            self._flash_bar()
        self._update_anim()
        self.update()

    def _update_awake(self):
        want = self.state == "mirroring" and bool(self.settings.get("keep_awake", True))
        if want != self._awake:
            self._awake = want
            keep_awake(want)

    def _set_opacity(self, value):
        self.settings["opacity"] = value
        self.settings.save()
        self.setWindowOpacity(value)

    def _toggle_autostart(self):
        on = autostart.set_enabled(not autostart.enabled())
        self._hint("Starts with Windows, in the tray" if on else "Does not start with Windows")

    def _toggle_keep_awake(self):
        self.settings["keep_awake"] = not self.settings.get("keep_awake", True)
        self.settings.save()
        self._update_awake()

    def _show_control_error(self, message):
        if self._error_box is not None:
            try:
                self._error_box.close()
            except RuntimeError:  # already deleted
                pass
        box = QMessageBox(QMessageBox.Warning, "iPhone control", message, QMessageBox.Ok, self)
        box.setWindowModality(Qt.NonModal)
        box.setAttribute(Qt.WA_DeleteOnClose)
        box.setTextInteractionFlags(Qt.TextSelectableByMouse)
        guide = box.addButton("Setup Guide", QMessageBox.HelpRole)
        guide.clicked.connect(self.open_setup)
        box.show()
        self._error_box = box

    def open_setup(self):
        """The 'Set Up iPhone Control' checklist window."""
        from .setup_window import SetupWindow

        if self._setup_win is None:
            self._setup_win = SetupWindow(self, start_control=self._start_control)
        self._setup_win.show()
        self._setup_win.raise_()
        self._setup_win.activateWindow()

    def _start_control(self):
        if self.ctrl is not None and not self.ctrl.active:
            self.ctrl.start()

    def _check_expiry(self):
        """Background check (worker thread), started when control becomes ready."""
        from .control import setup

        text = setup.expiry_warning()
        if text:
            try:
                self.notice.emit("iPhone control", text)
            except RuntimeError:  # window deleted meanwhile
                pass

    # ------------------------------------------------------------ painting
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.phone_rect()
        r = self.corner_radius()
        showing = self.image is not None and self.state in ("mirroring", "paused", "connecting")
        chrome = self._chrome(rect, r, showing)

        if self.fullscreen:
            p.fillRect(self.rect(), Qt.black)
        else:
            for pos, shadow, _ in chrome:
                p.drawPixmap(pos, shadow)

        if showing:
            # a frame scaled to the window (the usual case) maps 1:1 to device pixels: see phone_rect
            brush = QBrush(self.image)
            t = QTransform()
            t.translate(rect.x(), rect.y())
            t.scale(rect.width() / self.image.width(), rect.height() / self.image.height())
            brush.setTransform(t)
            p.setPen(Qt.NoPen)
            p.setBrush(brush)
            p.drawRoundedRect(rect, r, r)
            if self.state == "paused":
                p.setBrush(QColor(0, 0, 0, 150))
                p.drawRoundedRect(rect, r, r)
                self._center_text(p, rect, "iPhone is locked", "Unlock your iPhone to continue")
        else:
            self._paint_placeholder(p, rect, r)

        self._paint_touches(p, rect, r)
        if self.show_stats:
            self._paint_stats(p, rect)

        for pos, _, bezel in chrome:
            p.drawPixmap(pos, bezel)

        if self.hover:
            # a new frame repaints only the phone screen; the bar above it is still on screen
            if e.region().intersects(self._bar_rect().toAlignedRect()):
                self._paint_bar(p)
        elif self.rx is not None and self.rx.recorder is not None:  # recording, bar hidden: red dot
            p.setPen(Qt.NoPen)
            p.setBrush(RED)
            p.drawEllipse(QPointF(rect.x() + r * 0.55, rect.y() + r * 0.55), 5, 5)
        p.end()

    def _chrome(self, rect, r, outline) -> list:
        """Drop shadow and bezel, drawn once per window size instead of every frame.

        Both show only in a frame around the phone screen (the picture covers the inside), so
        only that frame is kept: a band along the top and the bottom, which hold the rounded
        corners, and a strip down each side. Returns [(position, shadow, bezel)], one entry per
        piece (shadow is None in full screen). The pieces lie on whole device pixels, so
        drawing one is a plain copy. outline: with the black line that edges a mirrored picture."""
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr, self.fullscreen, rect.x(), rect.y(), rect.width(), rect.height(), r,
               outline)
        if self._chrome_cache is not None and self._chrome_cache[0] == key:
            return self._chrome_cache[1]

        def dev(v):
            return round(v * dpr)

        x0, y0, x1, y1 = dev(rect.left()), dev(rect.top()), dev(rect.right()), dev(rect.bottom())
        left, top, right, bottom = 0, 0, dev(self.width()), dev(self.height())
        if self.fullscreen:  # no shadow: only the bezel, which hugs the phone screen
            left, top, right, bottom = max(left, x0 - 2), max(top, y0 - 2), min(right, x1 + 2), min(bottom, y1 + 2)
        c = math.ceil(r * dpr) + 2  # height of a rounded corner
        edge = math.ceil(2 * dpr)  # how far the bezel reaches into the picture
        boxes = (
            QRect(left, top, right - left, y0 + c - top),
            QRect(left, y1 - c, right - left, bottom - (y1 - c)),
            QRect(left, y0 + c, x0 + edge - left, y1 - y0 - 2 * c),
            QRect(x1 - edge, y0 + c, right - (x1 - edge), y1 - y0 - 2 * c),
        )

        def shadow(sp):
            sp.setPen(Qt.NoPen)
            for i in range(SHADOW, 0, -2):
                sp.setBrush(QColor(0, 0, 0, int(34 * (1 - i / SHADOW) ** 2) + 2))
                sp.drawRoundedRect(rect.adjusted(-i, -i + 6, i, i + 6), r + i, r + i)

        def bezel(sp):
            sp.setBrush(Qt.NoBrush)
            if outline:
                sp.setPen(QPen(Qt.black, 1))
                sp.drawRoundedRect(rect, r, r)
            sp.setPen(QPen(QColor(255, 255, 255, 46), 1.2))
            sp.drawRoundedRect(rect.adjusted(0.6, 0.6, -0.6, -0.6), r, r)
            sp.setPen(QPen(QColor(0, 0, 0, 120), 1))
            sp.drawRoundedRect(rect.adjusted(-0.5, -0.5, 0.5, 0.5), r + 0.5, r + 0.5)

        def piece(box, paint):
            pm = QPixmap(box.size())
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.transparent)
            sp = QPainter(pm)
            sp.setRenderHint(QPainter.Antialiasing)
            sp.translate(-box.x() / dpr, -box.y() / dpr)
            paint(sp)
            sp.end()
            return pm

        pieces = [
            (QPointF(box.x() / dpr, box.y() / dpr), None if self.fullscreen else piece(box, shadow), piece(box, bezel))
            for box in boxes
            if not box.isEmpty()
        ]
        self._chrome_cache = (key, pieces)
        return pieces

    def _paint_placeholder(self, p, rect, r):
        g = QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0.0, QColor("#2b1d3f"))
        g.setColorAt(0.55, QColor("#16131f"))
        g.setColorAt(1.0, QColor("#0b0b10"))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(rect, r, r)
        glow = QRadialGradient(rect.center() + QPointF(0, -rect.height() * 0.12), rect.width() * 0.6)
        glow.setColorAt(0, QColor(140, 110, 255, 70))
        glow.setColorAt(1, QColor(140, 110, 255, 0))
        p.setBrush(glow)
        p.drawRoundedRect(rect, r, r)

        # dynamic island
        iw, ih = rect.width() * 0.32, rect.width() * 0.09
        p.setBrush(QColor("#000000"))
        p.drawRoundedRect(QRectF(rect.center().x() - iw / 2, rect.y() + rect.width() * 0.035, iw, ih), ih / 2, ih / 2)

        self._paint_airplay_glyph(p, rect)
        name = self.info.get("name") or self.settings["name"]
        if self.state == "starting":
            title, sub = "Starting...", "Preparing the AirPlay receiver"
        elif self.state == "connecting":
            title, sub = "Connecting...", f"{self.client or 'iPhone'} is starting Screen Mirroring"
        elif self.state == "decrypt_error":
            title = "Could not decrypt the video"
            sub = (
                "Stop Screen Mirroring and connect again. If it keeps happening, "
                "send the log (right-click > Open Log)."
            )
        elif self.state == "error":
            title, sub = "Error", self.info.get("message", "")
        elif self.rx is not None and not self.rx.advertised:
            title = "Hidden"
            sub = "This PC is not shown in Screen Mirroring. Right-click > Visible in Screen Mirroring to show it."
        else:
            title = "Waiting for iPhone"
            sub = f'On your iPhone open Control Center > Screen Mirroring and choose "{name}"'
        self._center_text(p, rect, title, sub)

        addrs = self.info.get("addresses") or []
        if addrs:
            p.setFont(font(8))
            p.setPen(QColor(255, 255, 255, 90))
            p.drawText(
                QRectF(rect.x(), rect.bottom() - rect.width() * 0.16, rect.width(), 20),
                Qt.AlignHCenter,
                "PC: " + ", ".join(addrs) + "  -  iPhone and PC must be on the same Wi-Fi",
            )

    def _stats_lines(self) -> list:
        d = self.rx.decoder if self.rx else None
        lines = []
        if self.src_size:
            lines.append(f"Video  {self.src_size[0]}x{self.src_size[1]}")
        lines.append(f"Shown  {self.fps:.0f} fps")
        lines.append(f"Bitrate  {self.kbps / 1000:.1f} Mbit/s" if self.kbps >= 1000 else f"Bitrate  {self.kbps:.0f} kbit/s")
        if d is not None:
            lines.append(f"Decoded  {getattr(d, 'decoded', 0)}  dropped  {getattr(d, 'dropped', 0)}")
        q = self.settings
        lines.append(f"Requested  {q['height']}p {q['fps']} fps")
        return lines

    def _paint_stats(self, p, rect):
        lines = self._stats_lines()
        p.setFont(font(8))
        lh = metrics(8).height()
        w = max(text_width(8, False, t) for t in lines) + 16
        box = QRectF(rect.x() + 10, rect.bottom() - 14 - lh * len(lines) - 10, w, lh * len(lines) + 10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 170))
        p.drawRoundedRect(box, 8, 8)
        p.setPen(QColor(255, 255, 255, 230))
        for i, t in enumerate(lines):
            p.drawText(QRectF(box.x() + 8, box.y() + 5 + i * lh, w, lh), Qt.AlignLeft | Qt.AlignVCenter, t)

    def _toggle_stats(self):
        self.show_stats = not self.show_stats
        self.update()

    def _set_quality(self, width=None, height=None, fps=None):
        if width:
            self.settings["width"], self.settings["height"] = width, height
        if fps:
            self.settings["fps"] = fps
        self.settings.save()
        self._hint("Applies the next time the iPhone connects")

    def _paint_airplay_glyph(self, p, rect):
        s = rect.width() * 0.2
        cx, cy = rect.center().x(), rect.y() + rect.height() * 0.36
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 220), max(2.0, s * 0.07), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        top = cy - s * 0.5
        p.drawRoundedRect(QRectF(cx - s * 0.62, top, s * 1.24, s * 0.75), s * 0.08, s * 0.08)
        tri = QPainterPath()
        tri.moveTo(cx, cy + s * 0.05)
        tri.lineTo(cx + s * 0.3, cy + s * 0.45)
        tri.lineTo(cx - s * 0.3, cy + s * 0.45)
        tri.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawPath(tri)

    def _center_text(self, p, rect, title, sub):
        w = rect.width()
        p.setFont(font(max(11, int(w * 0.055)), True))
        p.setPen(QColor(255, 255, 255, 240))
        y = rect.y() + rect.height() * 0.5
        p.drawText(QRectF(rect.x() + w * 0.08, y, w * 0.84, w * 0.12), Qt.AlignHCenter | Qt.AlignTop, title)
        p.setFont(font(max(9, int(w * 0.034))))
        p.setPen(QColor(255, 255, 255, 170))
        p.drawText(
            QRectF(rect.x() + w * 0.1, y + w * 0.12, w * 0.8, rect.height() * 0.3),
            Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
            sub,
        )

    def _paint_touches(self, p, rect, r):
        """Touch feedback: ripples for taps / long presses, fading lines for swipes."""
        if not self._effects and self._g is None:
            return
        now = time.monotonic()

        def pt(f):
            return QPointF(rect.x() + f[0] * rect.width(), rect.y() + f[1] * rect.height())

        p.save()
        clip = QPainterPath()
        clip.addRoundedRect(rect, r, r)
        p.setClipPath(clip)
        for fx in self._effects:
            k = (now - fx["t"]) / fx["life"]
            if not 0 <= k < 1:
                continue
            fade = 1 - k
            if fx["kind"] == "swipe":
                a, b = pt(fx["a"]), pt(fx["b"])
                p.setPen(QPen(QColor(255, 255, 255, int(170 * fade)), 3 + 4 * fade, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(a, b)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, int(210 * fade)))
                p.drawEllipse(b, 3 + 4 * fade, 3 + 4 * fade)
            else:
                big = fx["kind"] == "long"
                radius = 10 + (34 if big else 20) * k
                p.setPen(QPen(QColor(255, 255, 255, int(220 * fade)), 2.5 if big else 2))
                p.setBrush(QColor(255, 255, 255, int((80 if big else 60) * fade)))
                p.drawEllipse(pt(fx["a"]), radius, radius)
        g = self._g
        if g is not None:  # finger down
            if g["moved"] and not g["done"]:
                p.setPen(QPen(QColor(255, 255, 255, 110), 3, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(g["pos0"], g["pos"])
            p.setPen(QPen(QColor(255, 255, 255, 150), 1.5))
            p.setBrush(QColor(255, 255, 255, 60))
            p.drawEllipse(g["pos"] if g["moved"] else g["pos0"], 11, 11)
        p.restore()

    # hover bar: [label .......... control  home  pin  -  x]
    def _bar_rect(self) -> QRectF:
        rect = self.phone_rect()
        top = rect.y() + 8 if self.fullscreen else SHADOW + 2
        return QRectF(rect.x() + 6, top, rect.width() - 12, BAR - 10)

    def _buttons(self):
        b = self._bar_rect()
        names = ("control", "home", "pin", "min", "close")
        s = min(b.height(), max(18.0, (b.width() - 40) / len(names)))
        y = b.center().y() - s / 2
        right = b.right() - max(0.0, (b.height() - s) / 2)
        return {n: QRectF(right - (len(names) - i) * s, y, s, s) for i, n in enumerate(names)}

    def _button_at(self, pos):
        for name, r in self._buttons().items():
            if r.contains(pos):
                return name
        return None

    def _control_status(self) -> str:
        st = self.control_state
        if self.ctrl is None or st == OFF:
            return ""
        if st == STARTING:
            return self.control_message.splitlines()[0] if self.control_message else "Starting control..."
        if st == READY:
            return "Control on"
        first = self.control_message.splitlines()[0] if self.control_message else ""
        return f"Control error: {first}" if first else "Control error"

    def _bar_labels(self) -> list:
        """Top bar label, most detailed first; the painter uses the first one that fits."""
        if self._hint_text and time.monotonic() < self._hint_until:
            return [self._hint_text]
        name = self.client or "iPhone"
        fps = f"{self.fps:.0f} fps" if self.state == "mirroring" and self.fps else ""
        status = self._control_status()
        rec = self._rec_label()
        sep = "  ·  "
        labels = [sep.join(x for x in (rec, name, fps, status) if x)]
        if fps:
            labels.append(sep.join(x for x in (rec, name, status) if x))
        if status:
            labels.append(sep.join(x for x in (rec, status) if x))
        if rec:
            labels.append(rec)
        return labels

    def _rec_label(self) -> str:
        rec = self.rx.recorder if self.rx else None
        if rec is None:
            return ""
        s = int(rec.seconds)
        return f"● REC {s // 60}:{s % 60:02d}"

    def _bar_label(self) -> str:
        return self._bar_labels()[0]

    def _control_color(self) -> QColor:
        st = self.control_state
        if st == READY:
            return QColor(GREEN)
        if st == STARTING:
            c = QColor(ORANGE)
            c.setAlphaF(0.35 + 0.65 * (0.5 + 0.5 * math.sin(time.monotonic() * 2 * math.pi / 1.1)))
            return c
        if st == ERROR:
            return QColor(RED)
        return QColor(255, 255, 255, 220)

    def _paint_bar(self, p):
        b = self._bar_rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(30, 30, 34, 225))
        p.drawRoundedRect(b, b.height() / 2, b.height() / 2)
        btn = self._buttons()

        bar_font = (9, True)
        p.setFont(font(*bar_font))
        text_rect = QRectF(b.x() + 14, b.y(), max(0.0, btn["control"].left() - b.x() - 18), b.height())
        labels = self._bar_labels()
        label = next((t for t in labels if text_width(*bar_font, t) <= text_rect.width()), None)
        if label is None:
            label = metrics(*bar_font).elidedText(labels[-1], Qt.ElideRight, int(text_rect.width()))
        p.setPen(QColor(255, 255, 255, 220))
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, label)

        s = btn["close"].width()
        k = s / 30  # glyph scale
        if self._hover_btn in btn:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 34))
            p.drawEllipse(btn[self._hover_btn].center(), s * 0.42, s * 0.42)

        self._paint_hand(p, btn["control"].center() + QPointF(0.8 * k, 0.4 * k), k * 0.95, self._control_color())

        white = QColor(255, 255, 255, 220)
        d = 4.5 * k
        c = btn["home"].center()
        home_on = self.control_state == READY
        p.setPen(QPen(white if home_on else QColor(255, 255, 255, 110), 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, 5.6 * k, 5.6 * k)

        pen = QPen(white, 1.6, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        c = btn["close"].center()
        p.drawLine(QPointF(c.x() - d, c.y() - d), QPointF(c.x() + d, c.y() + d))
        p.drawLine(QPointF(c.x() - d, c.y() + d), QPointF(c.x() + d, c.y() - d))
        c = btn["min"].center()
        p.drawLine(QPointF(c.x() - d, c.y()), QPointF(c.x() + d, c.y()))
        c = btn["pin"].center()
        on = self.settings.get("always_on_top", False)
        p.setBrush(white if on else Qt.NoBrush)
        p.drawEllipse(QPointF(c.x(), c.y() - 1.6 * k), 3.6 * k, 3.6 * k)
        p.drawLine(QPointF(c.x(), c.y() + 2.0 * k), QPointF(c.x(), c.y() + 6.4 * k))

    @staticmethod
    def _paint_hand(p, c, k, color):
        """Hand with a raised index finger (the 'control the iPhone' glyph)."""

        def rr(x, y, w, h, r):
            q = QPainterPath()
            q.addRoundedRect(QRectF(c.x() + x * k, c.y() + y * k, w * k, h * k), r * k, r * k)
            return q

        path = rr(-2.0, -9.0, 3.6, 10.0, 1.8)  # index finger
        path = path.united(rr(-4.4, -2.6, 10.4, 10.6, 3.2))  # palm with folded fingers
        path = path.united(rr(-7.6, 0.4, 5.0, 3.6, 1.8))  # thumb
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(path)
        p.setPen(QPen(QColor(30, 30, 34, 200), 1.0 * max(1.0, k)))
        for x in (1.8, 4.0):  # gaps between the folded fingers
            p.drawLine(QPointF(c.x() + x * k, c.y() - 2.2 * k), QPointF(c.x() + x * k, c.y() + 1.4 * k))

    def _bar_off(self):
        self.hover = False
        self._hover_btn = None
        self._update_anim()
        self.update()

    def _flash_bar(self, seconds=HINT_S):
        """Show the top bar for a moment (status changes, hints) even if the mouse is elsewhere."""
        self.hover = True
        if self.fullscreen or not self.underMouse():  # in full screen the mouse is always over us
            self._hide_bar.start(int(seconds * 1000))
        self._update_anim()
        self.update()

    def _hint(self, text):
        self._hint_text = text
        self._hint_until = time.monotonic() + HINT_S
        self._flash_bar()
        QTimer.singleShot(int(HINT_S * 1000) + 50, self.update)

    # ------------------------------------------------------------ animation
    def _needs_anim(self):
        return bool(self._effects) or (self.hover and self.control_state == STARTING)

    def _update_anim(self):
        if self._needs_anim() and not self._anim.isActive():
            self._anim.start()

    def _tick(self):
        now = time.monotonic()
        self._effects = [fx for fx in self._effects if now - fx["t"] < fx["life"]]
        if not self._needs_anim():
            self._anim.stop()
        self.update()

    def _add_effect(self, kind, a, b=None):
        life = {"tap": 0.45, "long": 0.7, "swipe": 0.5}[kind]
        self._effects.append({"kind": kind, "a": a, "b": b, "t": time.monotonic(), "life": life})
        self._update_anim()
        self.update()

    # ------------------------------------------------------------ iPhone control
    def _control_ready(self):
        return self.ctrl is not None and self.control_state == READY

    def _gestures_on(self):
        """Mouse input goes to the iPhone only while control is ready and its screen is shown."""
        return self._control_ready() and self.image is not None

    def _toggle_control(self):
        if self.ctrl is None:
            self._hint("iPhone control is not available")
        elif self.ctrl.active:  # the controller's own state: the shown one may lag behind
            self.ctrl.stop()
        else:
            self.ctrl.start()

    def _phone(self, method, *args):
        """Send a command (home, app_switcher, button) to the iPhone, or explain why not."""
        if not self._control_ready():
            if self.ctrl is None:
                self._hint("iPhone control is not available")
            elif self.control_state == STARTING:
                self._hint("iPhone control is still starting...")
            else:
                self._hint("Turn on iPhone control first (Ctrl+U)")
            return
        self._commit_composition()
        self._flush_tap()
        getattr(self.ctrl, method)(*args)

    def _paste(self):
        """Type the PC clipboard's text into the focused field on the iPhone."""
        text = QApplication.clipboard().text()
        if not text:
            self._hint("The clipboard has no text")
            return
        if len(text) > PASTE_MAX:
            text = text[:PASTE_MAX]
            self._hint(f"Only the first {PASTE_MAX} characters are pasted")
        self._flush_type()  # characters typed before the paste go first
        self._phone("type_text", text)

    def _gesture_begin(self, pos, double=False):
        self._g = {
            "pos0": QPointF(pos),
            "pos": QPointF(pos),
            "t0": time.monotonic(),
            "moved": False,
            "done": False,
            "double": double,  # second press of a double-click whose first click is still held back
        }
        self._long_timer.start()
        self.update()

    def _cancel_gesture(self):
        self._g = None
        self._long_timer.stop()
        if self._pending_tap is not None and not self._tap_timer.isActive():
            self._flush_tap()  # its double-click will not complete now

    def _flush_tap(self):
        """Send the held-back click as a single tap (no second click came in time)."""
        self._tap_timer.stop()
        a, self._pending_tap = self._pending_tap, None
        if a is not None and self._control_ready():
            self.ctrl.tap(*a)

    def _drop_tap(self):
        self._tap_timer.stop()
        self._pending_tap = None

    def _on_long_press(self):
        g = self._g
        if g is None or g["moved"] or g["done"] or not self._control_ready():
            return
        g["done"] = True
        self._flush_tap()  # a click before this press stays a tap of its own
        a = to_fraction(self.phone_rect(), g["pos0"])
        self.ctrl.long_press(*a)
        self._add_effect("long", a)

    def _gesture_end(self, pos):
        g, self._g = self._g, None
        self._long_timer.stop()
        if not self._control_ready():
            self._drop_tap()
            self.update()
            return
        if g["done"]:
            self.update()
            return
        rect = self.phone_rect()
        a = to_fraction(rect, g["pos0"])
        held = time.monotonic() - g["t0"]
        if g["moved"]:
            self._flush_tap()
            b = to_fraction(rect, pos)
            self.ctrl.swipe(a[0], a[1], b[0], b[1], swipe_seconds(held))
            self._add_effect("swipe", a, b)
        elif held >= LONG_PRESS_S:  # the timer did not get to run (busy event loop)
            self._flush_tap()
            self.ctrl.long_press(*a)
            self._add_effect("long", a)
        elif g["double"] and self._pending_tap is not None:
            first = self._pending_tap
            self._drop_tap()
            self.ctrl.double_tap(*first)  # both taps in one go, at the first click's position
            self._add_effect("tap", first)
        else:
            # hold the tap back briefly: a second click turns it into a double tap
            self._flush_tap()
            self._pending_tap = a
            self._tap_timer.start()
            self._add_effect("tap", a)

    def _flush_wheel(self):
        n, self._wheel_acc = self._wheel_acc, 0.0
        if abs(n) >= 0.05 and self._control_ready():
            self._flush_tap()  # keep the order: a click made before the scroll goes first
            self.ctrl.scroll(self._wheel_pos[0], self._wheel_pos[1], n)

    def _type(self, text):
        self._type_buf += text
        if not self._type_timer.isActive():
            self._type_timer.start()

    def _flush_type(self):
        text, self._type_buf = self._type_buf, ""
        if text and self._control_ready():
            self._flush_tap()  # the click that focused a text field must arrive before the text
            self.ctrl.type_text(text)

    def _update_cursor(self, pos):
        touch = (
            self._gestures_on()
            and self.phone_rect().contains(pos)
            and not (QApplication.keyboardModifiers() & Qt.AltModifier)
        )
        want = Qt.PointingHandCursor if touch else Qt.ArrowCursor
        if self.cursor().shape() != want:
            self.setCursor(want)

    # ------------------------------------------------------------ input
    def enterEvent(self, e):
        if self.fullscreen:
            return  # the window covers the screen: the bar follows the mouse (mouseMoveEvent)
        self._hide_bar.stop()
        self.hover = True
        self._update_anim()
        self.update()

    def leaveEvent(self, e):
        self._hide_bar.start(1200)
        if self._hover_btn:
            self._hover_btn = None
            self.update()

    def event(self, e):
        if e.type() == QEvent.ToolTip:
            name = self._button_at(QPointF(e.pos())) if self.hover else None
            if name:
                QToolTip.showText(e.globalPos(), self._button_tip(name), self)
            else:
                QToolTip.hideText()
                e.ignore()
            return True
        return super().event(e)

    def _button_tip(self, name):
        if name == "control":
            return {
                READY: "iPhone control is on - click to turn it off (Ctrl+U)",
                STARTING: "iPhone control is starting - click to cancel (Ctrl+U)",
                ERROR: "iPhone control failed - click to try again (Ctrl+U)",
            }.get(self.control_state, "Control iPhone over USB (Ctrl+U)")
        return {"home": "Home (Ctrl+H)", "pin": "Always on top", "min": "Minimize", "close": "Close"}[name]

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._phone("home")
            return
        if e.button() == Qt.BackButton:
            self._phone("back")
            return
        if e.button() != Qt.LeftButton:
            return
        pos = e.position()
        if self.hover:
            name = self._button_at(pos)
            if name:
                self._button(name)
                return
        alt = bool(e.modifiers() & Qt.AltModifier)
        if self._gestures_on() and not alt and self.phone_rect().contains(pos):
            self._commit_composition()
            self._gesture_begin(pos)
            return
        if not self.fullscreen:
            self.drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        pos = e.position()
        g = self._g
        if g is not None:
            g["pos"] = QPointF(pos)
            if not g["moved"] and not g["done"]:
                d = pos - g["pos0"]
                if math.hypot(d.x(), d.y()) > TAP_SLOP:
                    g["moved"] = True
                    self._long_timer.stop()
            self.update()
            return
        if self.drag_offset is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self.drag_offset)
            return
        if self.fullscreen:
            near = pos.y() <= self._bar_rect().bottom() + 24
            if near:
                self._hide_bar.stop()
            if near != self.hover:
                self.hover = near
                self._update_anim()
                self.update()
        name = self._button_at(pos) if self.hover else None
        if name != self._hover_btn:
            self._hover_btn = name
            self.update()
        self._update_cursor(pos)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self._g is not None:
            self._gesture_end(e.position())
            return
        if self.drag_offset is not None:
            self.drag_offset = None
            self._save_pos()

    def mouseDoubleClickEvent(self, e):
        if e.button() in (Qt.MiddleButton, Qt.BackButton):
            self.mousePressEvent(e)  # a quick second press is a press of its own
            return
        if e.button() != Qt.LeftButton:
            return
        pos = e.position()
        if self.hover and self._button_at(pos):
            return  # the first click already pressed the button
        alt = bool(e.modifiers() & Qt.AltModifier)
        if self._gestures_on() and not alt and self.phone_rect().contains(pos):
            # second press of a double-click. If the first click is still held back, both are
            # sent together as a double tap on release; if it already went out, this is a tap.
            double = self._tap_timer.isActive()
            self._tap_timer.stop()  # keep the first click until this press ends
            self._gesture_begin(pos, double=double)
            return
        if self.fullscreen:
            self.toggle_fullscreen()
        else:
            self._toggle_size()

    def _apply_zoom(self):
        """Resize by the Ctrl+wheel delta collected so far, then wait ZOOM_MS before the next step."""
        dy, self._zoom_acc = self._zoom_acc, 0
        if dy:
            self.set_phone_height(round(self.phone_h * ZOOM_PER_NOTCH ** (dy / 120)))
            self._zoom_timer.start()

    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if e.modifiers() & Qt.ControlModifier:
            if dy:
                self._zoom_acc += dy  # proportional: a touchpad pinch sends many small deltas
                if not self._zoom_timer.isActive():
                    self._apply_zoom()
            return
        if dy and self._gestures_on() and self.phone_rect().contains(e.position()):
            self._commit_composition()
            if not self._wheel_timer.isActive():
                self._wheel_pos = to_fraction(self.phone_rect(), e.position())
                self._wheel_timer.start()
            self._wheel_acc += dy / 120  # > 0: wheel rotated away from the user

    def inputMethodEvent(self, e):
        """Text composed by an input method: type what it commits (the preview is not sent)."""
        text = e.commitString()
        forced, self._ime_forced = self._ime_forced, None
        if text and text != forced and self._control_ready():
            self._type(text)
        self._preedit = e.preeditString()
        e.accept()

    def _commit_composition(self):
        """Before a tap, scroll, shortcut or paste: send the word the IME is still composing, so it
        lands in the field it was typed for, ahead of the action."""
        if self._preedit and self._control_ready():
            self._type(self._preedit)
            self._ime_forced, self._preedit = self._preedit, ""
            QGuiApplication.inputMethod().reset()  # end the composition (Windows may commit it: skipped)
        if self._type_buf:
            self._flush_type()

    def inputMethodQuery(self, query):
        if query == Qt.ImEnabled:
            return self._control_ready()
        if query == Qt.ImCursorRectangle:  # where the IME shows its candidate window
            r = self.phone_rect()
            return QRectF(r.x() + r.width() * 0.1, r.bottom() - r.height() * 0.4, 1, 20).toRect()
        return super().inputMethodQuery(query)

    def keyPressEvent(self, e):
        mods = e.modifiers()
        if e.key() == Qt.Key_F11 or (e.key() == Qt.Key_Escape and self.fullscreen):
            if not e.isAutoRepeat():
                self.toggle_fullscreen()
            return
        if (mods & Qt.ControlModifier) and not (mods & Qt.AltModifier):
            rep = e.isAutoRepeat()
            if is_key(e, (Qt.Key_Plus, Qt.Key_Equal), (VK_OEM_PLUS, VK_ADD)):
                self.set_phone_height(self.phone_h * 1.1)
            elif is_key(e, (Qt.Key_Minus,), (VK_OEM_MINUS, VK_SUBTRACT)):
                self.set_phone_height(self.phone_h / 1.1)
            elif is_key(e, (Qt.Key_Up,)):
                self._phone("button", "volumeUp")
            elif is_key(e, (Qt.Key_Down,)):
                self._phone("button", "volumeDown")
            elif rep:
                pass  # Home / App Switcher / toggles: once per key press
            elif is_key(e, (Qt.Key_H,), (VK_H,)):
                self._phone("home")
            elif is_key(e, (Qt.Key_J,), (VK_J,)):
                self._phone("app_switcher")
            elif is_key(e, (Qt.Key_M,), (VK_M,)):
                self._toggle_mute()
            elif is_key(e, (Qt.Key_N,), (VK_N,)) and mods & Qt.ShiftModifier:
                self._phone("control_center")
            elif is_key(e, (Qt.Key_N,), (VK_N,)):
                self._phone("notification_center")
            elif is_key(e, (Qt.Key_K,), (VK_K,)):
                self._phone("spotlight")
            elif is_key(e, (Qt.Key_L,), (VK_L,)):
                self._phone("lock")
            elif is_key(e, (Qt.Key_B,), (VK_B,)):
                self._phone("back")
            elif is_key(e, (Qt.Key_V,), (VK_V,)):
                self._paste()
            elif is_key(e, (Qt.Key_I,), (VK_I,)):
                self._toggle_stats()
            elif is_key(e, (Qt.Key_R,), (VK_R,)):
                self._toggle_recording()
            elif is_key(e, (Qt.Key_S,), (VK_S,)) and mods & Qt.ShiftModifier:
                self.copy_screenshot()
            elif is_key(e, (Qt.Key_S,), (VK_S,)):
                self.screenshot()
            elif is_key(e, (Qt.Key_U,), (VK_U,)):
                self._toggle_control()
            else:
                super().keyPressEvent(e)
            return
        if self._control_ready():
            text = key_text(e)
            if text:
                self._type(text)
                return
        super().keyPressEvent(e)

    def contextMenuEvent(self, e):
        self._cancel_gesture()
        m = QMenu(self)
        ready = self._control_ready()
        ctl = QAction(
            "Control iPhone (USB)\tCtrl+U", m, checkable=True, checked=self.control_state in (STARTING, READY)
        )
        ctl.setEnabled(self.ctrl is not None)
        ctl.triggered.connect(self._toggle_control)
        m.addAction(ctl)
        m.addAction("Set Up iPhone Control...", self.open_setup)
        for label, method, args in (
            ("Home\tCtrl+H", "home", ()),
            ("App Switcher\tCtrl+J", "app_switcher", ()),
            ("Back\tCtrl+B", "back", ()),
            ("Spotlight\tCtrl+K", "spotlight", ()),
            ("Notification Center\tCtrl+N", "notification_center", ()),
            ("Control Center\tCtrl+Shift+N", "control_center", ()),
            ("Lock Screen\tCtrl+L", "lock", ()),
            ("Volume Up\tCtrl+Up", "button", ("volumeUp",)),
            ("Volume Down\tCtrl+Down", "button", ("volumeDown",)),
        ):
            a = m.addAction(label, lambda method=method, args=args: self._phone(method, *args))
            a.setEnabled(ready)
        paste = m.addAction("Paste PC Clipboard\tCtrl+V", self._paste)
        paste.setEnabled(ready)
        m.addSeparator()
        top = QAction("Always on Top", m, checkable=True, checked=self.settings.get("always_on_top", False))
        top.triggered.connect(lambda: self._button("pin"))
        m.addAction(top)
        snd = QAction("Sound\tCtrl+M", m, checkable=True, checked=not (self.rx and self.rx.muted))
        snd.triggered.connect(self._toggle_mute)
        m.addAction(snd)
        fs = QAction("Full Screen\tF11", m, checkable=True, checked=self.fullscreen)
        fs.triggered.connect(self.toggle_fullscreen)
        m.addAction(fs)
        size = m.addMenu("Size")
        size.setEnabled(not self.fullscreen)
        quality = m.addMenu("Stream Quality")
        for label, w, h in QUALITIES:
            a = quality.addAction(label, lambda w=w, h=h: self._set_quality(w, h))
            a.setCheckable(True)
            a.setChecked(int(self.settings["height"]) == h)
        quality.addSeparator()
        for fps in FRAME_RATES:
            a = quality.addAction(f"{fps} fps", lambda fps=fps: self._set_quality(fps=fps))
            a.setCheckable(True)
            a.setChecked(int(self.settings["fps"]) == fps)
        stats = QAction("Show Stream Info\tCtrl+I", m, checkable=True, checked=self.show_stats)
        stats.triggered.connect(self._toggle_stats)
        m.addAction(stats)
        opacity = m.addMenu("Opacity")
        current = self.settings.get("opacity") or 1.0
        for v in OPACITIES:
            a = opacity.addAction(f"{v:.0%}", lambda v=v: self._set_opacity(v))
            a.setCheckable(True)
            a.setChecked(abs(current - v) < 0.01)
        awake = QAction("Keep PC Awake While Mirroring", m, checkable=True,
                        checked=bool(self.settings.get("keep_awake", True)))
        awake.triggered.connect(self._toggle_keep_awake)
        m.addAction(awake)
        boot = QAction("Start with Windows", m, checkable=True, checked=autostart.enabled())
        boot.triggered.connect(self._toggle_autostart)
        m.addAction(boot)
        screen = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        for label, k in (("Small", 0.5), ("Medium", 0.72), ("Large", 0.92)):
            size.addAction(label, lambda k=k: self.set_phone_height(screen.height() * k))
        m.addSeparator()
        m.addAction("Save Screenshot\tCtrl+S", self.screenshot)
        m.addAction("Copy Screenshot\tCtrl+Shift+S", self.copy_screenshot)
        recording = bool(self.rx and self.rx.recorder)
        rec = QAction("Record Screen\tCtrl+R", m, checkable=True, checked=recording)
        rec.setEnabled(self.rx is not None)
        rec.triggered.connect(self._toggle_recording)
        m.addAction(rec)
        m.addAction("Rename PC...", self._rename)
        vis = QAction("Visible in Screen Mirroring", m, checkable=True, checked=bool(self.rx and self.rx.advertised))
        vis.setEnabled(self.rx is not None)
        vis.triggered.connect(self._toggle_advertised)
        m.addAction(vis)
        m.addAction("Open Media Folder", self._open_media_folder)
        m.addAction("Open Log", self._open_log)
        m.addSeparator()
        m.addAction("Quit", QApplication.quit)
        m.exec(e.globalPos())

    def _button(self, name):
        if name == "close":
            QApplication.quit()
        elif name == "min":
            if self.fullscreen:
                self.toggle_fullscreen()
            self.showMinimized()
        elif name == "control":
            self._toggle_control()
        elif name == "home":
            self._phone("home")
        elif name == "pin":
            on = not self.settings.get("always_on_top", False)
            self.settings["always_on_top"] = on
            self.settings.save()
            pos = self.pos()
            self._apply_flags()
            self.move(pos)
            self.show()
        self.update()

    def _rename(self):
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "PC Name", "Name of this PC in Screen Mirroring on the iPhone:", text=self.settings["name"]
        )
        name = name.strip()
        if ok and name and self.rx:
            self.rx.rename(name)
            self.info = dict(self.info, name=name)
            self.update()

    def _toggle_advertised(self):
        if self.rx:
            self.rx.set_advertised(not self.rx.advertised)
            self._hint("Shown in Screen Mirroring" if self.rx.advertised else "Hidden from Screen Mirroring")
            self.update()

    def _toggle_mute(self):
        if self.rx:
            self.rx.set_muted(not self.rx.muted)
            self._hint("Sound off" if self.rx.muted else "Sound on")

    def _open_log(self):
        from .config import LOG_FILE

        if LOG_FILE.exists():
            os.startfile(str(LOG_FILE))

    def _frame_image(self):
        """The current frame at full resolution as a QImage, or None (with a hint) if there is none."""
        frame = getattr(self.rx.decoder, "last_frame", None) if self.rx else None
        if frame is None or self.image is None:
            self._hint("Nothing to capture yet")
            return None
        arr = frame.to_ndarray(format="bgra")
        return QImage(arr.data, arr.shape[1], arr.shape[0], arr.strides[0], QImage.Format_RGB32).copy()

    def screenshot(self):
        try:
            img = self._frame_image()
            if img is None:
                return
            folder = Path.home() / "Pictures" / APP_NAME
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / time.strftime("iPhone %Y-%m-%d %H-%M-%S.png")
            img.save(str(path))
            self._notify_saved("Screenshot saved", path)
        except Exception:
            log.exception("screenshot failed")

    def copy_screenshot(self):
        img = self._frame_image()
        if img is not None:
            QApplication.clipboard().setImage(img)
            self._hint("Screenshot copied to the clipboard")

    def _open_media_folder(self):
        for folder in (self._saved_folder, Path.home() / "Pictures" / APP_NAME):
            if folder is not None:
                folder.mkdir(parents=True, exist_ok=True)
                os.startfile(str(folder))
                return

    def _toggle_recording(self):
        if self.rx is None:
            return
        if self.rx.recorder is None:
            self.rx.start_recording(Path.home() / "Videos" / APP_NAME)
            self._rec_timer.start()
            self._hint("Recording - press Ctrl+R to stop")
            return
        # ponytail: stops on the GUI thread; the encoder drains at most ~3 s of queued frames
        # (Recorder.stop never blocks on a dead encoder)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            paths = self.rx.stop_recording()
        finally:
            QApplication.restoreOverrideCursor()
        self._rec_timer.stop()
        if paths:
            self._notify_saved("Recording saved", paths[-1])
        else:
            self._hint("Nothing was recorded")
        self.update()

    def _rec_tick(self):
        """REC clock; also notices an encoder that failed (disk full, folder not writable)."""
        rec = self.rx.recorder if self.rx else None
        if rec is not None and not rec.alive:
            error = rec.error or "the encoder stopped"
            self._toggle_recording()  # finishes what was written so far
            self._show_message("Recording stopped", f"Recording failed: {error}")
        self.update()

    def _show_message(self, title, text):
        if self._tray:
            self._tray.showMessage(title, text, app_icon(), 6000)
        else:
            self._hint(text)

    def _notify_saved(self, title, path):
        self._saved_folder = Path(path).parent
        if self._tray:
            self._tray.showMessage(title, f"{path}\nClick to open the folder", app_icon(), 4000)
        else:
            self._hint(title)

    def _open_saved_folder(self):
        if self._saved_folder and self._saved_folder.exists():
            os.startfile(str(self._saved_folder))

    def _save_pos(self):
        if self.fullscreen:
            return
        self.settings["x"], self.settings["y"] = self.x(), self.y()
        self.settings.save()

    def moveEvent(self, e):
        self._update_target()

    def closeEvent(self, e):
        self._save_pos()
        if self._awake:
            self._awake = False
            keep_awake(False)
        super().closeEvent(e)

    # ------------------------------------------------------------ tray
    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(app_icon(), self)
        tray.setToolTip(APP_NAME)
        menu = QMenu()
        menu.addAction("Show Window", self._show_front)
        menu.addAction("Hide Window", self.hide)
        menu.addAction("Quit", QApplication.quit)
        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason: self._show_front() if reason == QSystemTrayIcon.Trigger else None)
        tray.messageClicked.connect(self._open_saved_folder)
        tray.show()
        self._tray = tray
        self._tray_menu = menu  # the tray does not take ownership of the menu

    def _show_front(self):
        if self.fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()
        self.raise_()
        self.activateWindow()
