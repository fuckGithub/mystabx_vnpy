"""Optional leftover Qt smoke. Default deps do not include PySide6."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 not installed (Web-only deps). Skip Qt smoke.",
            file=sys.stderr,
        )
        return 0

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
