import csv

from microtrace.analysis import AnalysisOptions, analyze_inputs
from microtrace.report import write_analysis_outputs
from microtrace.synthetic import write_synthetic_series


def test_end_to_end_demo_outputs_are_shareable(tmp_path):
    image_dir = tmp_path / "images"
    report_dir = tmp_path / "report"
    write_synthetic_series(image_dir, images_per_condition=1, seed=9, width=96, height=96, base_objects=8)

    analyses = analyze_inputs(image_dir, options=AnalysisOptions(min_size=8))
    outputs = write_analysis_outputs(analyses, report_dir)

    assert len(analyses) == 2
    assert outputs["objects"].exists()
    assert outputs["summary"].exists()
    assert outputs["statistics"].exists()
    assert outputs["report"].exists()
    assert (report_dir / "overlays").exists()

    with outputs["objects"].open(newline="", encoding="utf-8") as handle:
        object_rows = list(csv.DictReader(handle))
    with outputs["statistics"].open(newline="", encoding="utf-8") as handle:
        statistics_rows = list(csv.DictReader(handle))

    report_html = outputs["report"].read_text(encoding="utf-8")

    assert object_rows
    assert statistics_rows
    assert statistics_rows[0]["condition"] == "all"
    assert "mean_area_px" in statistics_rows[0]
    assert "microtrace report" in report_html
    assert "Measurement Statistics" in report_html
    assert "Mean area px" in report_html
    assert "Object Measurements" in report_html
    assert "Integrated intensity" in report_html
    assert object_rows[0]["image"] in report_html
    assert str(tmp_path) not in report_html
