#!/usr/bin/env python3
"""Import PDFs the app pushed to inbox/ into recipes.json, then run build.py.

The app (pushRecipeToInbox in index.html) writes two files per upload:
  inbox/<id>.pdf   the original PDF, untouched
  inbox/<id>.json  the fields Gal reviewed on screen: title, desc, category, time

This script is the other half. It exists so the daily task does not re-improvise PDF
rendering every morning - the page geometry here must stay identical to the in-browser
importer (1200px wide, JPEG quality 0.72) or pages imported from the phone will not match
pages imported on the desktop.

Safety: recipes.json is read with json.load and written with json.dump (never hand-edited,
per CLAUDE.md rule 4), the recipe count is asserted before and after, and an inbox file is
deleted only after its recipe is actually in the file.

  python3 import_inbox.py            # import, build, delete the consumed inbox files
  python3 import_inbox.py --dry-run  # report what it would do, touch nothing
"""
import base64, io, json, os, re, sys, subprocess

ROOT     = os.path.dirname(os.path.abspath(__file__))
INBOX    = os.path.join(ROOT, 'inbox')
RECIPES  = os.path.join(ROOT, 'recipes.json')
PAGE_W   = 1200      # must match onFileChosen() in index.html
PAGE_Q   = 72        # must match its toDataURL('image/jpeg', 0.72)
DRY      = '--dry-run' in sys.argv


def render_pages(pdf_path):
    """PDF -> list of JPEG data URIs, one per page, matching the browser importer."""
    import fitz                      # pymupdf
    from PIL import Image
    out = []
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            raise ValueError('the PDF has no pages')
        for page in doc:
            scale = PAGE_W / page.rect.width
            pix   = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            im    = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
            buf   = io.BytesIO()
            im.save(buf, 'JPEG', quality=PAGE_Q, optimize=True)
            out.append('data:image/jpeg;base64,' +
                       base64.b64encode(buf.getvalue()).decode('ascii'))
    return out


def next_builtin_id(recipes):
    """Next free b# - never reuse the p... id the phone generated."""
    used = {int(m.group(1)) for r in recipes
            for m in [re.fullmatch(r'b(\d+)', str(r.get('id', '')))] if m}
    return 'b' + str(max(used, default=0) + 1)


def load_jobs():
    jobs = []
    if not os.path.isdir(INBOX):
        return jobs
    for name in sorted(os.listdir(INBOX)):
        if not name.endswith('.json'):
            continue
        path = os.path.join(INBOX, name)
        try:
            meta = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            print('SKIP %s - unreadable sidecar: %s' % (name, e))
            continue
        if meta.get('status') != 'new':
            continue
        pdf = os.path.join(ROOT, meta.get('file') or '')
        if not os.path.isfile(pdf):
            # the app uploads the PDF first, so this means a genuinely broken row
            print('SKIP %s - sidecar points at a missing PDF (%s)' % (name, meta.get('file')))
            continue
        jobs.append((path, pdf, meta))
    return jobs


def mark_failed(sidecar, meta, reason):
    meta['status'] = 'failed'
    meta['resolution'] = reason
    if not DRY:
        json.dump(meta, open(sidecar, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)


def main():
    jobs = load_jobs()
    if not jobs:
        print('inbox is empty - nothing to import')
        return 0

    recipes = json.load(open(RECIPES, encoding='utf-8'))
    before  = len(recipes)
    print('recipes before: %d | pending uploads: %d' % (before, len(jobs)))

    imported, failed, consumed = [], [], []
    for sidecar, pdf, meta in jobs:
        title = (meta.get('title') or '').strip() or '(ללא שם)'
        try:
            pages = render_pages(pdf)
        except Exception as e:
            print('FAIL  %s - %s' % (title, e))
            mark_failed(sidecar, meta, 'רינדור ה-PDF נכשל: %s' % e)
            failed.append((title, str(e)))
            continue
        rid = next_builtin_id(recipes)
        recipes.append({
            'id':       rid,
            'title':    title,
            'desc':     (meta.get('desc') or '').strip(),
            'category': (meta.get('category') or '').strip(),
            'time':     meta.get('time'),
            'pages':    pages,
        })
        want = meta.get('pageCount')
        note = '' if not want or want == len(pages) else \
               '  (the phone counted %s pages, this render made %d)' % (want, len(pages))
        print('OK    %s -> %s, %d pages%s' % (title, rid, len(pages), note))
        imported.append((rid, title, meta.get('category'), len(pages)))
        consumed.append((sidecar, pdf))

    if not imported:
        print('nothing imported')
        return 1 if failed else 0
    if DRY:
        print('\n--dry-run: recipes.json, build.py and inbox/ left untouched')
        return 0

    # single write, then re-read from disk and assert - losing recipes is the one
    # failure this repo has actually suffered (see the incident log in CLAUDE.md)
    json.dump(recipes, open(RECIPES, 'w', encoding='utf-8'), ensure_ascii=False)
    after = len(json.load(open(RECIPES, encoding='utf-8')))
    if after != before + len(imported):
        print('ABORT recipes.json holds %d, expected %d - not deleting anything'
              % (after, before + len(imported)))
        return 2
    print('recipes after: %d' % after)

    r = subprocess.run([sys.executable, 'build.py'], cwd=ROOT)
    if r.returncode != 0:
        print('ABORT build.py failed - inbox kept so the import can be retried')
        return 3

    index = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
    if len(index) != after:
        print('ABORT index.json holds %d, recipes.json %d - inbox kept' % (len(index), after))
        return 4

    # only now is the upload genuinely consumed
    for sidecar, pdf in consumed:
        os.remove(sidecar)
        os.remove(pdf)
    print('deleted %d inbox file pairs' % len(consumed))

    print('\nIMPORTED:')
    for rid, title, cat, n in imported:
        print('  %s  %s  [%s]  %d עמודים' % (rid, title, cat, n))
    if failed:
        print('FAILED (left in inbox/):')
        for title, why in failed:
            print('  %s - %s' % (title, why))
    return 0


if __name__ == '__main__':
    sys.exit(main())
