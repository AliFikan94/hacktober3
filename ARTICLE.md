---
title: Sloth Tidy: a folder sorter that runs on my own gemma3, offline
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

## What I Built
Sloth Tidy sorts and renames a messy folder (Downloads, Desktop) for you. Point it at a folder and it proposes `IMG_0042.JPG -> images/img-0042.jpg` or `Untitled(3).txt -> documents/team-standup-notes.txt`. It is a dry run by default, never overwrites a file, and `--undo` reverts the last run. The lazy part: I'd never organise this folder myself.

## Demo
Two files, `note2.txt` (a grocery list) and `Untitled1.txt` (standup notes), sorted by what they actually say, using `gemma3:1b` on my own CPU:

```
PS> python sloth.py $HOME\mini --model gemma3:1b
(first file may be slow while gemma3:1b loads)
[1/2] note2.txt ...
[2/2] Untitled1.txt ...
note2.txt  ->  documents\groceries-list.txt
Untitled1.txt  ->  documents\standup-notes.txt
dry run: 2 files. add --apply to do it.
```
<!-- TODO: optionally add a screenshot or short screen recording here -->

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
It names files by their content without me opening them, and my files never leave my machine. Honest notes from building it:
- My first run named both files `other.txt`. Two causes: Windows PowerShell saves text as UTF-16, which my code read as garbage, and a 1B model sometimes copies words from the prompt. Fixing the decoding and giving the model a clearer example made it work.
- The tool never hangs: if Ollama is down or a reply is invalid, it falls back to simple extension rules.
- It runs entirely on CPU. A small model is slow per file, so it suits an overnight or one-off tidy, not instant results.

## Prize Categories
<!-- TODO: list any partner categories, or delete this section -->
