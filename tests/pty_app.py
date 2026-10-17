"""Run pqcli in a pseudo-terminal and read its screen through pyte.

Only works on POSIX: it needs pty.fork and the termios ioctls.
"""

import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios
import time
from collections.abc import Callable
from pathlib import Path

import pyte

ROWS = 40
COLS = 120
TIMEOUT = 10.0
# a pause in the output this long means a frame is complete
QUIET = 0.03
# or a match that keeps holding this long while output goes on
STABLE = 0.1

# What the keys send with TERM=xterm-256color once curses has switched
# the keypad to application mode.
ENTER = "\n"
ESC = "\x1b"
TAB = "\t"
BACKSPACE = "\x7f"
CTRL_W = "\x17"
CTRL_T = "\x14"
UP = "\x1bOA"
DOWN = "\x1bOB"
RIGHT = "\x1bOC"
LEFT = "\x1bOD"
PAGE_UP = "\x1b[5~"
PAGE_DOWN = "\x1b[6~"
F5 = "\x1b[15~"
F6 = "\x1b[17~"
F10 = "\x1b[21~"


def _set_size(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


class PtyApp:
    """A pqcli process attached to a pty, rendered into a pyte screen."""

    def __init__(
        self,
        config: Path,
        *args: str,
        rows: int = ROWS,
        cols: int = COLS,
        cwd: Path | None = None,
    ) -> None:
        self.screen = pyte.Screen(cols, rows)
        self._stream = pyte.ByteStream(self.screen)
        self.exit_status: int | None = None
        self._lines: list[str] | None = None

        env = {
            **os.environ,
            "XDG_CONFIG_HOME": str(config),
            "TERM": "xterm-256color",
            # draw boxes with Unicode lines; pyte ignores the DEC line
            # drawing charset and would show them as letters
            "NCURSES_NO_UTF8_ACS": "1",
        }
        # LINES/COLUMNS would override the pty size seen by curses.
        env.pop("LINES", None)
        env.pop("COLUMNS", None)
        argv = [sys.executable, "-m", "pqcli", *args]

        pid, fd = pty.fork()
        if pid == 0:  # pragma: no cover - runs in the child
            try:
                _set_size(0, rows, cols)
                if cwd is not None:
                    os.chdir(cwd)
                os.execve(sys.executable, argv, env)
            finally:
                os._exit(127)
        self.pid = pid
        self.fd = fd

    # reading ---------------------------------------------------------

    def _pump(self, timeout: float) -> bool | None:
        """Feed pending output to the screen.

        Returns True if output arrived, False if there was none within
        timeout, None once the pty is closed.
        """
        if self.fd < 0:
            return None
        ready, _, _ = select.select([self.fd], [], [], timeout)
        if not ready:
            return False
        try:
            chunk = os.read(self.fd, 65536)
        except OSError:  # EIO: the child closed its end
            chunk = b""
        if not chunk:
            os.close(self.fd)
            self.fd = -1
            return None
        self._stream.feed(chunk)
        self._lines = None
        return True

    @property
    def lines(self) -> list[str]:
        """The screen's rows; cached, as pyte builds them slowly."""
        if self._lines is None:
            self._lines = self.screen.display
        return self._lines

    def screen_text(self) -> str:
        return "\n".join(line.rstrip() for line in self.lines)

    def wait_until(
        self,
        predicate: Callable[[str], bool],
        timeout: float = TIMEOUT,
        what: str = "condition",
    ) -> str:
        """Wait until predicate holds for a screen that is done drawing.

        A frame arrives in several reads, so a match only counts once it
        survives a pause of QUIET seconds in the output, or, while the
        game view keeps drawing, once it has held for STABLE seconds.
        """
        deadline = time.monotonic() + timeout
        matched_since: float | None = None
        while True:
            now = time.monotonic()
            if now >= deadline:
                raise AssertionError(
                    f"timed out waiting for {what}; screen:\n"
                    + self.screen_text()
                )
            if not predicate(self.screen_text()):
                matched_since = None
            elif matched_since is None:
                matched_since = now
            got = self._pump(
                min(deadline - now, 0.05 if matched_since is None else QUIET)
            )
            text = self.screen_text()
            if got is None:
                if predicate(text):
                    return text
                raise AssertionError(
                    f"pqcli exited while waiting for {what}; screen:\n" + text
                )
            if matched_since is not None and predicate(text):
                if not got or time.monotonic() - matched_since >= STABLE:
                    return text

    def wait_for(self, text: str, timeout: float = TIMEOUT) -> str:
        return self.wait_until(lambda s: text in s, timeout, repr(text))

    def wait_gone(self, text: str, timeout: float = TIMEOUT) -> str:
        return self.wait_until(
            lambda s: text not in s, timeout, f"{text!r} to go away"
        )

    def row_of(self, text: str) -> int:
        for y, line in enumerate(self.lines):
            if text in line:
                return y
        raise AssertionError(f"{text!r} not on screen:\n{self.screen_text()}")

    def is_reverse(self, text: str) -> bool:
        """Whether the first cell of text on screen is drawn highlighted."""
        y = self.row_of(text)
        x = self.lines[y].index(text)
        return bool(self.screen.buffer[y][x].reverse)

    # writing ---------------------------------------------------------

    def send(self, keys: str) -> None:
        os.write(self.fd, keys.encode())

    def resize(self, rows: int, cols: int) -> None:
        self.screen.resize(rows, cols)
        self._lines = None
        _set_size(self.fd, rows, cols)
        os.kill(self.pid, signal.SIGWINCH)

    # lifetime --------------------------------------------------------

    def wait_exit(self, timeout: float = TIMEOUT) -> int:
        """Wait for the process to end and return its exit code."""
        deadline = time.monotonic() + timeout
        while self.exit_status is None:
            # keep draining so the child never blocks on a full pty
            self._pump(0.02)
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                self.exit_status = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() > deadline:
                raise AssertionError(
                    f"pqcli did not exit; screen:\n{self.screen_text()}"
                )
        while self._pump(0) is not None:
            pass
        return self.exit_status

    def close(self) -> None:
        if self.exit_status is None:
            # SIGINT runs the app's own handler, so it exits cleanly and
            # coverage gets to write its data.
            os.kill(self.pid, signal.SIGINT)
            try:
                self.wait_exit(5)
            except AssertionError:
                os.kill(self.pid, signal.SIGKILL)
                self.wait_exit(5)
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1
