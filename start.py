"""One start command for Windows, macOS, and Linux.

The first run creates .venv and installs the packages in requirements.txt.
Later runs start the controller with that environment.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def venv_python(root: Path, platform: str) -> Path:
    """The interpreter inside .venv for this operating system."""
    base = Path(root) / ".venv"
    if platform == "win32":
        return base / "Scripts" / "python.exe"
    return base / "bin" / "python"


def ensure_environment(python: Path) -> None:
    if not python.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(python.parent.parent)])
    probe = subprocess.run(
        [str(python), "-c", "import flask, PIL"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if probe.returncode != 0:
        subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


def main() -> None:
    python = venv_python(ROOT, sys.platform)
    if python.exists() and Path(sys.executable).resolve() == python.resolve():
        from run import main as run_main

        run_main()
        return
    ensure_environment(python)
    raise SystemExit(subprocess.call([str(python), str(ROOT / "run.py")]))


if __name__ == "__main__":
    main()
