from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


@dataclass(frozen=True)
class SyntheticConfig:
    width: int = 384
    height: int = 384
    objects: int = 36
    seed: int = 7
    background: float = 0.12
    noise: float = 0.035
    blur_radius: float = 1.15
    size_scale: float = 1.0
    fragmentation: float = 0.15
    intensity: float = 0.82


@dataclass(frozen=True)
class ConditionProfile:
    name: str
    object_multiplier: float
    size_scale: float
    fragmentation: float
    intensity: float


@dataclass(frozen=True)
class SyntheticRecord:
    condition: str
    image: str
    seed: int
    objects: int
    size_scale: float
    fragmentation: float


DEFAULT_PROFILES = (
    ConditionProfile("control", 1.0, 1.0, 0.12, 0.84),
    ConditionProfile("stress", 1.35, 0.68, 0.58, 0.78),
)


def generate_micrograph(config: SyntheticConfig) -> Image.Image:
    """Create a grayscale microscopy-like field with bright biological objects."""
    rng = np.random.default_rng(config.seed)
    yy = np.linspace(0.0, 1.0, config.height, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, config.width, dtype=np.float32)[None, :]
    gradient = 0.035 * (xx * 0.7 + yy * 0.3)
    background = rng.normal(config.background, config.noise, (config.height, config.width))
    base = np.clip(background + gradient, 0.0, 1.0)

    layer = Image.new("L", (config.width, config.height), 0)
    draw = ImageDraw.Draw(layer)
    margin = max(18, int(22 * config.size_scale))

    for _ in range(config.objects):
        cx = int(rng.integers(margin, max(margin + 1, config.width - margin)))
        cy = int(rng.integers(margin, max(margin + 1, config.height - margin)))
        radius = float(rng.lognormal(mean=2.45, sigma=0.34) * config.size_scale)
        pieces = 1 + int(rng.random() < config.fragmentation) + int(rng.random() < config.fragmentation * 0.65)
        fill = int(np.clip(rng.normal(config.intensity, 0.055), 0.42, 0.98) * 255)

        for piece in range(pieces):
            offset = radius * config.fragmentation * 0.55
            px = cx + int(rng.normal(0.0, max(1.0, offset)))
            py = cy + int(rng.normal(0.0, max(1.0, offset)))
            sx = max(3.0, radius * rng.uniform(0.72, 1.28))
            sy = max(3.0, radius * rng.uniform(0.55, 1.05))
            if piece:
                sx *= rng.uniform(0.42, 0.72)
                sy *= rng.uniform(0.42, 0.72)
            draw.ellipse((px - sx, py - sy, px + sx, py + sy), fill=fill)

    layer = layer.filter(ImageFilter.GaussianBlur(radius=config.blur_radius))
    signal = np.asarray(layer, dtype=np.float32) / 255.0
    camera_noise = rng.normal(0.0, config.noise * 0.55, signal.shape)
    image = np.clip(np.maximum(base, signal) + camera_noise, 0.0, 1.0)
    return Image.fromarray(np.round(image * 255).astype(np.uint8), mode="L")


def write_synthetic_series(
    output_dir: str | Path,
    *,
    images_per_condition: int = 4,
    seed: int = 7,
    width: int = 384,
    height: int = 384,
    base_objects: int = 36,
    profiles: tuple[ConditionProfile, ...] = DEFAULT_PROFILES,
) -> list[SyntheticRecord]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    records: list[SyntheticRecord] = []

    for condition_index, profile in enumerate(profiles):
        condition_dir = output / profile.name
        condition_dir.mkdir(parents=True, exist_ok=True)

        for image_index in range(images_per_condition):
            image_seed = seed + condition_index * 10_000 + image_index
            object_count = max(1, int(round(base_objects * profile.object_multiplier)))
            config = SyntheticConfig(
                width=width,
                height=height,
                objects=object_count,
                seed=image_seed,
                size_scale=profile.size_scale,
                fragmentation=profile.fragmentation,
                intensity=profile.intensity,
            )
            image = generate_micrograph(config)
            image_name = f"field_{image_index + 1:03d}.png"
            image.save(condition_dir / image_name)
            records.append(
                SyntheticRecord(
                    condition=profile.name,
                    image=f"{profile.name}/{image_name}",
                    seed=image_seed,
                    objects=object_count,
                    size_scale=profile.size_scale,
                    fragmentation=profile.fragmentation,
                )
            )

    _write_metadata(output / "metadata.csv", records)
    return records


def _write_metadata(path: Path, records: list[SyntheticRecord]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["condition", "image", "seed", "objects", "size_scale", "fragmentation"],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "condition": record.condition,
                    "image": record.image,
                    "seed": record.seed,
                    "objects": record.objects,
                    "size_scale": f"{record.size_scale:.3f}",
                    "fragmentation": f"{record.fragmentation:.3f}",
                }
            )
