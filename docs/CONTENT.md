# Content reference

Split out of `CLAUDE.md` on 2026-08-31. Read this when you are adding recipes,
handling an uploaded PDF, or working on the notes→tips loop. The hard rules and the incident
log stay in `CLAUDE.md` — read that too.
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

### Inbox — a PDF uploaded from the phone reaches every device (added 2026-08-30)

Gal's ask: upload a PDF on the phone, have it land in the book on *all* devices, and have
the uploaded file deleted afterwards. `saveNewRecipe()` only ever wrote to IndexedDB on
one device; this is the path that crosses devices.

The app's **הוסף מתכון** view now has two buttons. **שמור במכשיר הזה** is the old local
save. **שלח לכל המכשירים** calls `pushRecipeToInbox()`, which writes two files with the
GitHub token already in ⚙︎ settings:

* `inbox/<id>.pdf` — the original PDF, unmodified, via `ghPutBinary`. Capped at 20 MB.
* `inbox/<id>.json` — `{id, title, desc, category, time, file, pageCount, status:"new",
  ts, device, version}`. These are the fields **Gal reviewed and corrected on screen**,
  so the import never has to guess them.

The PDF is uploaded first on purpose: a sidecar pointing at a missing file is a broken
row, whereas a PDF with no sidecar is inert and harmless.

**Draining it (the daily task's job).** For each `inbox/*.json` with `status: "new"`:

1. Render the PDF to JPEG pages at **1200px wide, quality 0.72** — the format
   `recipes.json` expects and exactly what the in-browser importer produces.
2. `json.load` `recipes.json`, append `{id, title, desc, category, time, pages}` with the
   next free `b#` id (**not** the `p…` inbox id), `json.dump` back. Never hand-edit it.
3. Run `python3 build.py`, then confirm the recipe count went up by exactly the number
   imported. If it did not, **stop and tell Gal** — do not push.
4. `git rm` both `inbox/<id>.pdf` and `inbox/<id>.json`. This is the deletion Gal asked
   for. Be honest about its limit: it removes them from the current tree, but the blob
   stays in git history forever. Fine for recipes; say so rather than implying otherwise.
5. Report each imported recipe by name in the Hebrew summary, so Gal can catch a wrong
   category the morning it happens rather than months later.

If a PDF fails to render, leave both files in place, set `status` to `"failed"` with a
`resolution` line, and report it. Never delete a file you could not import.

`gal-recipe-issue-triage` (daily 06:30) drains rows where `status` is `new`: views the
screenshot, scopes to the reported device unless the defect is cross-cutting, fixes bugs
in place, prepares features as mockups under `mockups/<issue-id>.html` and waits for Gal,
then writes `done <date>` / `awaiting approval` back. **It never deletes rows.**

---

