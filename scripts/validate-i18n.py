#!/usr/bin/env python3
"""Validate the single-file bilingual decks.

For each HTML file (default: index.html + the three decks) checks:
  1. RU and EN i18n key sets are identical            (hard error if not)
  2. every data-i="..." attribute resolves to an EN key (hard error)
  3. i18n keys never used as data-i                    (info; may be JS-dynamic, e.g. rec.s*)
  4. the <script> block passes `node --check`          (if node is installed)

Exit code is non-zero if any hard error is found. Run from the repo root:
    python3 scripts/validate-i18n.py
    python3 scripts/validate-i18n.py chat-cowork-code.html
"""
import sys, re, subprocess, shutil

DEFAULT = ["index.html", "chat-cowork-code.html", "claude-code-context.html", "auto-mode.html"]
KEY = r'(?:[,{]\s*|\n\s*)"([^"]+)":'          # an object key at a valid position
have_node = shutil.which("node") is not None


def lang_block(html, name):
    if name == "ru":
        m = re.search(r'\bru:\{(.*?)\n\s*\},\s*\n?\s*en:\{', html, re.S)
    else:
        m = re.search(r'\ben:\{(.*?)\n\s*\}\s*\n?\s*\};', html, re.S)
    return m.group(1) if m else ""


def check(path):
    errors, infos = [], []
    html = open(path, encoding="utf-8").read()
    used = set(re.findall(r'data-i="([^"]+)"', html))
    rk = set(re.findall(KEY, lang_block(html, "ru")))
    ek = set(re.findall(KEY, lang_block(html, "en")))

    if not rk or not ek:
        errors.append("could not parse ru/en i18n blocks")
    if rk != ek:
        if rk - ek:
            errors.append(f"keys only in RU: {sorted(rk - ek)}")
        if ek - rk:
            errors.append(f"keys only in EN: {sorted(ek - rk)}")
    missing = used - ek
    if missing:
        errors.append(f"data-i with no i18n key: {sorted(missing)}")
    unused = ek - used
    if unused:
        infos.append(f"i18n keys not used as data-i (ok if used in JS, e.g. rec.s*): {sorted(unused)}")

    if have_node:
        m = re.search(r'<script>(.*?)</script>', html, re.S)
        if m:
            tmp = "/tmp/_validate_i18n.js"
            open(tmp, "w").write(m.group(1))
            r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
            if r.returncode != 0:
                errors.append("JS syntax error: " + r.stderr.strip()[:200])
    return errors, infos


def main(argv):
    files = argv[1:] or DEFAULT
    bad = 0
    for f in files:
        errors, infos = check(f)
        status = "OK " if not errors else "FAIL"
        print(f"[{status}] {f}")
        for i in infos:
            print(f"    info:  {i}")
        for e in errors:
            print(f"    ERROR: {e}")
        bad += len(errors) > 0
    if not have_node:
        print("note: `node` not found — skipped JS syntax check")
    print(f"\n{len(files)} file(s), {bad} with errors.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
