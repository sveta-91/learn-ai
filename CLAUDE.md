# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A set of standalone, single-file HTML "learning decks" that teach how to work with Claude Code. Each `.html` file is a complete, self-contained interactive presentation (inline CSS + JS, no dependencies, no build step). They are published via GitHub Pages — the file served as the site root must be named `index.html` (see commit `Rename to index.html for GitHub Pages`).

Current files:
- `index.html` — course chooser / landing page. The GitHub Pages root; links out to the three decks in order. Same design system and i18n pattern as the decks but no module navigation (it's a single static page).
- `chat-cowork-code.html` — "Chat · Cowork · Code" (Course 01, the foundational overview): the three Claude modes (Chat/Cowork/Code) × the four surfaces (browser/desktop/terminal/`claude -p`), connectors/MCP, limitations, examples. 7 modules (0–6). Includes an interactive "what should I pick" helper (`pick()`).
- `claude-code-context.html` — "Project and its Context" (Course 02). CLAUDE.md, @-imports, rules/, settings, agents, skills, MCP. 9 modules (0–8).
- `auto-mode.html` — "Steps to Agents" (Course 03). (Was previously `index.html` before the chooser took that name.)
- `CNAME` — the GitHub Pages custom domain (`wanna-know-ai.com`).
- `scripts/` — maintainer tooling, not served by the site: `validate-i18n.py` (deck sanity check), `cf-analytics.py` (pull visitor stats), and `rename-course.py` (rename a course across chooser + nav + title + brand, bilingually).

There is no package manager, bundler, test runner, or lint config. To preview, open the file directly in a browser or serve the directory statically (e.g. `python3 -m http.server`).

## Architecture (shared by every deck)

Each file follows the same pattern, so changes to one usually apply to the other:

1. **Inline design system** in a single `<style>` block. Shared tokens live in `:root` (`--ink`, `--paper`, `--rust`, `--moss`, `--gold`, `--line`). Fonts: Fraunces (headings), Newsreader (body), Spline Sans Mono (labels/code), loaded from Google Fonts. Keep new decks consistent with this palette and these fonts.

2. **Module-based navigation.** Content is split into `.module` blocks tagged `data-mod="N"`. Only one is visible at a time (`.module.active`). `go(i)` switches modules, toggles the active nav button, and scrolls to top. The top nav is rebuilt from the `navTitles` object by `buildNav()`.

3. **Bilingual content via i18n, not hardcoded text.** This is the most important convention. Visible text is NOT written inline in the HTML — elements carry a `data-i="<key>"` attribute and are filled at runtime. All strings live in a single JS object `const I = { ru: {...}, en: {...} }`. `setLang(l)` walks every `[data-i]` element and sets `el.innerHTML = I[l][key]`.
   - **Editing content = editing the `I` object**, not the HTML body. Adding/removing a `data-i` element requires adding/removing the matching key in **both** `ru` and `en`.
   - Values may contain HTML (`<strong>`, `<code>`, etc.) since they're assigned via `innerHTML`.
   - `navTitles` (and any other JS-built UI like quiz questions) also has per-language arrays/keys — keep these in sync with module count.
   - Default language is set by the `setLang('en')` call at the very end of the script.

4. **Interactive widgets** are plain JS reading the same `I[lang]` dictionary. E.g. `claude-code-context.html` has an offline "repo-context builder" — a weighted checklist (`checked`/`weights`, `buildQuestions()`, `toggleQ()`, `runEvaluate()`) that scores readiness and pulls verdict/`miss.*`/`have.*` strings from `I`.

## Cross-course navigation

Each deck links to its neighbours so the three read as a sequence (order = the chooser order: `chat-cowork-code` → `claude-code-context` → `auto-mode`):
- The header **brand is an `<a href="index.html">`** with a leading `←` (`.home` span) — a persistent "back to all courses".
- A **`.coursenav` rail above the footer** holds "All courses" (centre) plus Prev/Next *course* links with the neighbour's short name (`cn.prev*`/`cn.next*` i18n keys). It's a 3-column grid; the missing side on the first/last deck is an empty `<span></span>` to keep "All courses" centred. This is separate from the in-module `.pager` (prev/next *module*).
- When adding or reordering courses, update each affected deck's rail `href`s and the `cn.prev`/`cn.next` neighbour-name keys (both `ru` and `en`), and the chooser cards in `index.html`.

## Working conventions

- **Keep `ru` and `en` key sets identical.** A key present in one language and missing in the other shows blank in that language. When adding content, add the `data-i` element plus both translations together.
- When renaming the published entry point, the file must end up named `index.html` for GitHub Pages to serve it.
- Edits are content-only inside existing single-file decks; there is nothing to compile or test beyond opening the page and checking both EN and RU render and every module navigates.
- **Validate before committing:** `python3 scripts/validate-i18n.py` checks RU/EN key balance, that every `data-i` resolves, and that each `<script>` passes `node --check`. (Keys used only from JS — quiz/eval widgets, the `rec.s*` recommendations — show as "info", not errors.)
- When embedding images, inline them as base64 data URIs to keep each deck a self-contained single file (no external asset files).

## Deployment & ops

- **GitHub Pages from `main` / root**, no build step: commit, push, and Pages rebuilds in ~30–60s. The live site is the **custom domain `wanna-know-ai.com`** (set via `CNAME`); the `https://sveta-91.github.io/learn-ai/` URL **301-redirects** there, so both funnel to one site.
- **Verify after pushing:** poll `https://wanna-know-ai.com/<page>` (follow redirects) until the change appears before calling it done.
- Pages is served directly by GitHub/Fastly — **not** proxied through Cloudflare, even though the domain's DNS lives on a Cloudflare account.
- Gotcha: `index.html` was once left read-only (`chmod 444`), blocking writes — restore to `644` if a write fails.
- **Analytics:** a Cloudflare Web Analytics JS beacon sits before `</body>` on every page (one per file — don't duplicate). Pull stats with `python3 scripts/cf-analytics.py` (needs `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` in the environment). Only real browser hits count; bots and `curl` are excluded, with a few-minutes ingestion lag.
