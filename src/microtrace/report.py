from __future__ import annotations

import csv
import hashlib
import html
from pathlib import Path

import numpy as np
from PIL import Image

from .analysis import ImageAnalysis
from .image_io import load_grayscale


def write_analysis_outputs(
    analyses: list[ImageAnalysis],
    output_dir: str | Path,
    *,
    include_overlays: bool = True,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    object_rows = [measurement.as_dict() for result in analyses for measurement in result.objects]
    summary_rows = [result.summary.as_dict() for result in analyses]
    object_csv = output / "objects.csv"
    summary_csv = output / "summary.csv"
    _write_csv(object_csv, object_rows, _object_fields())
    _write_csv(summary_csv, summary_rows, _summary_fields())

    overlay_paths: dict[str, str] = {}
    if include_overlays:
        overlay_dir = output / "overlays"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        for result in analyses:
            overlay_name = f"{_stable_name(result.image)}_overlay.png"
            overlay_path = overlay_dir / overlay_name
            image = load_grayscale(result.path)
            _create_overlay(image, result.labels).save(overlay_path)
            overlay_paths[result.image] = f"overlays/{overlay_name}"

    report_path = output / "report.html"
    report_path.write_text(_render_html(analyses, overlay_paths), encoding="utf-8")
    return {"objects": object_csv, "summary": summary_csv, "report": report_path}


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _object_fields() -> list[str]:
    return [
        "image",
        "condition",
        "object_id",
        "area_px",
        "perimeter_px",
        "circularity",
        "elongation",
        "centroid_x",
        "centroid_y",
        "bbox_x",
        "bbox_y",
        "bbox_width",
        "bbox_height",
        "mean_intensity",
        "integrated_intensity",
    ]


def _summary_fields() -> list[str]:
    return [
        "image",
        "condition",
        "threshold",
        "object_count",
        "total_area_px",
        "median_area_px",
        "mean_circularity",
        "mean_elongation",
        "mean_intensity",
    ]


def _create_overlay(image: np.ndarray, labels: np.ndarray) -> Image.Image:
    gray = np.round(np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)
    rgb = np.stack((gray, gray, gray), axis=-1).astype(np.float32)
    foreground = labels > 0
    rgb[foreground] = rgb[foreground] * 0.72 + np.array([33, 180, 150], dtype=np.float32) * 0.28

    padded = np.pad(labels, 1, mode="constant", constant_values=0)
    center = padded[1:-1, 1:-1]
    border = foreground & (
        (padded[:-2, 1:-1] != center)
        | (padded[2:, 1:-1] != center)
        | (padded[1:-1, :-2] != center)
        | (padded[1:-1, 2:] != center)
    )
    rgb[border] = np.array([255, 92, 70], dtype=np.float32)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")


def _render_html(analyses: list[ImageAnalysis], overlay_paths: dict[str, str]) -> str:
    object_count = sum(result.summary.object_count for result in analyses)
    total_area = sum(result.summary.total_area_px for result in analyses)
    all_areas = [measurement.area_px for result in analyses for measurement in result.objects]
    condition_rows = _condition_table(analyses)
    image_rows = "\n".join(_image_row(result) for result in analyses)
    object_rows = _object_table(analyses)
    overlay_cards = "\n".join(_overlay_card(result, overlay_paths.get(result.image)) for result in analyses)
    histogram = _histogram_svg(all_areas)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>microtrace report</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17211f;
      --muted: #66706d;
      --line: #dce5e1;
      --wash: #f4f8f6;
      --accent: #21a68b;
      --warm: #ff6d4d;
    }}
    body {{
      margin: 0;
      font: 14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #fbfcfb;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 24px;
    }}
    h1 {{
      font-size: 32px;
      line-height: 1.1;
      margin: 0 0 8px;
      letter-spacing: 0;
    }}
    h2 {{
      font-size: 18px;
      margin: 28px 0 12px;
      letter-spacing: 0;
    }}
    .muted {{ color: var(--muted); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin: 20px 0;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: white;
    }}
    .metric strong {{
      display: block;
      font-size: 24px;
      line-height: 1.2;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: white;
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
    }}
    th {{
      background: var(--wash);
      font-weight: 650;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .table-scroll {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
    }}
    .table-scroll table {{
      border: 0;
      border-radius: 0;
      min-width: 980px;
    }}
    td.numeric, th.numeric {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    figure {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
      overflow: hidden;
    }}
    figure img {{
      display: block;
      width: 100%;
      height: auto;
      image-rendering: auto;
    }}
    figcaption {{
      padding: 8px 10px;
      color: var(--muted);
      border-top: 1px solid var(--line);
      word-break: break-word;
    }}
    .chart {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
      padding: 12px;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>microtrace report</h1>
      <div class="muted">Reproducible object morphometry from microscopy-style images.</div>
    </header>
    <section class="metrics" aria-label="Run summary">
      <div class="metric"><span class="muted">Images</span><strong>{len(analyses)}</strong></div>
      <div class="metric"><span class="muted">Objects</span><strong>{object_count}</strong></div>
      <div class="metric"><span class="muted">Total area</span><strong>{total_area}</strong><span class="muted">px</span></div>
    </section>
    <h2>Object Area Distribution</h2>
    <div class="chart">{histogram}</div>
    <h2>Condition Summary</h2>
    <table>
      <thead><tr><th>Condition</th><th>Images</th><th>Objects</th><th>Median area px</th><th>Mean circularity</th><th>Mean intensity</th></tr></thead>
      <tbody>{condition_rows}</tbody>
    </table>
    <h2>Image Summary</h2>
    <table>
      <thead><tr><th>Image</th><th>Condition</th><th>Threshold</th><th>Objects</th><th>Total area px</th><th>Median area px</th></tr></thead>
      <tbody>{image_rows}</tbody>
    </table>
    <h2>Object Measurements</h2>
    <div class="table-scroll">
      <table>
        <thead><tr>{_object_header()}</tr></thead>
        <tbody>{object_rows}</tbody>
      </table>
    </div>
    <h2>Segmentation Overlays</h2>
    <div class="grid">{overlay_cards}</div>
  </main>
</body>
</html>
"""


def _condition_table(analyses: list[ImageAnalysis]) -> str:
    grouped: dict[str, list[ImageAnalysis]] = {}
    for result in analyses:
        grouped.setdefault(result.condition, []).append(result)

    rows: list[str] = []
    for condition, items in sorted(grouped.items()):
        measurements = [measurement for item in items for measurement in item.objects]
        areas = np.array([measurement.area_px for measurement in measurements], dtype=np.float64)
        circularity = np.array([measurement.circularity for measurement in measurements], dtype=np.float64)
        intensity = np.array([measurement.mean_intensity for measurement in measurements], dtype=np.float64)
        rows.append(
            "<tr>"
            f"<td>{html.escape(condition)}</td>"
            f"<td>{len(items)}</td>"
            f"<td>{len(measurements)}</td>"
            f"<td>{_mean_or_zero(areas, median=True):.2f}</td>"
            f"<td>{_mean_or_zero(circularity):.3f}</td>"
            f"<td>{_mean_or_zero(intensity):.3f}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _image_row(result: ImageAnalysis) -> str:
    summary = result.summary
    return (
        "<tr>"
        f"<td>{html.escape(summary.image)}</td>"
        f"<td>{html.escape(summary.condition)}</td>"
        f"<td>{summary.threshold:.4f}</td>"
        f"<td>{summary.object_count}</td>"
        f"<td>{summary.total_area_px}</td>"
        f"<td>{summary.median_area_px:.2f}</td>"
        "</tr>"
    )


def _object_header() -> str:
    labels = {
        "image": "Image",
        "condition": "Condition",
        "object_id": "Object",
        "area_px": "Area px",
        "perimeter_px": "Perimeter px",
        "circularity": "Circularity",
        "elongation": "Elongation",
        "centroid_x": "Centroid x",
        "centroid_y": "Centroid y",
        "bbox_x": "Box x",
        "bbox_y": "Box y",
        "bbox_width": "Box width",
        "bbox_height": "Box height",
        "mean_intensity": "Mean intensity",
        "integrated_intensity": "Integrated intensity",
    }
    cells = []
    for field in _object_fields():
        css_class = ' class="numeric"' if field not in {"image", "condition"} else ""
        cells.append(f"<th{css_class}>{labels[field]}</th>")
    return "".join(cells)


def _object_table(analyses: list[ImageAnalysis]) -> str:
    rows: list[str] = []
    numeric_fields = set(_object_fields()) - {"image", "condition"}
    for result in analyses:
        for measurement in result.objects:
            values = measurement.as_dict()
            cells = []
            for field in _object_fields():
                value = values[field]
                css_class = ' class="numeric"' if field in numeric_fields else ""
                cells.append(f"<td{css_class}>{html.escape(str(value))}</td>")
            rows.append(f"<tr>{''.join(cells)}</tr>")
    if rows:
        return "\n".join(rows)
    return f'<tr><td colspan="{len(_object_fields())}">No objects detected.</td></tr>'


def _overlay_card(result: ImageAnalysis, overlay_path: str | None) -> str:
    if overlay_path is None:
        return ""
    return (
        "<figure>"
        f'<img src="{html.escape(overlay_path)}" alt="Segmentation overlay for {html.escape(result.image)}">'
        f"<figcaption>{html.escape(result.image)}</figcaption>"
        "</figure>"
    )


def _histogram_svg(values: list[int], *, width: int = 760, height: int = 180, bins: int = 18) -> str:
    if not values:
        return '<svg viewBox="0 0 760 180" role="img" aria-label="No object areas detected"></svg>'
    counts, edges = np.histogram(np.array(values, dtype=np.float64), bins=min(bins, max(1, len(values))))
    max_count = int(counts.max()) or 1
    padding = 24
    plot_width = width - padding * 2
    plot_height = height - padding * 2
    bar_width = plot_width / len(counts)
    bars = []
    for index, count in enumerate(counts):
        bar_height = plot_height * (int(count) / max_count)
        x = padding + index * bar_width
        y = height - padding - bar_height
        bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(1.0, bar_width - 3):.2f}" '
            f'height="{bar_height:.2f}" fill="#21a68b" rx="2" />'
        )
    label = f"{edges[0]:.0f}-{edges[-1]:.0f} px"
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Object area histogram">'
        f'<line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" stroke="#dce5e1" />'
        f'{"".join(bars)}'
        f'<text x="{padding}" y="{height - 6}" fill="#66706d" font-size="12">{html.escape(label)}</text>'
        "</svg>"
    )


def _mean_or_zero(values: np.ndarray, *, median: bool = False) -> float:
    if values.size == 0:
        return 0.0
    return float(np.median(values) if median else values.mean())


def _stable_name(identifier: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "-_." else "_" for char in identifier.replace("/", "__"))
    digest = hashlib.sha1(identifier.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned[:80]}_{digest}"
