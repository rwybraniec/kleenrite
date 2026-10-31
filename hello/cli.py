"""Command-line entry point for the hello CLI."""

import argparse

from hello.greet import greet


def positive_int(value: str) -> int:
    """Convert ``value`` to an int >= 1 or raise ``argparse.ArgumentTypeError``."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value!r}") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value!r}")
    return number


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, print the greeting and return the exit code."""
    parser = argparse.ArgumentParser(prog="hello", description="Print a greeting.")
    parser.add_argument("name", nargs="?", default="world", help="who to greet (default: world)")
    parser.add_argument("--shout", action="store_true", help="uppercase the greeting")
    parser.add_argument(
        "--repeat",
        type=positive_int,
        default=1,
        metavar="N",
        help="print the greeting N times (default: 1)",
    )
    args = parser.parse_args(argv)
    message = greet(args.name, shout=args.shout)
    for _ in range(args.repeat):
        print(message)
    return 0
