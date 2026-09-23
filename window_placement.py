"""Keep overlay windows reachable on the monitor containing the overview."""
import os


def work_areas(window):
    areas = []
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class MonitorInfo(ctypes.Structure):
                _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                            ("work", wintypes.RECT), ("flags", wintypes.DWORD)]

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE,
                                               wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                               wintypes.LPARAM)
            user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
            user32.GetMonitorInfoW.restype = wintypes.BOOL
            user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                                   callback_type, wintypes.LPARAM]
            user32.EnumDisplayMonitors.restype = wintypes.BOOL

            @callback_type
            def collect(monitor, dc, rect, data):
                info = MonitorInfo()
                info.size = ctypes.sizeof(info)
                if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    area = info.work
                    areas.append((area.left, area.top, area.right, area.bottom))
                return True

            user32.EnumDisplayMonitors(None, None, collect, 0)
        except (OSError, AttributeError):
            pass
    return areas or [(0, 0, window.winfo_screenwidth(), window.winfo_screenheight())]


def title_visible(rect, areas):
    x, y, width, height = rect
    return any(y >= top and y + min(28, height) <= bottom
               and min(x + width, right) - max(x, left) >= min(80, width)
               for left, top, right, bottom in areas)


def position_near(anchor, size, areas, index=0):
    ax, ay, aw, ah = anchor
    cx, cy = ax + aw / 2, ay + min(ah, 28) / 2

    def distance(area):
        left, top, right, bottom = area
        return max(left - cx, 0, cx - right) ** 2 + max(top - cy, 0, cy - bottom) ** 2

    left, top, right, bottom = min(areas, key=distance)
    width, height = size
    offset = (index % 8) * 28
    x, y = ax + aw + 12 + offset, ay + offset
    if x + width > right:
        x = ax - width - 12 - offset
    # The title remains reachable even when the panel is taller than a monitor.
    return max(left, min(x, right - width)), max(top, min(y, bottom - height))


def rectangle(window):
    window.update_idletasks()
    return (window.winfo_x(), window.winfo_y(), window.winfo_width(), window.winfo_height())


def move_near(window, anchor, index=0):
    rect = rectangle(window)
    x, y = position_near(rectangle(anchor), rect[2:], work_areas(anchor), index)
    # A leading '+' followed by a signed coordinate is an absolute Tk offset,
    # so monitors left/above the primary display retain negative coordinates.
    window.geometry(f"+{x}+{y}")
    window.update_idletasks()


def recover_if_offscreen(window, anchor, index=0):
    if not title_visible(rectangle(window), work_areas(anchor)):
        move_near(window, anchor, index)
        return True
    return False
