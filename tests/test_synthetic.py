import numpy as np

from microtrace.synthetic import SyntheticConfig, generate_micrograph, write_synthetic_series


def test_synthetic_micrograph_is_deterministic():
    config = SyntheticConfig(width=96, height=80, objects=8, seed=42)

    first = np.asarray(generate_micrograph(config))
    second = np.asarray(generate_micrograph(config))

    assert first.shape == (80, 96)
    assert np.array_equal(first, second)
    assert first.max() > first.mean()


def test_synthetic_series_writes_relative_metadata(tmp_path):
    records = write_synthetic_series(tmp_path, images_per_condition=1, seed=4, width=64, height=64, base_objects=6)
    metadata = (tmp_path / "metadata.csv").read_text(encoding="utf-8")

    assert len(records) == 2
    assert "control/field_001.png" in metadata
    assert str(tmp_path) not in metadata
    assert (tmp_path / "control" / "field_001.png").exists()
