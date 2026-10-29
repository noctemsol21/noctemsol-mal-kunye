#!/usr/bin/env python3
"""Build a Classic MAL list's per-entry künye CSS from public MAL data.

No credentials are used. The generated CSS contains only public series data.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CACHE_FILE = DOCS / "cache.json"
CSS_FILE = DOCS / "kunye.css"
USERNAME = os.environ.get("MAL_USERNAME", "noctemsol").strip()
BASE = "https://jikan.lucashdo.com/v1"
REQUEST_GAP = 1.1  # Respect Jikan's per-minute rate limit.
STALE_DAYS = 28
MAX_DETAILS = int(os.environ.get("MAX_DETAILS", "1200"))
last_request = 0.0


def api(path: str) -> dict:
    global last_request
    url = BASE + path
    for attempt in range(6):
        wait = REQUEST_GAP - (time.monotonic() - last_request)
        if wait > 0:
            time.sleep(wait)
        last_request = time.monotonic()
        request = urllib.request.Request(url, headers={
            "User-Agent": "NoctemsolMALKunye/1.0 (public metadata; GitHub Actions)",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(min(60, 3 * (2 ** attempt)))
                continue
            raise RuntimeError(f"Metadata API HTTP {error.code}: {url}") from error
        except (TimeoutError, urllib.error.URLError) as error:
            reason = getattr(error, "reason", error)
            if isinstance(reason, OSError) and reason.errno in (101, 113):
                raise RuntimeError(f"Runner has no network route to {url}: {reason}") from error
            if attempt < 5:
                time.sleep(min(60, 3 * (2 ** attempt)))
                continue
            raise RuntimeError(f"Metadata API connection error: {url}") from error
    raise RuntimeError(f"Metadata API failed: {url}")


def user_list(kind: str) -> dict[int, dict]:
    records: dict[int, dict] = {}
    page = 1
    while True:
        path = f"/users/{urllib.parse.quote(USERNAME)}/{kind}list?page={page}&limit=100"
        payload = api(path)
        entries = payload.get("data", [])
        if not isinstance(entries, list):
            raise RuntimeError(f"Unexpected {kind} list format")
        for entry in entries:
            media = entry.get(kind) or entry.get("entry") or entry
            mal_id = media.get("malId") or media.get("mal_id")
            if isinstance(mal_id, int):
                records[mal_id] = media
        pagination = (payload.get("meta") or {}).get("pagination") or payload.get("pagination") or {}
        if not (pagination.get("hasNextPage") or pagination.get("has_next_page")):
            break
        page += 1
        if page > 300:
            raise RuntimeError("Unusually large list; stopping to avoid an infinite loop")
    return records


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if data.get("username") == USERNAME:
                return data
        except (ValueError, OSError):
            pass
    return {"username": USERNAME, "anime": {}, "manga": {}}


def value_text(value, fallback="—") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def name_list(items: list | None, limit=7) -> str:
    names = [str(item.get("name", "")) for item in (items or []) if item.get("name")]
    return ", ".join(names[:limit]) or "—"


def synopsis_record(kind: str, entry: dict) -> dict:
    title = entry.get("title") or "—"
    english = entry.get("titleEnglish") or entry.get("title_english") or entry.get("title") or "—"
    japanese = value_text(entry.get("titleJapanese") or entry.get("title_japanese"))
    synonyms = ", ".join((entry.get("titleSynonyms") or entry.get("title_synonyms") or [])[:4]) or "—"
    genres = name_list(entry.get("genres"), 6)
    themes = name_list((entry.get("themes") or []) + (entry.get("demographics") or []), 4)
    score = entry.get("score")
    score_text = f"{score:.2f} / 10" if isinstance(score, (int, float)) else "Not rated"
    images = entry.get("images") or {}
    poster = (images.get("jpg") or {}).get("large_image_url") or (images.get("jpg") or {}).get("image_url") or images.get("large") or entry.get("imageUrl") or ""
    year = entry.get("year") or (entry.get("published") or {}).get("string") or "—"
    if kind == "anime":
        episodes = entry.get("episodes")
        season = entry.get("season")
        type_year = " · ".join(part for part in (value_text(entry.get("type")), f"{episodes} episodes" if episodes else "Ongoing / unknown episodes", str(year), value_text(season, "")) if part and part != "—")
        fields = [
            ("TITLE", title), ("ALTERNATIVE NAME", english), ("JAPANESE", japanese),
            ("OTHER NAMES", synonyms), ("GENRES", genres), ("THEMES", themes),
            ("STUDIO", name_list(entry.get("studios"), 3)),
            ("FORMAT", type_year), ("MAL SCORE", score_text),
        ]
    else:
        chapters, volumes = entry.get("chapters"), entry.get("volumes")
        author_names = []
        for author in entry.get("authors") or []:
            person = author.get("person") or author
            if person.get("name"):
                author_names.append(person["name"])
        format_bits = [value_text(entry.get("type"))]
        if chapters:
            format_bits.append(f"{chapters} chapters")
        if volumes:
            format_bits.append(f"{volumes} volumes")
        fields = [
            ("TITLE", title), ("ALTERNATIVE NAME", english), ("JAPANESE", japanese),
            ("OTHER NAMES", synonyms), ("GENRES", genres), ("THEMES", themes),
            ("AUTHOR", ", ".join(author_names[:3]) or "—"),
            ("FORMAT", " · ".join(format_bits)), ("MAL SCORE", score_text),
        ]
    return {"fields": fields, "poster": poster, "fetched": datetime.now(timezone.utc).isoformat()}


def css_string(value: str) -> str:
    """Quote CSS-generated text, preventing premature CSS/string termination."""
    value = str(value).replace("\\", "\\\\").replace('"', '\\"')
    value = value.replace("\r", " ").replace("\n", " ").replace("\f", " ")
    return '"' + "".join(f"\\{ord(char):x} " if ord(char) < 32 else char for char in value) + '"'


def css_lines(values: list[str]) -> str:
    return ' "\\A " '.join(css_string(value) for value in values)


def safe_image_url(url: str) -> str:
    parts = urllib.parse.urlparse(url)
    if parts.scheme != "https" or parts.hostname not in {"cdn.myanimelist.net", "myanimelist.net"}:
        return "none"
    return f'url("{url.replace(chr(34), "%22")}")'


def emit_css(cache: dict) -> str:
    lines = [
        "/* Noctemsol MAL Classic künye panels. Generated automatically; do not edit. */",
        "/* This stylesheet depends on MAL's native More button and #more<ID> element. */",
        "/* Base style; type-specific selectors below prevent anime/manga ID collisions. */",
        "#list_surround td:has(a.animetitle) > div[style*=\"float\"] small a[id^=\"xmenu\"] {",
        "  align-items:center;height:18px;margin:0 0 0 11px!important;",
        "  padding:0 0 0 10px!important;border-left:1px solid rgba(226,205,208,.3);",
        "  color:#e3d7d9!important;font:700 11px/18px 'DM Sans',sans-serif!important;vertical-align:baseline;",
        "}",
        "#list_surround td:has(a.animetitle) > div[style*=\"float\"] small {display:inline-flex!important;align-items:center;line-height:18px!important;}",
        "#list_surround td:has(a.animetitle) > div[style*=\"float\"] small a:first-of-type {display:inline-flex!important;align-items:center;height:18px;line-height:18px!important;}",
        "#list_surround td:has(a.animetitle) > div[style*=\"float\"] small a[id^=\"xmenu\"]:hover {color:#ff6775!important;text-shadow:0 0 8px rgba(220,32,51,.6);}",
    ]
    for kind in ("anime", "manga"):
        entries = cache.get(kind) or {}
        for id_text in sorted(entries, key=lambda s: int(s)):
            item = entries[id_text]
            fields = item.get("fields") or []
            if len(fields) != 9 or not re.fullmatch(r"\d+", id_text):
                continue
            mal_id = int(id_text)
            # Match the current row only: a body-wide :has() would be costly
            # when a long list contains hundreds of anime/manga entries.
            row = f'#list_surround td:has(a.animetitle[href*="/{kind}/{mal_id}/"])'
            scope = f'{row} #more{mal_id}'
            button_scope = f'{row} > div[style*="float"] small a#xmenu{mal_id}'
            poster = safe_image_url(item.get("poster") or "")
            labels = [pair[0] for pair in fields]
            values = [pair[1] for pair in fields]
            lines.extend([
                f"/* {kind} {mal_id} */",
                f"{button_scope} {{display:inline-flex!important;align-items:center;height:18px;}}",
                f"{scope} {{box-sizing:border-box!important;position:relative;width:100%!important;min-height:308px;",
                " margin:4px 0 14px!important;padding:20px!important;border:1px solid rgba(205,45,60,.48)!important;",
                " border-radius:4px;background-color:rgba(13,11,15,.97)!important;",
                f" background-image:{poster},linear-gradient(#a92334,#a92334)!important;",
                " background-size:163px 237px,165px 239px!important;background-position:21px 21px,20px 20px!important;",
                " background-repeat:no-repeat!important;color:#e4dddf!important;font:400 0/0 'DM Sans',sans-serif!important;",
                " text-transform:none!important;text-align:left!important;overflow:hidden;box-shadow:0 9px 24px rgba(0,0,0,.3);}",
                f"{scope} > * {{display:none!important;}}",
                f"{scope}::before {{content:{css_lines(labels)};display:block;position:absolute;left:218px;top:17px;",
                " width:140px;color:#ef8190;font:900 10px/25px 'DM Sans',sans-serif;letter-spacing:.8px;",
                " white-space:pre;text-transform:uppercase;pointer-events:none;}",
                f"{scope}::after {{content:{css_lines(values)};display:block;position:absolute;left:372px;top:17px;",
                " width:calc(100% - 396px);color:#e9e2e4;font:400 12px/25px 'DM Sans',sans-serif;letter-spacing:.1px;",
                " white-space:pre;overflow:hidden;text-overflow:ellipsis;text-align:left;text-transform:none;pointer-events:none;}",
            ])
    return "\n".join(lines) + "\n"


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    cached = load_cache()
    now = datetime.now(timezone.utc)
    seen: dict[str, dict[int, dict]] = {}
    for kind in ("anime", "manga"):
        seen[kind] = user_list(kind)
        print(f"{kind}: {len(seen[kind])} list entries",flush=True)
    budget = MAX_DETAILS
    for kind in ("anime", "manga"):
        records = cached.setdefault(kind, {})
        new_records = {}
        for mal_id, media in seen[kind].items():
            key = str(mal_id)
            old = records.get(key, {})
            stale = True
            try:
                stale = now - datetime.fromisoformat(old["fetched"]) > timedelta(days=STALE_DAYS)
            except (KeyError, ValueError, TypeError):
                pass
            if stale and budget > 0:
                try:
                    detail = api(f"/{kind}/{mal_id}").get("data") or {}
                    new_records[key] = synopsis_record(kind, detail)
                    budget -= 1
                except Exception as exc:
                    print(f"WARN {kind}/{mal_id}: {exc}",file=sys.stderr)
                    if old:
                        new_records[key] = old
            elif old:
                new_records[key] = old
            # If the metadata request fails for a new title, we'll retry tomorrow.
        cached[kind] = new_records
        print(f"{kind}: {len(new_records)} künye entries available",flush=True)
    CSS_FILE.write_text(emit_css(cached),encoding="utf-8")
    CACHE_FILE.write_text(json.dumps(cached,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"Wrote {CSS_FILE} ({CSS_FILE.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
