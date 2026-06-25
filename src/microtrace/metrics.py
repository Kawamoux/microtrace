from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ObjectMeasurement:
    image: str
    condition: str
    object_id: int
    area_px: int
    perimeter_px: int
    circularity: float
    elongation: float
    centroid_x: float
    centroid_y: float
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    mean_intensity: float
    integrated_intensity: float

    def as_dict(self) -> dict[str, str | int | float]:
        return {
            "image": self.image,
            "condition": self.condition,
            "object_id": self.object_id,
            "area_px": self.area_px,
            "perimeter_px": self.perimeter_px,
            "circularity": round(self.circularity, 6),
            "elongation": round(self.elongation, 6),
            "centroid_x": round(self.centroid_x, 3),
            "centroid_y": round(self.centroid_y, 3),
            "bbox_x": self.bbox_x,
            "bbox_y": self.bbox_y,
            "bbox_width": self.bbox_width,
            "bbox_height": self.bbox_height,
            "mean_intensity": round(self.mean_intensity, 6),
            "integrated_intensity": round(self.integrated_intensity, 6),
        }


@dataclass(frozen=True)
class ImageSummary:
    image: str
    condition: str
    threshold: float
    object_count: int
    total_area_px: int
    median_area_px: float
    mean_circularity: float
    mean_elongation: float
    mean_intensity: float

    def as_dict(self) -> dict[str, str | int | float]:
        return {
            "image": self.image,
            "condition": self.condition,
            "threshold": round(self.threshold, 6),
            "object_count": self.object_count,
            "total_area_px": self.total_area_px,
            "median_area_px": round(self.median_area_px, 3),
            "mean_circularity": round(self.mean_circularity, 6),
            "mean_elongation": round(self.mean_elongation, 6),
            "mean_intensity": round(self.mean_intensity, 6),
        }


def measure_objects(
    image: np.ndarray,
    labels: np.ndarray,
    *,
    image_id: str,
    condition: str,
) -> list[ObjectMeasurement]:
    measurements: list[ObjectMeasurement] = []
    for object_id in range(1, int(labels.max()) + 1):
        coords = np.argwhere(labels == object_id)
        if coords.size == 0:
            continue
        ys = coords[:, 0]
        xs = coords[:, 1]
        values = image[ys, xs]
        area = int(coords.shape[0])
        perimeter = _perimeter(labels == object_id)
        circularity = 0.0 if perimeter == 0 else float(4.0 * math.pi * area / (perimeter * perimeter))
        elongation = _elongation(xs.astype(np.float64), ys.astype(np.float64))
        min_y, min_x = coords.min(axis=0)
        max_y, max_x = coords.max(axis=0)
        measurements.append(
            ObjectMeasurement(
                image=image_id,
                condition=condition,
                object_id=object_id,
                area_px=area,
                perimeter_px=perimeter,
                circularity=circularity,
                elongation=elongation,
                centroid_x=float(xs.mean()),
                centroid_y=float(ys.mean()),
                bbox_x=int(min_x),
                bbox_y=int(min_y),
                bbox_width=int(max_x - min_x + 1),
                bbox_height=int(max_y - min_y + 1),
                mean_intensity=float(values.mean()),
                integrated_intensity=float(values.sum()),
            )
        )
    return measurements


def summarize_image(
    *,
    image_id: str,
    condition: str,
    threshold: float,
    measurements: list[ObjectMeasurement],
) -> ImageSummary:
    if not measurements:
        return ImageSummary(image_id, condition, threshold, 0, 0, 0.0, 0.0, 0.0, 0.0)

    areas = np.array([item.area_px for item in measurements], dtype=np.float64)
    circularities = np.array([item.circularity for item in measurements], dtype=np.float64)
    elongations = np.array([item.elongation for item in measurements], dtype=np.float64)
    intensities = np.array([item.mean_intensity for item in measurements], dtype=np.float64)
    return ImageSummary(
        image=image_id,
        condition=condition,
        threshold=threshold,
        object_count=len(measurements),
        total_area_px=int(areas.sum()),
        median_area_px=float(np.median(areas)),
        mean_circularity=float(circularities.mean()),
        mean_elongation=float(elongations.mean()),
        mean_intensity=float(intensities.mean()),
    )


def _perimeter(component: np.ndarray) -> int:
    padded = np.pad(component.astype(bool), 1, mode="constant", constant_values=False)
    center = padded[1:-1, 1:-1]
    exposed = (
        (~padded[:-2, 1:-1]).astype(np.int8)
        + (~padded[2:, 1:-1]).astype(np.int8)
        + (~padded[1:-1, :-2]).astype(np.int8)
        + (~padded[1:-1, 2:]).astype(np.int8)
    )
    return int((center * exposed).sum())


def _elongation(xs: np.ndarray, ys: np.ndarray) -> float:
    if xs.size < 3:
        return 1.0
    centered = np.column_stack((xs - xs.mean(), ys - ys.mean()))
    covariance = np.cov(centered, rowvar=False)
    eigenvalues = np.linalg.eigvalsh(covariance)
    minor = max(float(eigenvalues[0]), 1e-9)
    major = max(float(eigenvalues[-1]), minor)
    return math.sqrt(major / minor)
