"""Start the project's portable VOICEVOX engine on demand (Windows)."""
import contextlib
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import urllib.parse


RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
_lock = threading.Lock()


def is_listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def engine_path() -> Path | None:
    if not (RUNTIME / "voicevox" / ".installed-0.25.2").is_file():
        return None
    candidates = sorted((RUNTIME / "voicevox").rglob("run.exe"), key=lambda path: len(path.parts))
    return candidates[0] if candidates else None


@contextlib.contextmanager
def startup_lock(deadline: float):
    # The web panel and bridge run in separate processes. Windows releases this
    # byte lock even if its owner exits unexpectedly.
    import msvcrt
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with _lock, (RUNTIME / "voicevox-start.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError("VOICEVOX đang khởi động ở tiến trình khác. Thử lại sau vài giây.")
                time.sleep(0.25)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def ensure_running(base_url: str) -> None:
    parsed = urllib.parse.urlsplit(base_url)
    host, port = parsed.hostname, parsed.port or 80
    if is_listening(host, port):
        return
    executable = engine_path()
    if executable is None:
        raise ValueError("Chưa cài engine VOICEVOX. Chạy CAI_VOICEVOX.bat trong thư mục dự án, rồi bấm Tải giọng / Test lại.")
    deadline = time.monotonic() + 60
    with startup_lock(deadline):
        if is_listening(host, port):
            return
        print(f"Đang tự khởi động VOICEVOX CPU tại {host}:{port}...", flush=True)
        log_path = RUNTIME / "voicevox-engine.log"
        with log_path.open("ab") as output:
            process = subprocess.Popen(
                [str(executable), "--host", host, "--port", str(port)],
                cwd=executable.parent, stdout=output, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise ValueError(f"VOICEVOX thoát với mã {process.returncode}. Xem {log_path}")
            if is_listening(host, port):
                print(f"VOICEVOX đã sẵn sàng (PID {process.pid}).", flush=True)
                return
            time.sleep(0.25)
        raise ValueError(f"VOICEVOX chưa sẵn sàng sau 60 giây. Xem {log_path}; chờ rồi bấm Test lại.")
