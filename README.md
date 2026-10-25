# Sloth Tidy

Point it at a messy folder. It sorts and renames everything using a **local open-weight model** (via [Ollama](https://ollama.com)). Nothing leaves your machine. Python stdlib only.

```bash
ollama pull gemma3:4b          # any open-weight model works (gemma3:1b is faster)
python3 sloth.py ~/Downloads             # dry run: shows what it would do
python3 sloth.py ~/Downloads --apply     # do it
python3 sloth.py ~/Downloads --undo      # change your mind
```

`IMG_0042.JPG` becomes `images/img-0042.jpg`. `Untitled(3).txt` containing meeting notes becomes `documents/team-standup-notes.txt`.

## How it works
- For each file, sends the filename plus the first 600 characters (text files only) to the local model and asks for JSON: `{category, name}`.
- Output is validated; a bad answer or an unreachable server falls back to extension rules, so it never hangs or breaks.
- Safe by default: dry run, never overwrites (`-2`, `-3` suffixes), and `--apply` writes an undo log.
- `--model` accepts any Ollama tag, so swapping models is one flag. `--no-model` is rules-only.

## Why open matters here
A folder tidier reads your *private* files: tax PDFs, chat exports, screenshots. With an open-weight model on localhost, contents never touch a third-party server, it works offline, and it costs nothing per file. Set it up once, run it from cron, and forget it.

## Tests
`python3 -m unittest discover -s tests`

---
*Submission for the Hacktoberfest Open-Source AI Challenge, Week 3: Slow and Steady.*
