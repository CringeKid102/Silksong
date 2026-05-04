from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "Silksong"


def _bundle_root() -> Path:
    """
    Return the root directory for bundled assets.
    Returns:
        Path: PyInstaller _MEIPASS when frozen, otherwise the project root.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def bundled_path(*parts: str) -> str:
    """
    Join parts onto the bundle root and return the absolute string path.
    Args:
        *parts (str): Path components to join.
    Returns:
        str: Absolute path string.
    """
    return str(_bundle_root().joinpath(*parts))


def assets_path(*parts: str) -> str:
    """
    Return the absolute path to a file inside the assets directory.
    Args:
        *parts (str): Path components relative to the assets folder.
    Returns:
        str: Absolute path string.
    """
    return bundled_path("assets", *parts)


def images_path(*parts: str) -> str:
    """
    Return the absolute path to a file inside the assets/images directory.
    Args:
        *parts (str): Path components relative to the images folder.
    Returns:
        str: Absolute path string.
    """
    return assets_path("images", *parts)


def user_data_dir() -> Path:
    """
    Return the platform-appropriate user data directory for the application.
    Returns:
        Path: User data directory path (LOCALAPPDATA on Windows, ~/.appname elsewhere).
    """
    if os.name == "nt":
        base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base_dir:
            return Path(base_dir) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def ensure_user_data_dir() -> Path:
    """
    Create the user data directory if it does not exist and return it.
    Returns:
        Path: The user data directory path.
    """
    data_dir = user_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def user_data_file(name: str) -> str:
    """
    Return the absolute path for a named file inside the user data directory.
    Args:
        name (str): Filename to resolve inside the user data directory.
    Returns:
        str: Absolute path string.
    """
    return str(ensure_user_data_dir() / name)