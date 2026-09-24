"""Download one free-licensed photo per car from Wikimedia Commons (run once, needs internet).

For each card in data/cars.json:
  1. If the card has a pinned `foto` (a Commons "File:..." title), use it.
  2. Otherwise search Commons for `foto_soek` and pick the first suitable exterior photo.
  3. Fall back to the lead image of the English Wikipedia article `wiki_title`.
Only public-domain / CC0 / CC BY / CC BY-SA images are accepted. Photos go to
assets/cars/<id>.jpg and attribution to data/credits.json. Existing photos are skipped;
pass --force to re-download, or card ids to only process those cards.
"""

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARS = ROOT / "data" / "cars.json"
CREDITS = ROOT / "data" / "credits.json"
OUT = ROOT / "assets" / "cars"

UA = "VinnigeFluite/1.0 (offline kids card game; one-off photo download) python-urllib"
COMMONS = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA = "https://en.wikipedia.org/w/api.php"
WIDTH = 960  # a standard Wikimedia thumbnail size (non-standard sizes get rate limited)

FREE_LICENCES = re.compile(r"^(public domain|pd|cc0|cc[ -]by(-sa)?( \d\.\d)?)", re.I)
# Titles containing these words are usually not a nice exterior shot of the whole car.
SKIP_WORDS = re.compile(
    r"interior|engine|motor\b|dashboard|cockpit|badge|logo|emblem|wheel|seat|detail|"
    r"steering|trunk|boot|tail ?light|headlight|gauge|interieur|innenraum|heck|rear|"
    r"model|toy|lego|diecast|scale|crash|wreck|drawing|diagram|\.svg|\.png|\.gif|\.tif",
    re.I,
)


def api(url: str, **params) -> dict:
    params |= {"format": "json", "formatversion": "2"}
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 — network hiccups, rate limits
            if attempt == 3:
                raise
            print(f"   ... retry ({e})")
            time.sleep(3 * (attempt + 1))
    return {}


def strip_html(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def info_for(pages: list[dict]) -> list[dict]:
    """Turn API pages (with imageinfo) into candidate dicts, keeping search order."""
    pages = sorted(pages, key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [None])[0]
        if not ii:
            continue
        meta = ii.get("extmetadata", {})
        licence = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
        out.append({
            "title": p["title"],
            "thumb": ii.get("thumburl") or ii.get("url"),
            "width": ii.get("width", 0),
            "height": ii.get("height", 0),
            "mime": ii.get("mime", ""),
            "licence": licence,
            "licence_url": meta.get("LicenseUrl", {}).get("value", ""),
            "artist": strip_html(meta.get("Artist", {}).get("value", "")) or "Onbekend",
            "source": ii.get("descriptionurl", ""),
        })
    return out


II = {"prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": WIDTH}


def suitable(c: dict, strict: bool = True) -> bool:
    if not FREE_LICENCES.match(c["licence"]):
        return False
    if strict:
        if c["mime"] != "image/jpeg" or c["width"] < 1000 or c["width"] < c["height"] * 1.2:
            return False
        if SKIP_WORDS.search(c["title"]):
            return False
    return True


def by_title(title: str) -> list[dict]:
    data = api(COMMONS, action="query", titles=title, **II)
    return info_for(data.get("query", {}).get("pages", []))


def by_search(query: str) -> list[dict]:
    data = api(COMMONS, action="query", generator="search", gsrsearch=f"{query} filetype:bitmap",
               gsrnamespace=6, gsrlimit=20, **II)
    return info_for(data.get("query", {}).get("pages", []))


def by_wikipedia(article: str) -> list[dict]:
    data = api(WIKIPEDIA, action="query", titles=article, prop="pageimages", piprop="name", redirects=1)
    pages = data.get("query", {}).get("pages", [])
    name = pages[0].get("pageimage") if pages else None
    return by_title(f"File:{name}") if name else []


def pick(car: dict) -> dict | None:
    if car.get("foto"):
        found = [c for c in by_title(car["foto"]) if suitable(c, strict=False)]
        if found:
            return found[0]
    found = [c for c in by_search(car["foto_soek"]) if suitable(c)]
    if found:
        return found[0]
    found = [c for c in by_wikipedia(car["wiki_title"]) if suitable(c, strict=False)]
    return found[0] if found else None


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                dest.write_bytes(r.read())
            return
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            wait = int(e.headers.get("Retry-After") or 10 * (attempt + 1))
            print(f"   ... te veel versoeke, wag {wait}s")
            time.sleep(wait)


def main(argv: list[str]) -> int:
    force = "--force" in argv
    only = {a for a in argv if not a.startswith("--")}
    cars = json.loads(CARS.read_text(encoding="utf-8"))
    credits = json.loads(CREDITS.read_text(encoding="utf-8")) if CREDITS.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    missing = []

    for car in cars:
        cid = car["id"]
        if only and cid not in only:
            continue
        dest = OUT / f"{cid}.jpg"
        if dest.exists() and cid in credits and not (force or only):
            continue
        print(f"-> {car['naam']}")
        try:
            choice = pick(car)
            if not choice:
                print("   geen vry foto gevind nie")
                missing.append(cid)
                continue
            download(choice["thumb"], dest)
            credits[cid] = {k: choice[k] for k in ("title", "artist", "licence", "licence_url", "source")}
            print(f"   {choice['title']}  [{choice['licence']}]")
            CREDITS.write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            print(f"   FOUT: {e}")
            missing.append(cid)
        time.sleep(4)

    have = sum((OUT / f"{c['id']}.jpg").exists() for c in cars)
    print(f"\n{have}/{len(cars)} karre het 'n foto.")
    if missing:
        print("Geen foto nie:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
