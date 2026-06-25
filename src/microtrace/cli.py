from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microtrace",
        description="Microscopy-style morphometry from images to reproducible reports.",
    )
    parser.add_argument("--version", action="version", version=f"microtrace {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("demo", help="Create a synthetic demo dataset and analyze it.")
    subparsers.add_parser("simulate", help="Create synthetic microscopy-style images.")
    subparsers.add_parser("analyze", help="Analyze one image or a folder of images.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    parser.error(f"Command '{args.command}' is not implemented yet.")
    return 2
