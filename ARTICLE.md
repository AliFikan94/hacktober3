---
title: Sloth Tidy: a folder sorter that runs on my own gemma3, offline
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

## What I Built
Sloth Tidy sorts and renames a messy folder (Downloads, Desktop) for you. Point it at a folder and it proposes `IMG_0042.JPG -> images/img-0042.jpg` or `Untitled(3).txt -> documents/team-standup-notes.txt`. It is a dry run by default, never overwrites a file, and `--undo` reverts the last run. The lazy part: I'd never organise this folder myself.

## Demo
<!-- TODO: paste a short screen recording, or the terminal output of a real run below -->
```
python sloth.py %USERPROFILE%\test-mess --model gemma3:1b
[1/3] notes.txt ...
...
dry run: 3 files. add --apply to do it.
```

## Code
{% embed https://github.com/AliFikan94/hacktober3 %}

## How I Built It
- **Model:** Google's open-weight `gemma3` (1B/4B) served by **Ollama** on my own PC. I already had it installed, so setup was zero.
- **Tool:** one Python file, standard library only. For each file it sends the filename and the first 600 characters of text files to the local model and asks for JSON (`{category, name}`).
- **Guardrails:** the answer is validated. If the server is down or the reply is invalid, it falls back to extension rules, so it never hangs or breaks.
- **Safety:** dry run first, collision-proof names, and an undo log.

## Why Does Open Innovation Matter?
A folder tidier has to read your private files: tax returns, chat exports, screenshots. With an open-weight model on localhost, the contents never leave my machine, it works offline, and it costs nothing per file. `--model` accepts any Ollama model, so swapping models is one flag. A closed API would mean uploading my Downloads folder to someone else's server.

## The Lazy Payoff
<!-- TODO: fill in honestly after your test, e.g. "sorted N files in X seconds; gemma3:1b was fast but names were generic, 4b was better but slower" -->

## Prize Categories
<!-- TODO: list any partner categories, or delete this section -->
