from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _host_target_triple() -> str:
    out = subprocess.check_output(["rustc", "-vV"], text=True)
    for line in out.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("Failed to read rust host target triple.")


def main() -> None:
    root = _repo_root()
    entry = root / "desktop_backend_entry.py"
    if not entry.exists():
        raise FileNotFoundError(f"Missing backend sidecar entry: {entry}")

    target = _host_target_triple()
    is_windows = "windows" in target
    sidecar_base = "mcube-backend"
    pyinstaller_name = f"{sidecar_base}.exe" if is_windows else sidecar_base

    dist_dir = root / ".tmp_sidecar_dist"
    work_dir = root / ".tmp_sidecar_build"
    spec_dir = root / ".tmp_sidecar_spec"
    for d in (dist_dir, work_dir, spec_dir):
        d.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        pyinstaller_name,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(spec_dir),
        str(entry),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    built_file = dist_dir / pyinstaller_name
    if not built_file.exists():
        raise FileNotFoundError(f"Expected built sidecar not found: {built_file}")

    binaries_dir = root / "frontend" / "src-tauri" / "binaries"
    binaries_dir.mkdir(parents=True, exist_ok=True)
    tauri_sidecar_name = f"{sidecar_base}-{target}{'.exe' if is_windows else ''}"
    out_file = binaries_dir / tauri_sidecar_name
    shutil.copy2(built_file, out_file)
    print(f"Sidecar ready: {out_file}")


if __name__ == "__main__":
    main()

