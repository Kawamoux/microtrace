# microtrace

Microtrace is a small, reproducible morphometry toolkit for microscopy-style
assay images. It helps biology labs turn raw micrographs into transparent
object-level measurements, image summaries, overlays, and shareable HTML
reports without requiring a heavy desktop workflow.

The project is designed for early experiment triage, method development, and
teaching datasets. It includes a synthetic image generator so examples and
tests can run without bundling real experimental data.

## Current scope

- Analyze single images or folders of images.
- Segment bright biological objects on darker backgrounds.
- Measure area, perimeter, circularity, elongation, centroid, and intensity.
- Export object-level and image-level CSV tables.
- Build an HTML report with compact visual summaries.
- Generate synthetic microscopy-like image sets for reproducible demos.

## Installation

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e ".[dev]"
```

## Quick start

```bash
microtrace demo demo-output
```

The demo command creates synthetic images, runs the analysis pipeline, and
writes a report into `demo-output/report`.

To run each step manually:

```bash
microtrace simulate synthetic-data --images-per-condition 3 --seed 21
microtrace analyze synthetic-data --output results
```

The analysis command writes:

- `objects.csv`: one row per segmented object.
- `summary.csv`: one row per image.
- `report.html`: a shareable report with condition summaries and overlays.
- `overlays/`: PNG overlays showing the segmented object boundaries.

## Measurement model

Microtrace segments bright objects with either Otsu thresholding or a user
provided threshold. Small connected components are removed, then each remaining
object is measured independently.

Object-level measurements include:

- area and perimeter in pixels,
- circularity,
- elongation from the object covariance matrix,
- centroid and bounding box,
- mean and integrated intensity.

Image-level summaries aggregate object count, total area, median area, mean
circularity, mean elongation, and mean intensity.

## Synthetic data

The synthetic generator creates two simple conditions by default:

- `control`: larger, more compact objects,
- `stress`: smaller and more fragmented objects.

The generator writes a `metadata.csv` file with relative image identifiers,
condition names, seeds, and simulation parameters.

## Development

Run the test suite with:

```bash
python -m pytest
```

## Design goals

Microtrace keeps the analysis path explicit: every result is derived from the
input image, a segmentation threshold, and a documented set of measurements.
The output files avoid absolute local paths so reports can be shared without
leaking workstation details.
