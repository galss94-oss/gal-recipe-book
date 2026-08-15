# gal-recipe-book — shared working agreement

**Read this before touching any file in this repo.**

Live site: https://galss94-oss.github.io/gal-recipe-book/ (GitHub Pages, serves `main`)

Gal works on this repo through **two separate Claude chats**. Neither can see the other's
conversation. This file is how they stay in sync — if you change the architecture or the
rules, update this file in the same commit.

| Chat | Owns | Touches |
|---|---|---|
| **"Recipe portal app"** | The app: design, layout, icons, manifest, features | `index.html`, `manifest.json`, `sw.js`, `icon-*.png`, `build.py` |
| **"Upload recipes"** | The content: adding recipes from NotebookLM PDFs | `recipes.json` (then run `build.py`) |

Generated, never hand-edited: `index.json`, `pages/*.jpg`.
Notes/tips data: `notes.json` (written by the app), `tips.json` (written by the daily task).

---

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

### Generated assets (added 2026-07-19)

`python3 build.py` reads `recipes.json` and writes:

* **`index.json`** (~80 KB) — id, title, desc, category, time, pageCount and a 180px
  thumbnail per recipe. This is the only file fetched at launch.
* **`pages/<id>-<n>.jpg`** — full-size page (1200px). Used by the **zoom viewer**.
* **`pagesv/<id>-<n>.jpg`** — 820px variants. Used by the **inline flow** (changed
  2026-08-12, see below). Both folders are live — `build.py` must keep writing both.

**How the iOS memory limit is handled (changed 2026-08-08).** iOS counts every decoded
image against a hard budget: 10 full-size pages is ~32 MB and iOS silently drops them
(blank or blurry pages). This was first solved by shrinking the inline images to 820px,
but that made the flow visibly softer than the zoom view. It is now solved by a **sliding
window** in `renderRecipe()`: only pages within `KEEP_MARGIN` (0.25) of a viewport
height beyond the screen stay decoded, the rest are set to a 1x1 blank. The
`aspect-ratio` rule on `.page-wrap img` holds the layout still when a page is blanked.
**Do not remove the window** — without it, full-size inline pages reintroduce the
blank/blurry bug.

**The window alone was not enough (changed 2026-08-12).** It bounds *distance*, not
*count*. At 402px a page renders only ~207px tall, so five or six fall inside the
window at once — for a 6-page recipe the window is effectively a no-op and ~15 MB of
full-size bitmap is resident. Gal reported b2 page 5 painted half-scanned. Measured in
a real browser at 402×874: 5 pages decoded at rest.

Fix, Gal's call after seeing `mockups/i1786565576264-9j4v.html`: **the inline flow now
serves `pagesv/` (820px) and the zoom viewer keeps `pages/` (1200px)** — `flowSrc()` in
`renderRecipe()`. Halves resident bitmap. This is the 820px approach that was reverted
on 2026-08-08 for softness; Gal chose it knowingly this time, because reading happens in
the zoom viewer and the flow is a scanning surface. **If he complains about softness
again, the next lever is fewer/larger pages on screen, not going back to 1200px inline.**

Rejected on the way, do not retry: **serialising decodes behind `img.decode()`**. Written
and executed at 402px — it stalls. `decode()` never settles for a page the compositor has
parked off screen, so the queue lock leaks and later pages never get a `src` at all.
Same reason `content-visibility:auto` must stay off `.page-wrap`.

**The window must be measured in pixels from the viewport, never in page indexes.**
An index-based window (`current ± 2`) shipped once and blanked pages that were still on
screen — at phone width a page is only ~200px tall, so four or five are visible at once
and the window could not cover them. Gal saw slides vanish and reappear while scrolling.
Invariant to preserve: **a page whose box touches the viewport is never unloaded.**

Launch payload went from 14 MB to ~80 KB. If a page image 404s, the app silently falls
back to the base64 copy in `recipes.json`, so a forgotten build degrades rather than
breaks — but a recipe added to `recipes.json` **will not appear at all** until
`build.py` runs, because it won't be in `index.json`.

### Cooking notes → tips (added 2026-07-19)

Gal can write personal notes on any recipe ("doubled the garlic, +5 min"). The loop:

* The **app** saves notes locally (IndexedDB) and, if a GitHub token is set in the app's
  ⚙︎ settings, PUSHes them to **`notes.json`** via the GitHub Contents API
  (`{ "<recipeId>": [ {id,text,ts}, ... ] }`). The token is the user's own fine-grained
  PAT, stored only in that device's browser — never in the repo.
* A **daily scheduled task** ("gal-recipe-tips") reads `notes.json`, and for each recipe
  with notes writes a concise Hebrew "שיפורים ותובנות" summary into **`tips.json`**
  (`{ "<recipeId>": {text, ts} }`), then commits + pushes. Style = KITCHEN_MENTOR.md.
* The **app** fetches `tips.json` on launch and shows that block above the recipe images.

**Precondition — check this first and stop if it fails.** If `notes.json` is absent, empty,
or unchanged since the last run, the task has nothing to do: say so in one line and exit
without reading `KITCHEN_MENTOR.md` or anything else. As of 2026-08-15 `notes.json` has
never existed, so every daily run so far has been a full session spun up to do nothing.

`tips.json` must stay valid JSON and is small — safe to edit programmatically. The task
must never touch `recipes.json`, `index.json`, `pages/`, or `index.html`. Notes are
*input*, tips are *output*; the recipe images themselves are never modified (if a note
implies a real method change, the task may also draft a NotebookLM prompt for Gal, but
does not regenerate anything itself).

### Report an issue → daily triage (added 2026-08-08)

A ⚑ button in the header, on every view, opens a report sheet: category buttons (one-tap
report — text is optional), optional dictation (`he-IL`, fills the textarea only), optional
screenshot (downscaled client-side to 1200px / JPEG 0.7). The page attaches its own context:
page, section, device class, and a **ZOOMED flag** when `innerWidth < screen.width * 0.95`
(a zoomed iPhone otherwise reports a narrow width and looks like an unknown small device).

Reports are written by the app to **`issues.json`** (array) using the same GitHub token as
notes; screenshots go to **`issues/<id>.jpg`**. No Google/Apps Script involved — the token
already existed, so this needs no setup and has no public endpoint.

Non-negotiables in the client (each fails silently if broken):
* Never show success unless the write was confirmed. Never clear the text on failure.
* Stop dictation BEFORE resetting the form, or a late result refills the box.
* A category with no text is a valid report — the client sends `[<category label>]`.

`gal-recipe-issue-triage` (daily 06:30) drains rows where `status` is `new`: views the
screenshot, scopes to the reported device unless the defect is cross-cutting, fixes bugs
in place, prepares features as mockups under `mockups/<issue-id>.html` and waits for Gal,
then writes `done <date>` / `awaiting approval` back. **It never deletes rows.**

---

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
