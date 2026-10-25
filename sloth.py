#!/usr/bin/env python3
"""Sloth Tidy: sort and rename a messy folder with a local open-weight model.

Talks to a local Ollama server (default http://localhost:11434). No cloud, no
API key, no dependencies. If no model is reachable it falls back to simple
extension rules, so it never blocks on the network.

Dry-run by default. --apply moves files and writes an undo log; --undo reverts.
"""
import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

CATEGORIES = ["documents", "images", "code", "data", "audio", "video", "archives", "other"]
EXT_MAP = {
    "images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".heic"},
    "documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".odt", ".rtf"},
    "code": {".py", ".js", ".ts", ".go", ".rs", ".c", ".cpp", ".java", ".sh", ".html", ".css"},
    "data": {".csv", ".json", ".xlsx", ".xml", ".yaml", ".yml", ".sql"},
    "audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "video": {".mp4", ".mov", ".mkv", ".avi", ".webm"},
    "archives": {".zip", ".tar", ".gz", ".7z", ".rar", ".tgz"},
}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".xml", ".yaml", ".yml", ".sql", ".sh"}
LOG_NAME = ".sloth-undo.json"


def rule_category(path: Path) -> str:
    ext = path.suffix.lower()
    for cat, exts in EXT_MAP.items():
        if ext in exts:
            return cat
    return "other"


def snippet(path: Path, limit: int = 600) -> str:
    if path.suffix.lower() not in TEXT_EXTS:
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(limit)
    except OSError:
        return ""


def slugify(name: str) -> str:
    name = re.sub(r"[^\w\- ]+", "", name).strip().lower()
    return re.sub(r"[\s_]+", "-", name)[:60].strip("-")


def ask_model(path: Path, host: str, model: str, timeout: float = 60.0, fallback_cat: str = "other"):
    """Return (category, stem) from the local model, or None if unavailable/invalid."""
    prompt = (
        "You file clutter. Reply with JSON only: "
        '{"category": one of %s, "name": "short-kebab-case-descriptive-name"}.\n'
        "Filename: %s\nContent start:\n%s" % (CATEGORIES, path.name, snippet(path) or "(binary or empty)")
    )
    body = json.dumps({"model": model, "stream": False, "format": "json",
                       "options": {"num_predict": 80, "temperature": 0},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(host.rstrip("/") + "/api/chat", body,
                                 {"Content-Type": "application/json"})
    raw = ""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = json.loads(r.read())["message"]["content"]
        reply = json.loads(raw)
        stem = slugify(str(reply.get("name", "")))
        cat = str(reply.get("category", "")).strip().lower()
        if cat not in CATEGORIES:
            cat = fallback_cat  # keep the model's name, use the extension's folder
        if stem:
            return cat, stem
        print(f"  model gave no usable name: {raw[:120]!r}", file=sys.stderr)
    except Exception as e:  # show why instead of failing silently
        print(f"  model call failed: {type(e).__name__}: {e} {raw[:120]!r}", file=sys.stderr)
    return None


def unique(dest: Path) -> Path:
    """Never overwrite: add -2, -3, ... until the name is free."""
    if not dest.exists():
        return dest
    i = 2
    while True:
        cand = dest.with_name(f"{dest.stem}-{i}{dest.suffix}")
        if not cand.exists():
            return cand
        i += 1


def server_up(host: str) -> bool:
    try:
        urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=3).close()
        return True
    except OSError:
        return False


def plan(folder: Path, classify, limit=None):
    moves = []
    files = [p for p in sorted(folder.iterdir()) if p.is_file() and not p.name.startswith(".")]
    if limit:
        files = files[:limit]
    for i, p in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {p.name} ...", file=sys.stderr, flush=True)
        cat, stem = classify(p)
        dest = unique(folder / cat / (stem + p.suffix.lower()))
        # two files in this batch may pick the same target
        while any(dest == m[1] for m in moves):
            dest = unique(dest.with_name(f"{dest.stem}-x{dest.suffix}"))
        moves.append((p, dest))
    return moves


def apply(moves, folder: Path):
    done = []
    for src, dst in moves:
        dst.parent.mkdir(exist_ok=True)
        shutil.move(str(src), str(dst))
        done.append([str(dst), str(src)])
    (folder / LOG_NAME).write_text(json.dumps(done, indent=2))


def undo(folder: Path):
    log = folder / LOG_NAME
    if not log.exists():
        sys.exit("nothing to undo")
    for dst, src in reversed(json.loads(log.read_text())):
        if os.path.exists(dst) and not os.path.exists(src):
            shutil.move(dst, src)
    log.unlink()
    for d in folder.iterdir():  # drop category dirs we emptied
        if d.is_dir() and d.name in CATEGORIES and not any(d.iterdir()):
            d.rmdir()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--apply", action="store_true", help="actually move files (default: dry run)")
    ap.add_argument("--undo", action="store_true", help="revert the last --apply")
    ap.add_argument("--model", default="gemma3:4b", help="any Ollama model tag")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--limit", type=int, help="only process the first N files")
    ap.add_argument("--timeout", type=float, default=120, help="seconds to wait per file")
    ap.add_argument("--no-model", action="store_true", help="rules only, skip the LLM")
    a = ap.parse_args(argv)
    folder = a.folder.resolve()

    if a.undo:
        undo(folder)
        return print("undone")

    state = {"model_ok": not a.no_model}
    if state["model_ok"] and not server_up(a.host):
        state["model_ok"] = False
        print("(Ollama not reachable, using extension rules)", file=sys.stderr)
    elif state["model_ok"]:
        print(f"(first file may be slow while {a.model} loads)", file=sys.stderr, flush=True)

    def classify(p):
        if state["model_ok"]:
            res = ask_model(p, a.host, a.model, a.timeout, rule_category(p))
            if res:
                return res
            state["model_ok"] = False  # don't retry a dead server for every file
            print("(no local model reachable, using extension rules)", file=sys.stderr)
        return rule_category(p), slugify(p.stem) or "file"

    moves = plan(folder, classify, a.limit)
    for src, dst in moves:
        print(f"{src.name}  ->  {dst.relative_to(folder)}")
    if a.apply:
        apply(moves, folder)
        print(f"moved {len(moves)} files. revert with: sloth.py {a.folder} --undo")
    else:
        print(f"dry run: {len(moves)} files. add --apply to do it.")


if __name__ == "__main__":
    main()
