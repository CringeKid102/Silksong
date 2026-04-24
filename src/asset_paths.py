from pathlib import Path

from runtime_paths import images_path

# This module provides a function to resolve image asset paths within the "assets/images" directory.
_IMAGES_ROOT = Path(images_path())
_DIRECT_PATH_CACHE = {}
_NAME_INDEX = None


def _build_name_index():
    """
    Builds an index mapping lowercase filenames to their full paths for all images in the assets directory.
    Returns:
        dict: A dictionary mapping lowercase filenames to lists of their full paths.
    """
    global _NAME_INDEX
    if _NAME_INDEX is None:
        index = {}
        for path in _IMAGES_ROOT.rglob("*"):
            if path.is_file():
                index.setdefault(path.name.lower(), []).append(path)
        _NAME_INDEX = index
    return _NAME_INDEX


def resolve_image_path(relative_path: str) -> str:
    """
    Resolve the full path of an image asset given its relative path within the assets/images directory.
    Args:
        relative_path (str): The relative path to the image asset (e.g., "characters/hero.png").
    Returns:
        str: The full path to the image asset.
    """
    normalized = str(relative_path).replace("\\", "/").lstrip("/")
    cached_path = _DIRECT_PATH_CACHE.get(normalized)
    if cached_path is not None:
        return cached_path

    direct_path = (_IMAGES_ROOT / Path(normalized)).resolve()
    if direct_path.exists():
        resolved = str(direct_path)
        _DIRECT_PATH_CACHE[normalized] = resolved
        return resolved

    matches = _build_name_index().get(Path(normalized).name.lower(), [])
    if not matches:
        raise FileNotFoundError(f"Image asset not found: {relative_path}")

    if len(matches) > 1:
        normalized_suffix = normalized.lower()
        for match in matches:
            relative_match = match.relative_to(_IMAGES_ROOT).as_posix().lower()
            if relative_match.endswith(normalized_suffix):
                resolved = str(match)
                _DIRECT_PATH_CACHE[normalized] = resolved
                return resolved

    resolved = str(matches[0])
    _DIRECT_PATH_CACHE[normalized] = resolved
    return resolved