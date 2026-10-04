"""Locate EVE logs without assuming Documents is in the default location."""
import os
from pathlib import Path


def windows_documents():
    """Ask Windows for Documents, including OneDrive and other redirects."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        lookup = ctypes.WinDLL("shell32", use_last_error=True).SHGetFolderPathW
        lookup.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HANDLE,
                           wintypes.DWORD, wintypes.LPWSTR]
        lookup.restype = ctypes.c_long
        buffer = ctypes.create_unicode_buffer(32768)
        # CSIDL_PERSONAL, SHGFP_TYPE_CURRENT: use Windows' current folder mapping.
        if lookup(None, 5, None, 0, buffer) == 0 and buffer.value:
            return Path(buffer.value)
    except (OSError, AttributeError):
        pass
    return None


def find_eve_log_path(subdir):
    home = Path.home()
    documents = windows_documents()
    candidates = []
    if documents is not None:
        candidates.append(documents / "EVE" / "logs" / subdir)
    candidates.append(home / "Documents" / "EVE" / "logs" / subdir)
    for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]) / "Documents" / "EVE" / "logs" / subdir)
    candidates.extend([
        home / ".eve" / "sharedcache" / "tq" / "logs" / subdir,
        home / ".local/share/Steam/steamapps/compatdata/8500/pfx/drive_c/users/steamuser/My Documents/EVE/logs" / subdir,
        Path("/mnt/ssd/SteamLibrary/steamapps/compatdata/8500/pfx/drive_c/users/steamuser/My Documents/EVE/logs") / subdir,
    ])
    return str(next((path for path in candidates if path.is_dir()), candidates[0]))
