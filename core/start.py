"""uv / console entry: exec repo-root start.sh (Mac/Linux). Does not start uvicorn itself."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    script = root / "start.sh"
    if not script.is_file():
        raise SystemExit(f"missing {script}")
    os.chdir(root)
    os.execv("/bin/bash", ["/bin/bash", str(script), *sys.argv[1:]])


if __name__ == "__main__":
    main()
