from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
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

    simulate = subparsers.add_parser("simulate", help="Create synthetic microscopy-style images.")
    simulate.add_argument("output", type=Path, help="Directory for generated images.")
    simulate.add_argument("--images-per-condition", type=int, default=4)
    simulate.add_argument("--seed", type=int, default=7)
    simulate.add_argument("--width", type=int, default=384)
    simulate.add_argument("--height", type=int, default=384)
    simulate.add_argument("--objects", type=int, default=36)
    subparsers.add_parser("analyze", help="Analyze one image or a folder of images.")
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
    parser.error(f"Command '{args.command}' is not implemented yet.")
    return 2
