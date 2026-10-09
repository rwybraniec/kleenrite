# hello CLI: plan

1. **Scaffold project** (Light). Create `hello/__init__.py`, empty `tests/__init__.py`, `.gitignore` (Python), and `filemap.md` entries. No logic yet. Verify: `python -c "import hello"`.
2. **Implement greeting and CLI** (Medium, after 1). Write `hello/greet.py`, `hello/cli.py`, `hello/__main__.py` exactly as in `docs/SPEC.md` (Architecture and Behaviour). Verify: run the three example commands and compare output.
3. **Add tests and README** (Light, after 2). Write `tests/test_hello.py` covering default, named, shout and blank-name cases for `greet` and `main`; write `README.md` with usage and the test command. Verify: `python -m unittest discover -s tests` passes.
