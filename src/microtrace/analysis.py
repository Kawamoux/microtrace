from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .image_io import condition_from_identifier, image_identifier, iter_image_paths, load_grayscale
from .metrics import ImageSummary, ObjectMeasurement, measure_objects, summarize_image
from .segmentation import segment_image


@dataclass(frozen=True)
class AnalysisOptions:
    threshold: float | str = "otsu"
    min_size: int = 32
    invert: bool = False


@dataclass(frozen=True)
class ImageAnalysis:
    image: str
    condition: str
    threshold: float
    summary: ImageSummary
    objects: list[ObjectMeasurement]


def analyze_image(path: str | Path, *, root: str | Path | None = None, options: AnalysisOptions | None = None) -> ImageAnalysis:
    analysis_options = options or AnalysisOptions()
    image_array = load_grayscale(path)
    image_id = image_identifier(path, root)
    condition = condition_from_identifier(image_id)
    segmentation = segment_image(
        image_array,
        threshold=analysis_options.threshold,
        min_size=analysis_options.min_size,
        invert=analysis_options.invert,
    )
    objects = measure_objects(image_array, segmentation.labels, image_id=image_id, condition=condition)
    summary = summarize_image(
        image_id=image_id,
        condition=condition,
        threshold=segmentation.threshold,
        measurements=objects,
    )
    return ImageAnalysis(image_id, condition, segmentation.threshold, summary, objects)


def analyze_inputs(input_path: str | Path, *, options: AnalysisOptions | None = None) -> list[ImageAnalysis]:
    root = Path(input_path)
    paths = iter_image_paths(root)
    root_for_ids = root if root.is_dir() else None
    return [analyze_image(path, root=root_for_ids, options=options) for path in paths]
