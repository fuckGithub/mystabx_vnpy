"""Create a QApplication and quit. Does not start the trader window."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication


def main() -> int:
    app = QApplication(sys.argv)
    platform = app.platformName()
    print(f"qt_platform={platform}")
    print(f"python={sys.version.split()[0]}")
    app.quit()
    if sys.platform == "darwin" and platform != "cocoa":
        print("expected cocoa on macOS", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
