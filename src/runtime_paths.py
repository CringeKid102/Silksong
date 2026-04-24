from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "Silksong"


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def bundled_path(*parts: str) -> str:
    return str(_bundle_root().joinpath(*parts))


def assets_path(*parts: str) -> str:
    return bundled_path("assets", *parts)


def images_path(*parts: str) -> str:
    return assets_path("images", *parts)


def user_data_dir() -> Path:
    if os.name == "nt":
        base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base_dir:
            return Path(base_dir) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def ensure_user_data_dir() -> Path:
    data_dir = user_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def user_data_file(name: str) -> str:
    return str(ensure_user_data_dir() / name)