from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}


def iter_image_paths(input_path: str | Path) -> list[Path]:
    path = Path(input_path)
    if path.is_file():
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported image extension: {path.suffix}")
        return [path]
    if not path.exists():
        raise FileNotFoundError(path)
    images = [
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda item: item.as_posix().lower())


def load_grayscale(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        grayscale = image.convert("L")
    return np.asarray(grayscale, dtype=np.float32) / 255.0


def image_identifier(path: str | Path, root: str | Path | None = None) -> str:
    image_path = Path(path)
    if root is not None:
        root_path = Path(root)
        if root_path.is_dir():
            try:
                return image_path.relative_to(root_path).as_posix()
            except ValueError:
                pass
    return image_path.name


def condition_from_identifier(identifier: str) -> str:
    parts = [part for part in identifier.replace("\\", "/").split("/") if part]
    if len(parts) > 1:
        return parts[0]
    return "default"
