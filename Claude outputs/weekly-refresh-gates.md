# Dashboard weekly refresh — three gates

All three are edits to the task's Instructions box. I can't make them myself: the task prompt
lives in Claude's app data folder, and `_regen/` isn't reachable from my session either.

Each one replaces "do the check every week" with "check cheaply first, do the work only when
there is work". None of them removes a check — they change when it fires.

---

## W1 · Column D — make it an assertion, not a memory

**Find**, in STEP 1:

    **If a ticker was added to the sheet since the last run, extend column D to its row in BOTH the master and the mirror** — a missing D means that ticker's row silently loses its day change, and nothing else complains.

**Replace with:**

    **If a ticker was added to the sheet since the last run, extend column D to its row in BOTH the master and the mirror** — a missing D means that ticker's row silently loses its day change, and nothing else complains. Do not eyeball it; after refreshing the mirror, run:

        python3 -c "import base64,csv,io; rows=list(csv.reader(io.StringIO(base64.b64decode(open('iPad Dashboards/_regen/liveprices.b64').read()).decode()))); bad=[r[0] for r in rows[1:] if r and r[0].strip() and (len(r)<4 or not r[3].strip())]; print('MISSING PrevClose (col D):', ', '.join(bad) if bad else 'none')"

    Anything other than `none` names the tickers to fix in BOTH sheets before you continue.

---

## W2 · CBS property index — only look when a period could plausibly exist

**Find**, in STEP 2:

    Property: check whether the CBS home-price index has published a period newer than the last in

**Replace the opening of that paragraph with:**

    Property — CHECK THE GATE BEFORE YOU SEARCH. Read the last `period` in `Projects/Master project/memory/property.json`. The index is roughly bi-monthly, so **if that period is less than 6 weeks old, write "property: index not due" and skip this item entirely** — no search, no lookup. Most weeks land here and that is the expected outcome, not a shortcut.

    Only when the last recorded period is 6+ weeks old: check whether the CBS home-price index has published a period newer than the last in

Everything after that phrase stays exactly as it is, including "Only add a period confirmed by a
source."

---

## W3 · Unity — grep before you search

**Find** the line in STEP 3b:

    Unity reports roughly early Feb / May / Aug / Nov. **If Unity has reported since the last run,**

**Insert immediately BEFORE it:**

    ESTABLISH THIS FROM THE FILE FIRST — IT IS A GREP, NOT A SEARCH. Unity reports four times a year, so roughly 48 weeks in 52 there is nothing to do here and finding that out must be cheap:

        grep -n -m1 -A3 'UNITY_EARNINGS' "Artifacts/rsu-dashboard-live/index.html"

    That prints `asOf`, `quarter` and `nextDue`. Then:

    - `nextDue` is a **future** date → no print has happened. Write "Unity: no new print" and move on. Do not search investor relations, do not open a summary article, do not check the price.
    - `nextDue` has **passed**, or is **null** → a print may have happened. Now do the work below.

    Reaching for investors.unity.com to discover that nothing was published is the expensive way to learn what the file already knows.

---

## Then verify

In the Instructions box, search for these three — all must be present:

    MISSING PrevClose (col D)
    property: index not due
    IT IS A GREP, NOT A SEARCH

And these must still be there — if any is missing, something was deleted by accident:

    FRESHNESS GATE
    Non-zero exit = DO NOT DEPLOY
    Only add a period confirmed by a source
    never from a summary article
    must NEVER be pushed to a branch
    do not "fix" that guard

---

## What this changes

Nothing about what gets fetched. Prices, crypto, funds, cards, pension, FX, earnings all still
refresh exactly as they do now, and every gate that blocks a bad deploy still blocks it.

What changes is the cost of discovering that nothing changed — which, for the property index and
Unity, is most weeks of the year.
