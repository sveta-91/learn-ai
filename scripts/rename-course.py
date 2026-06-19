#!/usr/bin/env python3
"""Rename a course across the whole site, consistently and bilingually.

A course name appears in several places, each with a different phrasing:
  - the chooser card title in index.html        (long, with <em> emphasis)
  - the cross-course nav links in the NEIGHBOUR decks (short, plain)
  - the deck's own browser <title>
  - (optionally) the deck's header brand
This script edits each location by STRUCTURE (i18n key / chooser order),
not by find-replacing a single string — because the strings differ.

Usage (dry-run prints the plan; add --apply to write):
  python3 scripts/rename-course.py auto-mode.html \
      --en "Agent vs <em>Project</em>" --ru "Агент vs <em>Проект</em>" --apply

Options:
  --en / --ru          chooser card title (may include <em>…</em>). REQUIRED.
  --short-en/--short-ru  short name for neighbour nav links (default: --en/--ru with <em> stripped)
  --title              browser <title> text for the deck (default: stripped --en)
  --brand-en/--brand-ru  also set the deck's header brand i18n value (optional)
  --root DIR           repo root (default: current dir)
  --apply              write changes (otherwise just print the plan)

After running, also: update CLAUDE.md's file list by hand, re-theme the deck
body/eyebrow/footer if the meaning changed, and run scripts/validate-i18n.py.
"""
import argparse, re, sys, os

EM = re.compile(r'</?em>')
strip_em = lambda s: EM.sub('', s)


def block_span(html, lang):
    """(start,end) of the inner text of the ru:{…} or en:{…} i18n block."""
    if lang == 'ru':
        m = re.search(r'\bru:\{(.*?)\n\s*\},\s*\n?\s*en:\{', html, re.S)
    else:
        m = re.search(r'\ben:\{(.*?)\n\s*\}\s*\n?\s*\};', html, re.S)
    if not m:
        raise SystemExit(f"  ! could not locate {lang} i18n block")
    return m.start(1), m.end(1)


def set_key(html, key, value, lang):
    """Set "key":"…" inside the given language block. Returns (html, changed?)."""
    s, e = block_span(html, lang)
    block = html[s:e]
    pat = re.compile(r'("%s"\s*:\s*")[^"]*(")' % re.escape(key))
    new_block, n = pat.subn(lambda m: m.group(1) + value + m.group(2), block)
    if n == 0:
        return html, False
    if n > 1:
        raise SystemExit(f"  ! key {key} matched {n}× in {lang} block (ambiguous)")
    return html[:s] + new_block + html[e:], True


def set_title(html, value):
    new, n = re.subn(r'(<title>).*?(</title>)', lambda m: m.group(1) + value + m.group(2), html, count=1, flags=re.S)
    return new, n == 1


def chooser_order(index_html):
    """Ordered [(href, cKey)] from the chooser cards in index.html."""
    return re.findall(r'<a class="card"[^>]*href="([^"]+)"[\s\S]*?data-i="(c\d+)\.h"', index_html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck", help="target deck filename, e.g. auto-mode.html")
    ap.add_argument("--en", required=True)
    ap.add_argument("--ru", required=True)
    ap.add_argument("--short-en"); ap.add_argument("--short-ru")
    ap.add_argument("--title")
    ap.add_argument("--brand-en"); ap.add_argument("--brand-ru")
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    short_en = a.short_en or strip_em(a.en)
    short_ru = a.short_ru or strip_em(a.ru)
    tab = a.title or strip_em(a.en)
    root = a.root
    p = lambda f: os.path.join(root, f)

    index = open(p("index.html"), encoding="utf-8").read()
    order = chooser_order(index)
    hrefs = [h for h, _ in order]
    if a.deck not in hrefs:
        raise SystemExit(f"{a.deck} is not a chooser card (have: {hrefs})")
    i = hrefs.index(a.deck)
    ckey = dict(order)[a.deck]
    prev_deck = hrefs[i - 1] if i > 0 else None
    next_deck = hrefs[i + 1] if i < len(hrefs) - 1 else None

    # old names (for the plan printout)
    old_en, _ = set_key(index, f"{ckey}.h", "X", "en")  # just to confirm it exists
    cur = re.search(r'"%s\.h"\s*:\s*"([^"]*)"' % re.escape(ckey),
                    index[block_span(index, "en")[0]:block_span(index, "en")[1]])
    print(f"Course {ckey[1:]} ({a.deck}):  '{cur.group(1) if cur else '?'}'  ->  '{a.en}'")
    print(f"  short (nav): '{short_en}' / '{short_ru}'   tab <title>: '{tab}'")
    print(f"  prev deck: {prev_deck or '—'}   next deck: {next_deck or '—'}")

    # Plan: (file, description, mutation)
    jobs = []

    def upd(fn, html):
        h = html
        h, c1 = set_key(h, f"{ckey}.h", a.en, "en");
        # chooser only owns the cN.h key; this fn is reused below per-file
        return h

    # 1) chooser titles
    def f_index(h):
        changed = []
        h, c = set_key(h, f"{ckey}.h", a.en, "en"); changed.append(("chooser "+ckey+".h en", c))
        h, c = set_key(h, f"{ckey}.h", a.ru, "ru"); changed.append(("chooser "+ckey+".h ru", c))
        return h, changed
    jobs.append(("index.html", f_index))

    # 2) deck's own <title> (+ optional brand)
    def f_deck(h):
        changed = []
        h, c = set_title(h, tab); changed.append(("<title>", c))
        if a.brand_en is not None:
            h, c = set_key(h, "brand", a.brand_en, "en"); changed.append(("brand en", c))
        if a.brand_ru is not None:
            h, c = set_key(h, "brand", a.brand_ru, "ru"); changed.append(("brand ru", c))
        return h, changed
    jobs.append((a.deck, f_deck))

    # 3) neighbour nav links
    if prev_deck:
        def f_prev(h):
            ch = []
            h, c = set_key(h, "cn.next", short_en, "en"); ch.append(("cn.next en", c))
            h, c = set_key(h, "cn.next", short_ru, "ru"); ch.append(("cn.next ru", c))
            return h, ch
        jobs.append((prev_deck, f_prev))
    if next_deck:
        def f_next(h):
            ch = []
            h, c = set_key(h, "cn.prev", short_en, "en"); ch.append(("cn.prev en", c))
            h, c = set_key(h, "cn.prev", short_ru, "ru"); ch.append(("cn.prev ru", c))
            return h, ch
        jobs.append((next_deck, f_next))

    print("\nPlanned edits:")
    results = []
    for fn, fn_apply in jobs:
        html = open(p(fn), encoding="utf-8").read()
        new, changed = fn_apply(html)
        for what, ok in changed:
            print(f"  {'✓' if ok else '–'} {fn}: {what}{'' if ok else ' (not found, skipped)'}")
        results.append((fn, new, html != new))

    if not a.apply:
        print("\n(dry run — re-run with --apply to write)")
        return
    for fn, new, dirty in results:
        if dirty:
            open(p(fn), "w", encoding="utf-8").write(new)
    print("\nApplied. Now: update CLAUDE.md's file list, re-theme deck body/eyebrow if")
    print("the meaning changed, then run:  python3 scripts/validate-i18n.py")


if __name__ == "__main__":
    main()
