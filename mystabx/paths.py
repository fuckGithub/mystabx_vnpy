"""Project paths. Create .vntrader before any vnpy import."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADER_FOLDER = PROJECT_ROOT / ".vntrader"


def ensure_project_trader_dir() -> Path:
    """Make cwd/.vntrader exist so vnpy binds TRADER_DIR here, not $HOME."""
    TRADER_FOLDER.mkdir(parents=True, exist_ok=True)
    return TRADER_FOLDER
