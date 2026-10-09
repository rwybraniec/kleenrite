# hello CLI: spec

## Goals
- A tiny command-line tool, `python -m hello [NAME] [--shout]`, that prints a greeting.
- A reference project for exercising the savvy-flow pipeline end to end.

## Non-goals
- No packaging to PyPI, no third-party dependencies, no config files, no i18n.

## Stack
- Python 3.13, standard library only (`argparse`, `unittest`).

## Architecture
- `hello/greet.py`: pure function `greet(name: str = "world", shout: bool = False) -> str`.
- `hello/cli.py`: `main(argv: list[str] | None = None) -> int`; parses args, prints `greet(...)`, returns 0.
- `hello/__main__.py`: calls `sys.exit(main())`.
- `tests/test_hello.py`: `unittest` tests for `greet` and `main`.

## Behaviour
- `python -m hello` prints `Hello, world!`
- `python -m hello Ada` prints `Hello, Ada!`
- `python -m hello Ada --shout` prints `HELLO, ADA!`
- An empty or whitespace-only NAME falls back to `world`.

## Definition of done
- All three commands above behave as listed.
- `python -m unittest discover -s tests` passes.
- README documents usage and how to run the tests.
