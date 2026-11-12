"""The local environment path is different on Windows than on macOS and Linux."""

import unittest
from pathlib import Path

from start import venv_python


class RuntimeTests(unittest.TestCase):
    def test_mac_and_linux_use_the_same_venv_layout(self):
        root = Path("/tmp/aquasentinel")
        mac = venv_python(root, "darwin")
        linux = venv_python(root, "linux")
        self.assertEqual(mac, linux)
        self.assertEqual(mac, root / ".venv" / "bin" / "python")

    def test_windows_uses_scripts(self):
        root = Path("/tmp/aquasentinel")
        self.assertEqual(venv_python(root, "win32"), root / ".venv" / "Scripts" / "python.exe")


if __name__ == "__main__":
    unittest.main()
