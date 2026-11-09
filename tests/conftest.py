"""Pytest configuration and python path setup."""

import sys
from pathlib import Path

# Add 'cli' and root directory to python sys.path
root_dir = Path(__file__).resolve().parent.parent
cli_dir = root_dir / "cli"

if str(cli_dir) not in sys.path:
    sys.path.insert(0, str(cli_dir))

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
