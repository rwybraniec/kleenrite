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
docs/images/agent-flair.png — preview render of the agent-flair cards; regenerate if the sprites change
docs/images/savvy-progress.png — preview render of savvy-progress (third-party mod, drawn from its output)
docs/INTEGRATOR.md — design + usage for the integrator iPaaS engine; touch when behaviour changes
integrator/ — Celigo-style flow engine (source -> mapping -> destination); `python -m integrator`
integrator/auth.py — OAuth1 (NetSuite TBA) and AWS SigV4 signing; touch for auth bugs
integrator/http.py — Transport interface + urllib impl + Response; tests inject a fake
integrator/config.py — flow JSON loading/validation and $env: secret resolution
integrator/mapping.py — field mapping and transforms; touch to add a transform
integrator/store.py — SQLite run history, errors, watermarks
integrator/runner.py — run_flow: batching, retries, error capture, delta watermark
integrator/cli.py — argparse CLI (validate, run, runs, errors, connectors)
integrator/connectors/ — connector registry (__init__), base class, netsuite.py, aws.py (S3, SQS); add new connectors here
examples/ — sample flow JSON files (NetSuite -> S3, S3 -> NetSuite)
tests/test_integrator.py — unittest tests for the integrator using a fake transport
