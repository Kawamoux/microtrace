# Examples

The examples are fully synthetic and do not require private microscopy data.

Create a small two-condition dataset:

```bash
microtrace simulate synthetic-data --images-per-condition 3 --seed 21
```

Analyze it:

```bash
microtrace analyze synthetic-data --output results
```

Open `results/report.html` to review the condition summary, image-level table,
object-level CSV outputs, and segmentation overlays.
