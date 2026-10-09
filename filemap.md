CLAUDE.md — agent rules for this repo; read first
docs/SPEC.md — what the CLI does and how it is structured
docs/PLAN.md — ordered task list for the build
filemap.md — this index; update when files change
.gitignore — Python ignores (venvs, caches, build output); touch when new artifacts appear
hello/__init__.py — package marker for the hello CLI; rarely touched
hello/greet.py — pure greet(name, shout) function; touch to change greeting text or name handling
hello/cli.py — argparse entry point main(argv) that prints greet(...); touch to add or change CLI options
hello/__main__.py — runs main() for `python -m hello`; rarely touched
tests/__init__.py — empty marker so unittest discovers tests/; do not add logic
tests/test_hello.py — unittest tests for greet() and main(); touch when behaviour changes
README.md — usage examples and test command; touch when CLI usage changes
.claude-plugin/marketplace.json — marketplace catalog for the agent-flair mod; touch when adding a mod
mods/agent-flair/ — mod: animated Claw'd cards per subagent type; edit hooks/register.tsx
