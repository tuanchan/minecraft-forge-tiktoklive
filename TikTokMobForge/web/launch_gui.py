"""Windowed entry point with visible startup errors and a persistent log."""
from pathlib import Path
import ctypes
import os
import runpy
import sys
import traceback


def main():
    root = Path(__file__).resolve().parent
    log_path = root.parent / "GUI" / "logs" / "gui_startup.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", buffering=1) as log:
            sys.stdout = sys.stderr = log
            sys.path.insert(0, str(root))
            try:
                runpy.run_path(str(root / "main.py"), run_name="__main__")
            except Exception:
                traceback.print_exc()
                raise
    except Exception as error:
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(
                None,
                f"Không mở được bảng điều khiển LIVE: {error}\n\nLog lỗi: {log_path}",
                "Lỗi mở TikTok Mob", 0x10,
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
