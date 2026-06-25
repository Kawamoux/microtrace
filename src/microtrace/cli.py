from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .analysis import AnalysisOptions, analyze_inputs
from .report import write_analysis_outputs
from .synthetic import write_synthetic_series


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microtrace",
        description="Microscopy-style morphometry from images to reproducible reports.",
    )
    parser.add_argument("--version", action="version", version=f"microtrace {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    demo = subparsers.add_parser("demo", help="Create a synthetic demo dataset and analyze it.")
    demo.add_argument("output", type=Path, help="Directory for the demo dataset and report.")
    demo.add_argument("--images-per-condition", type=int, default=4)
    demo.add_argument("--seed", type=int, default=7)

    simulate = subparsers.add_parser("simulate", help="Create synthetic microscopy-style images.")
    simulate.add_argument("output", type=Path, help="Directory for generated images.")
    simulate.add_argument("--images-per-condition", type=int, default=4)
    simulate.add_argument("--seed", type=int, default=7)
    simulate.add_argument("--width", type=int, default=384)
    simulate.add_argument("--height", type=int, default=384)
    simulate.add_argument("--objects", type=int, default=36)
    analyze = subparsers.add_parser("analyze", help="Analyze one image or a folder of images.")
    analyze.add_argument("input", type=Path, help="Image file or directory of images.")
    analyze.add_argument("--output", type=Path, default=Path("results"))
    analyze.add_argument("--threshold", default="otsu", help="Use 'otsu' or a numeric threshold between 0 and 1.")
    analyze.add_argument(
        "--mode",
        choices=["intensity", "brightfield"],
        default="intensity",
        help="Use intensity for bright objects, or brightfield for transmitted-light/phase-contrast images.",
    )
    analyze.add_argument("--min-size", type=int, default=32, help="Minimum object area in pixels.")
    analyze.add_argument("--invert", action="store_true", help="Segment dark objects on a bright background.")
    analyze.add_argument("--background-radius", type=float, default=18.0, help="Brightfield background blur radius.")
    analyze.add_argument("--smooth-radius", type=float, default=1.0, help="Brightfield response smoothing radius.")
    analyze.add_argument("--close-iterations", type=int, default=2, help="Brightfield contour closing iterations.")
    analyze.add_argument("--no-fill-holes", action="store_true", help="Skip brightfield hole filling.")
    analyze.add_argument("--no-overlays", action="store_true", help="Skip overlay image export.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "simulate":
        write_synthetic_series(
            args.output,
            images_per_condition=args.images_per_condition,
            seed=args.seed,
            width=args.width,
            height=args.height,
            base_objects=args.objects,
        )
        print(f"Wrote synthetic image series to {args.output}")
        return 0
    if args.command == "analyze":
        options = AnalysisOptions(
            threshold=_parse_threshold(args.threshold),
            min_size=args.min_size,
            invert=args.invert,
            mode=args.mode,
            background_radius=args.background_radius,
            smooth_radius=args.smooth_radius,
            close_iterations=args.close_iterations,
            fill_holes=not args.no_fill_holes,
        )
        analyses = analyze_inputs(args.input, options=options)
        outputs = write_analysis_outputs(analyses, args.output, include_overlays=not args.no_overlays)
        print(f"Analyzed {len(analyses)} image(s).")
        print(f"Report: {outputs['report']}")
        return 0
    if args.command == "demo":
        image_dir = args.output / "images"
        report_dir = args.output / "report"
        write_synthetic_series(image_dir, images_per_condition=args.images_per_condition, seed=args.seed)
        analyses = analyze_inputs(image_dir, options=AnalysisOptions(min_size=32))
        outputs = write_analysis_outputs(analyses, report_dir)
        print(f"Demo images: {image_dir}")
        print(f"Report: {outputs['report']}")
        return 0
    parser.error(f"Command '{args.command}' is not implemented yet.")
    return 2


def _parse_threshold(value: str) -> float | str:
    if value == "otsu":
        return value
    return float(value)
