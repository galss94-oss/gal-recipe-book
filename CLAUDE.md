# gal-recipe-book — shared working agreement

**Read this before touching any file in this repo.**

Live site: https://galss94-oss.github.io/gal-recipe-book/ (GitHub Pages, serves `main`)

Gal works on this repo through **two separate Claude chats**. Neither can see the other's
conversation. This file is how they stay in sync — if you change the architecture or the
rules, update this file in the same commit.

| Chat | Owns | Touches |
|---|---|---|
| **"Recipe portal app"** | The app: design, layout, icons, manifest, features | `index.html`, `manifest.json`, `sw.js`, `icon-*.png`, `build.py` |
| **"Upload new recipes"** | The content: adding recipes from NotebookLM PDFs, and Gal's culinary voice | `recipes.json` (then run `build.py`), `KITCHEN_MENTOR.md` |

**Ownership change, 2026-08-30.** `gal-recipe-issue-triage` may now append to `recipes.json`
and run `build.py`, but **only** to drain `inbox/` (below). Nothing else about the split
changes: it still never edits `KITCHEN_MENTOR.md`, never rewrites existing recipes, and
still routes kitchen issues to the recipes chat. Gal asked for this deliberately — the
alternative was that a PDF he uploads from his phone sits unimported until he happens to
open the other chat, which defeats the point of uploading it. The rule this relaxes was
written when recipes lived inline in `index.html`, where any full-file write destroyed
them; the file split already removed that danger, and rule 4's `json.load`/`json.dump`
append is what keeps it safe now.

## Where the rest of the detail lives

This file holds only what every session needs. Job-specific detail moved out on 2026-08-31
because it was being loaded into every turn of every session in this repo, and it had grown
46% in sixteen days.

| If your job is | Read |
|---|---|
| draining `issues.json` — the daily triage task | `docs/TRIAGE.md` (issue routing, the report sheet, app vs. kitchen) |
| adding recipes, PDFs, notes or tips — the "Upload new recipes" chat | `docs/CONTENT.md` (generated assets, the phone inbox, the notes→tips loop) |
| anything else | this file is enough |

Read the one that matches the job, not both, and not before you know you have work to do.
The hard rules and the incident log below apply to everyone and stay here on purpose.

**Generated, never hand-edited:** `index.json`, `pages/`, `pagesv/` are all written by
`python3 build.py` from `recipes.json`. Editing them by hand is how they go stale silently.
`docs/CONTENT.md` has the detail.
## Architecture (changed 2026-07-18 — the part most likely to be stale in your head)

The app and the data are **separate files**:

* **`index.html`** (~35 KB) — the app only. Design, CSS, and all logic.
  It declares `let BUILTIN = [];` and populates it at startup via `fetchIndex()`,
  which fetches **`index.json`**. **It contains no recipe data.**
* **`recipes.json`** (~14 MB) — the recipe data and still the single source of truth.
  The app no longer loads it on launch (it did until 2026-07-19; that cost 14 MB per
  app open). It is now only a fallback if a generated file is missing. A plain JSON array:

```json
[{"id":"b1","title":"...","desc":"...","category":"...","time":30,
  "pages":["data:image/jpeg;base64,..."]}]
```

`pages` is one JPEG data URI per PDF page, rendered at **1200px wide, quality 0.72**
(matching the app's own in-browser PDF import). User-added recipes still live in
IndexedDB on the device and are unaffected.

Before this split, the recipes were a 10 MB inline array inside `index.html`.
**They are not there anymore.** If you are holding a copy of `index.html` that contains
`const BUILTIN = [{...}]`, it is stale — discard it and pull.

## Hard rules

1. **`git pull` before you edit.** Both chats push to `main`.
2. **Never rebuild `index.html` from a saved or generated copy.** Edit the current file
   in place (targeted find-and-replace on the real file). Writing a whole regenerated
   `index.html` is what caused every incident below.
3. **Never put recipe data into `index.html`.** Recipes go in `recipes.json`, appended
   with the next `b#` id.
4. **Don't hand-edit `recipes.json`** — it's one 14 MB line. Read it with `json.load`,
   append, `json.dump` back.
5. **After any change to `recipes.json`, run `python3 build.py`** and commit the
   regenerated `index.json` and `pages/` alongside it. Skipping this makes the new
   recipe invisible in the app. (Needs Pillow: `pip3 install pillow`.)
6. **Verify before pushing:** confirm the recipe count is what you expect
   (`python3 -c "import json;print(len(json.load(open('recipes.json'))))"`) and that the
   page still renders. Losing data is much worse than a slow commit.

## Deploying

Push to `main`; Pages rebuilds in ~1 min. Auth is the `gh` CLI (`gh auth setup-git`).
A service worker (`sw.js`) caches the app for offline use: the shell and `index.json` are
network-first so updates land on the next open, page images are cache-first. Bump
`VERSION` in `sw.js` when the shell changes so old caches are dropped.
If `gh` is missing (it has been installed to `/tmp` before and wiped), reinstall and
re-run the device-code login.

---

## Incident log — why rule 2 exists

Recipes b9 (פסטה קארי ירוק וקוקוס) and b10 (סלט חסה, אגסים ואגוזים מקורמלים) were
silently destroyed **three times**, by commits only meant to change the icon and the
home-screen title:

* `fa24619` "Add home-screen icon and web manifest" — wiped b9
* `8a89aa4` / `d6ef990` icon + title changes — wiped b9 and b10 again

Each rewrote `index.html` wholesale from a copy that predated the recipes. Nothing was
malicious and no one was careless about the icons — the failure was structural: the app
and the data lived in the same file, so any full-file write to the app destroyed the data.
The split fixed the structure. Rule 2 covers what the structure can't.

---

## Token discipline (added 2026-08-15)

These rules change *how* you work, never *what* you produce. They exist because this repo
holds a 22 MB data file and an 87 KB app file, so a careless read costs more than the edit.

1. **Never read `index.html` whole** (1,906 lines, ~22k tokens). It is a flat list of named
   functions - locate, then read the range:
   `grep -n "function renderRecipe" index.html` then read from that line with a limit.
   Commits here touch 10-48 lines, median ~25. Read at that scale, not at file scale.
2. **Never `Read` `recipes.json`, `index.json`, `pages/`, `pagesv/`** - denied in
   `.claude/settings.json`. Query instead:
   `python3 -c "import json;d=json.load(open('index.json'));print(len(d),[r['id'] for r in d])"`.
   To inspect a page image, print its size/dimensions with PIL; do not load it into context.
   (The deny list covers the `Read` tool only - `build.py` and any `python3` still work.)
3. **Bound anything that can spew.** `git log --oneline -10`, never `git log -p`.
   `git show --numstat`, never bare `git show`. Pipe uncertain output through `head`.
4. **Subagents for fan-out, not for known targets.** "Which functions touch the decode
   window?" is a subagent that returns a short list. "Read lines 962-1084" is not - a
   subagent re-pays its whole system prompt and costs more than the read it replaces.
   Judge a subagent by what it returns: a paragraph is a win, a wall of text is a loss.
5. **Model routing.** Subagents that read, search, count or check formatting run `haiku`;
   implementation subagents run `sonnet`. Set it in the agent definition, not per call.
   The main session is never downgraded.
6. **One task per session, and stop when done.** Each daily task gets a fresh session -
   never resume yesterday's. A task with nothing to do says so and exits; it does not go
   looking for work to justify the run.

Cooking and recipe-writing instructions for Gal live in `KITCHEN_MENTOR.md`.
