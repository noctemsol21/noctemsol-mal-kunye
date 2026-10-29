#!/usr/bin/env python3
"""Generate Moonlit Elysion More/Details panels from public lunahelios data.

The existing noctemsol generator is imported for its HTTP, parsing, and CSS
escaping helpers. Its default paths, theme, and workflow remain unchanged.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import generate as core

USERNAME = "lunahelios"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / USERNAME
CACHE_FILE = OUTPUT / "cache.json"
CSS_FILE = OUTPUT / "kunye.css"
STALE_DAYS = 35
DETAIL_BUDGET = int(os.environ.get("LUNA_MAX_DETAILS", "350"))


def empty_cache() -> dict:
    return {"username": USERNAME, "anime": {}, "manga": {},
            "favorites": {"anime": [], "manga": []}}


def load_cache() -> dict:
    if not CACHE_FILE.exists():
        return empty_cache()
    try:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if cache.get("username") != USERNAME:
            raise ValueError("Cache belongs to another user")
        for kind in ("anime", "manga"):
            cache.setdefault(kind, {})
        cache.setdefault("favorites", {"anime": [], "manga": []})
        return cache
    except (OSError, ValueError, TypeError):
        return empty_cache()


def parse_id(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdecimal():
        number = int(value)
        return number if number > 0 else None
    return None


def favorites_from_payload(payload: dict) -> dict[str, list[int]]:
    """Accept v1 camelCase or Jikan v4 snake_case public favorite records."""
    data = payload.get("data") or payload
    if isinstance(data, dict) and isinstance(data.get("favorites"), dict):
        data = data["favorites"]
    if not isinstance(data, dict):
        raise ValueError("Unexpected public favorites response")
    result: dict[str, list[int]] = {}
    for kind in ("anime", "manga"):
        items = data.get(kind)
        if not isinstance(items, list):
            raise ValueError(f"Missing {kind} favorites list")
        ids: set[int] = set()
        for entry in items:
            if not isinstance(entry, dict):
                continue
            record = entry.get("entry") or entry.get(kind) or entry
            if not isinstance(record, dict):
                continue
            id_ = parse_id(record.get("malId") or record.get("mal_id"))
            if id_ is not None:
                ids.add(id_)
        result[kind] = sorted(ids)
    return result


def public_favorites() -> dict[str, list[int]]:
    return favorites_from_payload(core.api(f"/users/{USERNAME}/favorites"))


def fresh(record: dict, now: datetime) -> bool:
    try:
        fetched = datetime.fromisoformat(record["fetched"])
        return now - fetched < timedelta(days=STALE_DAYS)
    except (KeyError, ValueError, TypeError):
        return False


def panel_css(kind: str, mal_id: int, record: dict) -> list[str]:
    fields = record.get("fields") or []
    if len(fields) != 9 or any(len(field) != 2 for field in fields):
        return []
    # Different anime and manga can share an ID. Scope BOTH the expanded
    # panel and its More trigger by media type; unlike the original generator,
    # the second genre can never overwrite the first genre's panel.
    kind_page = (
        f'body:has(#list_surround a.animetitle[href*="/{kind}/"]) '
        f'#list_surround'
    )
    more = f"{kind_page} #more{mal_id}"
    poster = core.safe_image_url(record.get("poster") or "")
    labels = [str(field[0]) for field in fields]
    values = [str(field[1]) for field in fields]
    return [
        f"/* {kind}/{mal_id} */",
        f"{more} {{",
        " box-sizing:border-box!important;position:relative!important;",
        " width:100%!important;min-height:272px!important;",
        " margin:5px 0 14px!important;padding:20px!important;",
        " border:1px solid rgba(184,174,220,.49)!important;border-radius:3px!important;",
        " background-color:#162043!important;",
        f" background-image:{poster},linear-gradient(#d8be88,#d8be88)!important;",
        " background-repeat:no-repeat!important;",
        " background-position:19px 21px,18px 20px!important;",
        " background-size:147px 211px,149px 213px!important;",
        " color:#f2edf5!important;font:0/0 Inter,Arial,sans-serif!important;",
        " overflow:hidden!important;text-align:left!important;",
        " box-shadow:0 12px 28px rgba(4,7,24,.29)!important;}",
        f"{more} > * {{display:none!important;}}",
        f"{more}::before {{",
        f" content:{core.css_lines(labels)};",
        " position:absolute;top:19px;left:191px;width:118px;display:block;",
        " color:#d9c28e;font:700 10px/25px Inter,Arial,sans-serif;",
        " letter-spacing:.55px;white-space:pre;overflow:hidden;text-overflow:ellipsis;",
        " pointer-events:none;}",
        f"{more}::after {{",
        f" content:{core.css_lines(values)};",
        " position:absolute;top:19px;left:316px;width:calc(100% - 334px);",
        " display:block;color:#f3edf5;font:400 11px/25px Inter,Arial,sans-serif;",
        " white-space:pre;overflow:hidden;text-overflow:ellipsis;",
        " text-transform:none;pointer-events:none;}",
    ]


def favorite_css(kind: str, mal_id: int) -> str:
    return (
        '#list_surround tr:has(a.animetitle'
        f'[href*="/{kind}/{mal_id}/"]) td:has(a.animetitle)::after '
        '{content:"✦ Favorite";display:block!important;}'
    )


def emit_css(cache: dict) -> str:
    lines = [
        "/* Moonlit Elysion metadata. Auto-generated from public lunahelios data. */",
        "/* Native MAL More/Details JavaScript remains responsible for toggling. */",
        "/* Never copy a generated CSS file to an account with a different username. */",
    ]
    for kind in ("anime", "manga"):
        records = cache.get(kind) or {}
        for key in sorted(records, key=lambda x: int(x) if str(x).isdecimal() else -1):
            if not re.fullmatch(r"[0-9]+", str(key)):
                continue
            lines.extend(panel_css(kind, int(key), records[key]))

    favorites = cache.get("favorites") or {}
    for kind in ("anime", "manga"):
        known = cache.get(kind) or {}
        for id_ in sorted(set(filter(None, (parse_id(x) for x in favorites.get(kind, []))))):
            # Do not render profile-only favorites not present in this list.
            if str(id_) in known:
                lines.append(favorite_css(kind, id_))

    # On small screens, the original MAL More panel is more usable than a
    # nine-column synthetic panel. Preserve the native content as a fallback.
    lines.extend([
        "@media(max-width:680px){",
        ' #list_surround [id^="more"] {min-height:0!important;',
        " background-image:none!important;padding:10px!important;}",
        ' #list_surround [id^="more"] > * {display:revert!important;}',
        ' #list_surround [id^="more"]::before,',
        ' #list_surround [id^="more"]::after {content:none!important;display:none!important;}',
        "}",
    ])
    return "\n".join(lines) + "\n"


def build_cache(cache: dict) -> dict:
    # The old generator's Jikan-compatible source is re-used, but this process
    # sets the account explicitly. The original workflow is unaffected.
    core.USERNAME = USERNAME
    now = datetime.now(timezone.utc)
    seen: dict[str, dict[int, dict]] = {}
    for kind in ("anime", "manga"):
        seen[kind] = core.user_list(kind)
        print(f"{kind}: {len(seen[kind])} public entries", flush=True)
    if not any(seen.values()):
        raise RuntimeError("No public anime or manga entries; refusing to clear the cache")

    budget = DETAIL_BUDGET
    for kind in ("anime", "manga"):
        old_records = cache.get(kind) or {}
        records: dict[str, dict] = {}
        for id_, media in seen[kind].items():
            key = str(id_)
            old = old_records.get(key, {})
            if old and fresh(old, now):
                records[key] = old
                continue
            if budget > 0:
                try:
                    detail = core.api(f"/{kind}/{id_}").get("data") or {}
                    if detail.get("title"):
                        records[key] = core.synopsis_record(kind, detail)
                        budget -= 1
                        continue
                except Exception as exc:
                    print(f"WARN {kind}/{id_}: {exc}", file=sys.stderr)
            if old:
                records[key] = old
            elif media.get("title"):
                records[key] = core.synopsis_record(kind, media)
                # List-level metadata can be sparse; attempt full details later.
                records[key]["fetched"] = "1970-01-01T00:00:00+00:00"
        cache[kind] = records

    try:
        cache["favorites"] = public_favorites()
        print("Public profile favorites updated", flush=True)
    except Exception as exc:
        print(f"WARN favorites: {exc} (keeping prior verified IDs)", file=sys.stderr)
    cache["username"] = USERNAME
    return cache


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cache = build_cache(load_cache())
    css = emit_css(cache)
    # Prepare all bytes before replacing either published output.
    cache_text = json.dumps(cache, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    css_temp = CSS_FILE.with_suffix(".css.tmp")
    cache_temp = CACHE_FILE.with_suffix(".json.tmp")
    css_temp.write_text(css, encoding="utf-8")
    cache_temp.write_text(cache_text, encoding="utf-8")
    css_temp.replace(CSS_FILE)
    cache_temp.replace(CACHE_FILE)
    print(f"Wrote {CSS_FILE} ({len(css)} characters)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
