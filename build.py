#!/usr/bin/env python3
"""
Build the fast-loading assets the app reads.

recipes.json stays the single source of truth (the "Upload recipes" chat keeps
appending to it exactly as before). This script derives from it:

  index.json      small metadata file + tiny thumbnails  -> loaded on every launch
  pages/<id>-<n>.jpg   one JPEG per recipe page          -> loaded only when a
                                                            recipe is opened

Run this after every change to recipes.json:   python3 build.py
"""
import base64, io, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(ROOT, "pages")
THUMB_W = 180
THUMB_Q = 68

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


def data_uri_to_bytes(uri):
    return base64.b64decode(uri.split(",", 1)[1])


def make_thumb(jpg_bytes):
    """Small inline thumbnail for the recipe list. Falls back to the full page."""
    if not HAVE_PIL:
        return "data:image/jpeg;base64," + base64.b64encode(jpg_bytes).decode()
    im = Image.open(io.BytesIO(jpg_bytes)).convert("RGB")
    w, h = im.size
    im = im.resize((THUMB_W, max(1, round(h * THUMB_W / w))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=THUMB_Q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    with open(os.path.join(ROOT, "recipes.json"), encoding="utf-8") as f:
        recipes = json.load(f)
    if not recipes:
        sys.exit("recipes.json is empty - refusing to build")

    os.makedirs(PAGES, exist_ok=True)
    written, index = set(), []

    for r in recipes:
        rid = r["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", rid):
            sys.exit(f"unsafe recipe id: {rid!r}")
        first = None
        for n, uri in enumerate(r["pages"], 1):
            raw = data_uri_to_bytes(uri)
            if first is None:
                first = raw
            name = f"{rid}-{n}.jpg"
            with open(os.path.join(PAGES, name), "wb") as fh:
                fh.write(raw)
            written.add(name)
        index.append({
            "id": rid,
            "title": r["title"],
            "desc": r.get("desc", ""),
            "category": r["category"],
            "time": r.get("time"),
            "pageCount": len(r["pages"]),
            "thumb": make_thumb(first),
        })

    # drop page files belonging to recipes that no longer exist
    for name in os.listdir(PAGES):
        if name.endswith(".jpg") and name not in written:
            os.remove(os.path.join(PAGES, name))

    with open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

    idx_kb = os.path.getsize(os.path.join(ROOT, "index.json")) / 1024
    src_mb = os.path.getsize(os.path.join(ROOT, "recipes.json")) / 1e6
    print(f"{len(index)} recipes, {len(written)} page images")
    print(f"index.json {idx_kb:.0f} KB  (recipes.json is {src_mb:.1f} MB - no longer "
          f"fetched on launch)")
    if not HAVE_PIL:
        print("NOTE: Pillow not installed - thumbnails are full-size. "
              "Run: pip3 install pillow")


if __name__ == "__main__":
    main()
