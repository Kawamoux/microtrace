import numpy as np

from microtrace.metrics import measure_objects
from microtrace.segmentation import label_components, otsu_threshold, segment_image


def test_label_components_removes_small_objects():
    mask = np.zeros((12, 12), dtype=bool)
    mask[2:6, 2:6] = True
    mask[9, 9] = True

    labels, count = label_components(mask, min_size=4)

    assert count == 1
    assert labels[3, 3] == 1
    assert labels[9, 9] == 0


def test_segmentation_and_measurements_on_simple_object():
    image = np.zeros((20, 20), dtype=np.float32)
    image[5:11, 6:14] = 0.9

    result = segment_image(image, threshold=0.5, min_size=4)
    measurements = measure_objects(image, result.labels, image_id="field.png", condition="default")

    assert result.object_count == 1
    assert measurements[0].area_px == 48
    assert measurements[0].mean_intensity > 0.89
    assert measurements[0].bbox_width == 8
    assert measurements[0].bbox_height == 6


def test_otsu_threshold_separates_two_modes():
    image = np.concatenate(
        [
            np.full(100, 0.1, dtype=np.float32),
            np.full(100, 0.8, dtype=np.float32),
        ]
    )

    threshold = otsu_threshold(image)

    assert 0.1 <= threshold <= 0.8
