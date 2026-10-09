"""Command-line entry point for the hello CLI."""

import argparse

from hello.greet import greet


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, print the greeting and return the exit code."""
    parser = argparse.ArgumentParser(prog="hello", description="Print a greeting.")
    parser.add_argument("name", nargs="?", default="world", help="who to greet (default: world)")
    parser.add_argument("--shout", action="store_true", help="uppercase the greeting")
    args = parser.parse_args(argv)
    print(greet(args.name, shout=args.shout))
    return 0
