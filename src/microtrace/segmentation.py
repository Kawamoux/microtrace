from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image, ImageFilter


SegmentationMode = Literal["intensity", "brightfield"]


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
    mode: SegmentationMode = "intensity",
    background_radius: float = 18.0,
    smooth_radius: float = 1.0,
    close_iterations: int = 2,
    fill_holes: bool = True,
    solidify: bool = True,
) -> SegmentationResult:
    if min_size < 1:
        raise ValueError("min_size must be at least 1.")
    if close_iterations < 0:
        raise ValueError("close_iterations must not be negative.")
    if mode not in {"intensity", "brightfield"}:
        raise ValueError("mode must be 'intensity' or 'brightfield'.")

    source = _brightfield_response(
        image,
        background_radius=background_radius,
        smooth_radius=smooth_radius,
    ) if mode == "brightfield" else np.asarray(image, dtype=np.float32)

    threshold_value = otsu_threshold(source) if threshold == "otsu" else float(threshold)
    if not 0.0 <= threshold_value <= 1.0:
        raise ValueError("threshold must be between 0 and 1.")

    mask = np.asarray(source >= threshold_value, dtype=bool)
    if invert and mode == "intensity":
        mask = ~mask
    if mode == "brightfield":
        if solidify:
            mask = _binary_opening(mask, iterations=1)
            mask = _solidify_components(mask, min_component_size=max(8, min_size // 5))
            mask = _binary_opening(mask, iterations=1)
            if fill_holes:
                mask = _fill_holes(mask)
        else:
            mask = _binary_closing(mask, iterations=close_iterations)
            if fill_holes:
                mask = _fill_holes(mask)
            mask = _binary_opening(mask, iterations=1)
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


def _brightfield_response(
    image: np.ndarray,
    *,
    background_radius: float,
    smooth_radius: float,
) -> np.ndarray:
    values = np.asarray(image, dtype=np.float32)
    background = _blur_array(values, radius=background_radius)
    response = np.maximum(background - values, 0.0)
    response = _blur_array(response, radius=smooth_radius)
    return _normalize(response)


def _blur_array(image: np.ndarray, *, radius: float) -> np.ndarray:
    if radius <= 0:
        return np.asarray(image, dtype=np.float32)
    scaled = np.round(np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)
    blurred = Image.fromarray(scaled).filter(ImageFilter.GaussianBlur(radius=float(radius)))
    return np.asarray(blurred, dtype=np.float32) / 255.0


def _normalize(image: np.ndarray) -> np.ndarray:
    low, high = np.percentile(image, [1.0, 99.5])
    if high <= low:
        return np.zeros_like(image, dtype=np.float32)
    return np.clip((image - low) / (high - low), 0.0, 1.0).astype(np.float32)


def _binary_closing(mask: np.ndarray, *, iterations: int) -> np.ndarray:
    if iterations == 0:
        return np.asarray(mask, dtype=bool)
    return _binary_erosion(_binary_dilation(mask, iterations=iterations), iterations=iterations)


def _binary_opening(mask: np.ndarray, *, iterations: int) -> np.ndarray:
    if iterations == 0:
        return np.asarray(mask, dtype=bool)
    return _binary_dilation(_binary_erosion(mask, iterations=iterations), iterations=iterations)


def _binary_dilation(mask: np.ndarray, *, iterations: int) -> np.ndarray:
    result = np.asarray(mask, dtype=bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        grown = np.zeros_like(result, dtype=bool)
        for y_offset in range(3):
            for x_offset in range(3):
                grown |= padded[y_offset : y_offset + result.shape[0], x_offset : x_offset + result.shape[1]]
        result = grown
    return result


def _binary_erosion(mask: np.ndarray, *, iterations: int) -> np.ndarray:
    result = np.asarray(mask, dtype=bool)
    for _ in range(iterations):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        shrunken = np.ones_like(result, dtype=bool)
        for y_offset in range(3):
            for x_offset in range(3):
                shrunken &= padded[y_offset : y_offset + result.shape[0], x_offset : x_offset + result.shape[1]]
        result = shrunken
    return result


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    foreground = np.asarray(mask, dtype=bool)
    background = ~foreground
    height, width = foreground.shape
    seen = np.zeros_like(foreground, dtype=bool)
    stack: list[tuple[int, int]] = []

    for x in range(width):
        if background[0, x]:
            stack.append((0, x))
            seen[0, x] = True
        if background[height - 1, x] and not seen[height - 1, x]:
            stack.append((height - 1, x))
            seen[height - 1, x] = True
    for y in range(height):
        if background[y, 0] and not seen[y, 0]:
            stack.append((y, 0))
            seen[y, 0] = True
        if background[y, width - 1] and not seen[y, width - 1]:
            stack.append((y, width - 1))
            seen[y, width - 1] = True

    while stack:
        y, x = stack.pop()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and background[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                stack.append((ny, nx))

    holes = background & ~seen
    return foreground | holes


def _solidify_components(mask: np.ndarray, *, min_component_size: int) -> np.ndarray:
    labels, object_count = label_components(mask, min_size=min_component_size)
    solid = np.zeros_like(mask, dtype=bool)
    image_area = mask.shape[0] * mask.shape[1]

    for object_id in range(1, object_count + 1):
        coords = np.argwhere(labels == object_id)
        if coords.size == 0:
            continue

        min_y, min_x = coords.min(axis=0)
        max_y, max_x = coords.max(axis=0)
        height = int(max_y - min_y + 1)
        width = int(max_x - min_x + 1)
        bbox_area = height * width
        if width < 5 or height < 5:
            continue
        if bbox_area > image_area * 0.45:
            continue
        if max(width, height) / max(1, min(width, height)) > 4.5:
            continue

        padding = max(2, int(round(0.08 * max(width, height))))
        y0 = max(0, int(min_y) - padding)
        y1 = min(mask.shape[0], int(max_y) + padding + 1)
        x0 = max(0, int(min_x) - padding)
        x1 = min(mask.shape[1], int(max_x) + padding + 1)

        yy, xx = np.mgrid[y0:y1, x0:x1]
        center_y = (y0 + y1 - 1) / 2.0
        center_x = (x0 + x1 - 1) / 2.0
        radius_y = max((y1 - y0) / 2.0, 1.0)
        radius_x = max((x1 - x0) / 2.0, 1.0)
        ellipse = ((yy - center_y) / radius_y) ** 2 + ((xx - center_x) / radius_x) ** 2 <= 1.0
        solid[y0:y1, x0:x1] |= ellipse

    return solid
