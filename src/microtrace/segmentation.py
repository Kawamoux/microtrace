from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SegmentationResult:
    threshold: float
    mask: np.ndarray
    labels: np.ndarray
    object_count: int


def otsu_threshold(image: np.ndarray, bins: int = 256) -> float:
    values = np.asarray(image, dtype=np.float32)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError("Cannot threshold an empty image.")

    hist, edges = np.histogram(np.clip(values, 0.0, 1.0), bins=bins, range=(0.0, 1.0))
    probabilities = hist.astype(np.float64)
    total_count = probabilities.sum()
    if total_count == 0:
        return 0.5

    probabilities /= total_count
    centers = (edges[:-1] + edges[1:]) * 0.5
    weight_background = np.cumsum(probabilities)
    weight_foreground = 1.0 - weight_background
    mean_background = np.cumsum(probabilities * centers)
    total_mean = mean_background[-1]

    numerator = (total_mean * weight_background - mean_background) ** 2
    denominator = weight_background * weight_foreground
    score = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
    best_score = float(score.max())
    best_centers = centers[np.isclose(score, best_score, rtol=1e-12, atol=1e-12)]
    return float(best_centers.mean())


def segment_image(
    image: np.ndarray,
    *,
    threshold: float | str = "otsu",
    min_size: int = 32,
    invert: bool = False,
) -> SegmentationResult:
    if min_size < 1:
        raise ValueError("min_size must be at least 1.")
    threshold_value = otsu_threshold(image) if threshold == "otsu" else float(threshold)
    if not 0.0 <= threshold_value <= 1.0:
        raise ValueError("threshold must be between 0 and 1.")

    mask = np.asarray(image >= threshold_value, dtype=bool)
    if invert:
        mask = ~mask
    labels, object_count = label_components(mask, min_size=min_size)
    return SegmentationResult(threshold_value, mask, labels, object_count)


def label_components(mask: np.ndarray, *, min_size: int = 1) -> tuple[np.ndarray, int]:
    binary = np.asarray(mask, dtype=bool)
    height, width = binary.shape
    labels = np.zeros((height, width), dtype=np.int32)
    current_label = 0

    for start_y, start_x in zip(*np.nonzero(binary)):
        if labels[start_y, start_x] != 0:
            continue

        stack = [(int(start_y), int(start_x))]
        labels[start_y, start_x] = -1
        pixels: list[tuple[int, int]] = []

        while stack:
            y, x = stack.pop()
            pixels.append((y, x))
            for ny in range(max(0, y - 1), min(height, y + 2)):
                for nx in range(max(0, x - 1), min(width, x + 2)):
                    if ny == y and nx == x:
                        continue
                    if binary[ny, nx] and labels[ny, nx] == 0:
                        labels[ny, nx] = -1
                        stack.append((ny, nx))

        if len(pixels) >= min_size:
            current_label += 1
            for y, x in pixels:
                labels[y, x] = current_label
        else:
            for y, x in pixels:
                labels[y, x] = 0

    return labels, current_label
