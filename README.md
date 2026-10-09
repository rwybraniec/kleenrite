# hello

A tiny command-line tool that prints a greeting.

## Usage

```
$ python -m hello
Hello, world!
$ python -m hello Ada
Hello, Ada!
$ python -m hello Ada --shout
HELLO, ADA!
```

## Tests

```
python -m unittest discover -s tests
```

## Claude Code mods

This repo is also a Claude Code marketplace with one mod, and it pairs with `savvy-progress` for the progress bar.

| Mod | What it does |
| --- | --- |
| `agent-flair` (this repo) | Every subagent card gets an animated Claw'd, with its own colors, hat, gait and arm motion per agent type, plus a toast when the agent spawns. |
| `savvy-progress` ([JohnnyVizz/claude-kit](https://github.com/JohnnyVizz/claude-kit)) | The progress bar above the prompt and a live agents panel (`/agents-info`). Driven by the `savvy-flow` skill. |
| `savvy-flow` ([JohnnyVizz/claude-kit](https://github.com/JohnnyVizz/claude-kit)) | The `/savvy-flow:savvy-flow <task>` skill and its five worker agents that feed the bar. |

Install (terminal session):

```
/plugin marketplace add rwybraniec/kleenrite
/plugin install agent-flair@kleenrite
/plugin marketplace add JohnnyVizz/claude-kit
/plugin install savvy-flow@claude-kit
/plugin install savvy-progress@claude-kit
```

Restart the session afterwards. Mods draw only on the terminal and desktop surfaces, not in the claude.ai web or mobile apps.

Check the mod: `claude plugin validate mods/agent-flair` and `claude plugin test mods/agent-flair`.
