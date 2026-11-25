"""Shared resource root, independent of the current working directory."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
