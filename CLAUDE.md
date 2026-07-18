# gal-recipe-book — shared working agreement

**Read this before touching any file in this repo.**

Live site: https://galss94-oss.github.io/gal-recipe-book/ (GitHub Pages, serves `main`)

Gal works on this repo through **two separate Claude chats**. Neither can see the other's
conversation. This file is how they stay in sync — if you change the architecture or the
rules, update this file in the same commit.

| Chat | Owns | Touches |
|---|---|---|
| **"Recipe portal app"** | The app: design, layout, icons, manifest, features | `index.html`, `manifest.json`, `icon-*.png` |
| **"Upload recipes"** | The content: adding recipes from NotebookLM PDFs | `recipes.json` |

---

## Architecture (changed 2026-07-18 — the part most likely to be stale in your head)

The app and the data are **separate files**:

* **`index.html`** (~27 KB) — the app only. Design, CSS, and all logic.
  It declares `let BUILTIN = [];` and populates it at startup via `fetchRecipes()`,
  which fetches `recipes.json`. **It contains no recipe data.**
* **`recipes.json`** (~13 MB) — the recipe data. A plain JSON array:

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

---

## Hard rules

1. **`git pull` before you edit.** Both chats push to `main`.
2. **Never rebuild `index.html` from a saved or generated copy.** Edit the current file
   in place (targeted find-and-replace on the real file). Writing a whole regenerated
   `index.html` is what caused every incident below.
3. **Never put recipe data into `index.html`.** Recipes go in `recipes.json`, appended
   with the next `b#` id.
4. **Don't hand-edit `recipes.json`** — it's one 13 MB line. Read it with `json.load`,
   append, `json.dump` back.
5. **Verify before pushing:** confirm the recipe count is what you expect
   (`python3 -c "import json;print(len(json.load(open('recipes.json'))))"`) and that the
   page still renders. Losing data is much worse than a slow commit.

## Deploying

Push to `main`; Pages rebuilds in ~1 min. Auth is the `gh` CLI (`gh auth setup-git`).
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

Cooking and recipe-writing instructions for Gal live in `KITCHEN_MENTOR.md`.
