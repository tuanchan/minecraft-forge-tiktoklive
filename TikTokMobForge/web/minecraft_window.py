"""Read Minecraft's client area without moving or changing its window."""
import ctypes
from ctypes import wintypes
import sys


def minecraft_viewport() -> dict:
    fallback = {"width": 1920, "height": 1080, "detected": False}
    if sys.platform != "win32":
        return fallback
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    matches = []

    @callback_type
    def visit(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, len(title))
        if not title.value.startswith("Minecraft"):
            return True
        window_class = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hwnd, window_class, len(window_class))
        if window_class.value not in {"GLFW30", "LWJGL"}:
            return True
        rect = wintypes.RECT()
        if user32.GetClientRect(hwnd, ctypes.byref(rect)):
            width, height = rect.right - rect.left, rect.bottom - rect.top
            if width >= 320 and height >= 200:
                matches.append((width, height))
        return True

    user32.EnumWindows(visit, 0)
    if not matches:
        return fallback
    width, height = max(matches, key=lambda size: size[0] * size[1])
    return {"width": width, "height": height, "detected": True}
