# Triage reference

Split out of `CLAUDE.md` on 2026-08-31. Read this when you are draining
`issues.json`. The hard rules and the incident log stay in `CLAUDE.md` — read that too.
### Issue routing — app vs. kitchen (added 2026-08-23)

Gal files reports from the app's 🏳 flag button into `issues.json`. The daily
`gal-recipe-issue-triage` task drains that queue. Two kinds of report exist, and they
belong to different owners:

* **App issues** — how the book *presents* a recipe (layout, contrast, tap targets,
  images not loading). The triage task fixes these itself, or mocks them up and sets
  `status: "awaiting approval"`.
* **Kitchen issues** — what a recipe *says*: the NotebookLM prompt template, measurement
  rules, spice breakdown, ingredient grouping, cooking style. The triage task **cannot
  act on these** — recipe pages are baked images, and the rules live in
  `KITCHEN_MENTOR.md`, owned by the "Upload new recipes" chat.

Routing: triage sets `status: "awaiting kitchen"` on a kitchen issue and stops.
**The "Upload new recipes" chat checks for `awaiting kitchen` rows at the start of every
session**, decides, edits `KITCHEN_MENTOR.md`, and closes the row with
`status: "done <date>"` plus a `resolution` line. A rule only applies to prompts written
after it lands — existing recipe images are never regenerated.

Generated, never hand-edited: `index.json`, `pages/*.jpg`.
Notes/tips data: `notes.json` (written by the app), `tips.json` (written by the daily task).

---

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

**The request sheet does two jobs (changed 2026-08-30).** `openRequest()` opens the same
sheet with a segmented control: *בקשת מתכון* (ask Claude) or *העלאת PDF* (import a PDF you
already have). The upload side does **not** re-implement the PDF pipeline — `rpPickPdf()`
closes the sheet, calls `openAdd()` and clicks `#pdfInput`, so `onFileChosen()` in the add
view stays the only parser. Keep that handoff synchronous: iOS opens a file picker only
inside a user gesture, and an `await` before `.click()` silently does nothing.
Gal filed this as a missing feature (i1788047202706-47bq) while it already existed behind
the unlabelled round `+` — the defect was discoverability, not capability. The `+` FAB
still works and is unchanged.

**Sending shows a confirmation state, not a toast (changed 2026-08-30).** `rpShowDone()`
hides the form and shows `#rpDone` with the row id; it closes on Gal's tap. The old
version printed 13.5px of green text and auto-closed after 1400ms, and Gal reported never
seeing it (i1788047242017-dhik). Do not reintroduce a timer here.
Same issue: `renderRequests()` used to filter `category === 'request'`, so bug reports and
ideas appeared nowhere after sending and looked lost. It now lists every row, newest
first, with four states — `new` → ממתין, `awaiting approval` → ממתין לאישורך,
`awaiting kitchen` → אצל צ'אט המתכונים, anything else → טופל. **A new status value written
by the triage task must be added to `RQ_STATES` or it silently renders as טופל.**

**The list is not on the home screen any more (changed 2026-09-02, i1788153988954-3pes).**
Six rows took ~480px at 402×874, so the categories, the favourites and "בישלת לאחרונה" all
sat below the fold and the book opened on no recipes. Gal was shown three mockups and chose
**option B: home carries zero reports.** `renderRequests()` now fills `#reqList` inside
`#reportOverlay`, under a "הבקשות שלי" tab next to "דיווח חדש", and renders **every** row —
the cap of six existed only because the list was competing with the recipes.
The single entry point is ⚑, so `refreshReportBadge()` puts a count on that button; it counts
`awaiting approval` only. A `new` row is waiting on this task, not on Gal, and badging it
would teach him to ignore the badge — which matters more than usual now, because with the
home screen clear a mockup he never opens is invisible. The tabs are shown only in the ⚑
flow: `openRequest()` already uses `.rp-seg` for ask/upload, and two stacked segmented
controls read as one broken one.

## The inbox — also this task's queue (added 2026-08-31)

`gal-recipe-issue-triage` drains two queues, not one: `issues.json` (bug and feature reports)
and `inbox/` (PDFs Gal pushed from his phone with "שלח לכל המכשירים").

The client half writes `inbox/<id>.pdf` plus `inbox/<id>.json`. `import_inbox.py` is the other
half and works — but until 2026-08-31 nothing called it, so uploads sat in `inbox/` forever
while the button told Gal "✓ נשלח. אכניס אותו לספר בבוקר". The task prompt now drains it.

Render geometry, the sidecar format, and the failure handling live in `docs/CONTENT.md`
under "Inbox". Read that section only when an import fails or you are changing the importer —
`import_inbox.py --dry-run` tells you what it would do without touching anything.
