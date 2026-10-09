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

This repo is also a Claude Code marketplace with two mods.

| Mod | What it does |
| --- | --- |
| `agent-flair` | Every subagent card gets an animated Claw'd, with its own colors, hat, gait and arm motion per agent type, plus a toast when the agent spawns. |
| `progress-band` | A red-to-green gradient progress bar above the prompt. It follows the task list (or your usual turn length) and shows time left. It also opens a progress pane and `/progress`. |

Install (terminal session):

```
/plugin marketplace add rwybraniec/kleenrite
/plugin install agent-flair@kleenrite
/plugin install progress-band@kleenrite
```

Restart the session afterwards. Mods draw only on the terminal and desktop surfaces, not in the claude.ai web or mobile apps.

`progress-band` and `savvy-progress` (from `JohnnyVizz/claude-kit`) both draw above the prompt: use one or the other.

Check a mod: `claude plugin validate mods/<name>` and `claude plugin test mods/<name>`.
