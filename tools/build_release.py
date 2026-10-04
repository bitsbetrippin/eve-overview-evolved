"""Build the offline Windows x64 ZIP using official Python and pinned wheels."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from app_info import RELEASE_NAME
PYTHON_URL = "https://www.python.org/ftp/python/3.13.15/python-3.13.15-amd64.zip"
PYTHON_SHA256 = "6479223746cdfb79d25865110d6f524ac98de081324e119af1dc3ae36bddc7a5"
APP_FILES = (
    "app_info.py", "app_paths.py", "startup.py", "ratting.py", "eve_paths.py", "combat_meter.py", "window_placement.py", "neut_meter.py", "ewar_alerts.py",
    "battle_history.py", "requirements.txt", "requirements-windows.lock",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(output, cache, wheel_dir=None):
    if os.name != "nt":
        raise RuntimeError("Build this Windows runtime release on Windows.")
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "python-3.13.15-amd64.zip"
    if not archive.is_file() or sha256(archive) != PYTHON_SHA256:
        print("Downloading official Python runtime...", flush=True)
        pending = archive.with_suffix(".download")
        with urllib.request.urlopen(PYTHON_URL, timeout=60) as response, pending.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        if sha256(pending) != PYTHON_SHA256:
            raise RuntimeError("Python runtime checksum mismatch; build stopped.")
        pending.replace(archive)
    # Every build gets a new staging directory. User settings are never copied.
    build_root = ROOT / "build"
    build_root.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="release-", dir=build_root)) / RELEASE_NAME
    stage.mkdir()
    with zipfile.ZipFile(archive) as source:
        source.extractall(stage / "runtime")
    (stage / "app").mkdir()
    for name in ("START.bat", "README.md"):
        shutil.copy2(ROOT / name, stage / name)
    for name in APP_FILES:
        shutil.copy2(ROOT / "app" / name, stage / "app" / name)
    shutil.copytree(ROOT / "app/assets", stage / "app/assets")
    shutil.copytree(ROOT / "docs", stage / "docs")
    python = stage / "runtime/python.exe"
    package_source = ["--no-index", "--find-links", str(wheel_dir)] if wheel_dir else []
    subprocess.run([
        str(python), "-I", "-m", "pip", "install", "--disable-pip-version-check",
        "--no-warn-script-location", "--no-compile", "--only-binary=:all:",
        "--require-hashes", "-r", str(ROOT / "app/requirements-windows.lock"), *package_source,
    ], check=True)
    subprocess.run([str(python), "-I", "-B", str(stage / "app/startup.py"), "--self-test"], check=True)
    # Validate real GUI construction with synthetic/empty data before packaging.
    for test_file in ("test_release.py", "test_combat.py", "test_panels.py", "test_neuts.py", "test_ewar.py", "test_battles.py"):
        subprocess.run([str(python), "-I", "-B", str(ROOT / "tests" / test_file),
                        "--app", str(stage)], check=True)
    package = output / (RELEASE_NAME + ".zip")
    pending = package.with_suffix(".zip.partial")
    assert {p.name for p in stage.iterdir() if p.is_file()} == {"START.bat", "README.md"}
    assert not any(p.is_file() for p in (stage / "data").rglob("*")), "Personal data must not be packaged"
    with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as result:
        for folder in ("data", "data/cache", "data/logs", "data/battles"):
            result.write(stage / folder, (Path(RELEASE_NAME) / folder).as_posix() + "/")
        for path in sorted(stage.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                result.write(path, path.relative_to(stage.parent))
    pending.replace(package)
    package.with_suffix(".zip.sha256").write_text(sha256(package) + "  " + package.name + "\n")
    print(f"Release ready: {package}")
    return package


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--cache", type=Path, default=ROOT / "build/downloads")
    parser.add_argument("--wheel-dir", type=Path, help="Use a local wheel cache without accessing PyPI")
    args = parser.parse_args()
    build(args.output.resolve(), args.cache.resolve(), args.wheel_dir.resolve() if args.wheel_dir else None)
