"""Click only the installed Engine's read-only upper-right discovery refresh button."""

import ctypes
import time
from ctypes import wintypes
from pathlib import Path

from cc2_mce.installation import find_installations

user = ctypes.WinDLL("user32", use_last_error=True)
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
if hasattr(user, "SetProcessDpiAwarenessContext"):
    user.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))


class Rect(ctypes.Structure):
    _fields_ = [(key, wintypes.LONG) for key in ("left", "top", "right", "bottom")]


class Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user.FindWindowW.restype = wintypes.HWND
user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(Rect)]
user.EnumChildWindows.argtypes = [wintypes.HWND, callback, wintypes.LPARAM]
user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user.SetForegroundWindow.argtypes = [wintypes.HWND]
user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user.GetAncestor.restype = wintypes.HWND
user.WindowFromPoint.argtypes = [Point]
user.WindowFromPoint.restype = wintypes.HWND
user.GetCursorPos.argtypes = [ctypes.POINTER(Point)]
user.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
hwnd = user.FindWindowW(None, "CC2 Engine")
assert hwnd, "No Engine window"
pid = wintypes.DWORD()
user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
handle = kernel.OpenProcess(0x1000, False, pid.value)
assert handle
try:
    path = ctypes.create_unicode_buffer(32768)
    size = wintypes.DWORD(len(path))
    assert kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size))
    assert Path(path.value) == find_installations().games[0].root / "CC2Engine.exe"
finally:
    kernel.CloseHandle(handle)
outer = Rect()
assert user.GetWindowRect(hwnd, ctypes.byref(outer))
candidates = []


@callback
def visit(child, _):
    rect = Rect()
    if user.GetWindowRect(child, ctypes.byref(rect)):
        if (70 <= rect.right - rect.left <= 150 and 18 <= rect.bottom - rect.top <= 40
                and 90 <= rect.top - outer.top <= 220 and 10 <= outer.right - rect.right <= 40):
            candidates.append((child, rect))
    return True


user.EnumChildWindows(hwnd, visit, 0)
assert len(candidates) == 1, f"Refresh button not unambiguous: {len(candidates)}"
child, rect = candidates[0]
assert user.SetForegroundWindow(hwnd)
time.sleep(0.2)
point = Point((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
assert user.GetAncestor(user.WindowFromPoint(point), 2) == hwnd
original = Point()
assert user.GetCursorPos(ctypes.byref(original))
try:
    user.SetCursorPos(point.x, point.y)
    user.mouse_event(2, 0, 0, 0, 0)
    time.sleep(0.05)
    user.mouse_event(4, 0, 0, 0, 0)
    time.sleep(0.5)
finally:
    user.SetCursorPos(original.x, original.y)
print("Clicked Engine discovery refresh; no application was closed")
