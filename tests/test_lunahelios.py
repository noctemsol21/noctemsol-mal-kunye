"""Offline checks for the independent lunahelios generator."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
CORE = types.ModuleType("generate")
CORE.safe_image_url = lambda value: f'url("{value}")' if value else "none"
CORE.css_lines = lambda values: " ".join(repr(v) for v in values)
CORE.user_list = lambda kind: {}
CORE.api = lambda path: {"data": {}}
CORE.synopsis_record = lambda kind, data: {
    "poster": data.get("poster", ""),
    "fields": [[f"FIELD{i}", data.get("title", "Example")] for i in range(9)],
    "fetched": "2026-01-01T00:00:00+00:00",
}
sys.modules["generate"] = CORE
spec = importlib.util.spec_from_file_location(
    "generate_lunahelios", SCRIPTS / "generate_lunahelios.py"
)
moon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(moon)


class LunaheliosTests(unittest.TestCase):
    def setUp(self):
        self.entry = {
            "poster": "https://cdn.myanimelist.net/images/anime/example.jpg",
            "fields": [[f"FIELD{i}", f"Value{i}"] for i in range(9)],
            "fetched": "2026-10-29T00:00:00+00:00",
        }

    def test_same_id_has_separately_scoped_anime_and_manga_panels(self):
        css = moon.emit_css({
            "anime": {"42": self.entry},
            "manga": {"42": self.entry},
            "favorites": {"anime": [42], "manga": []},
        })
        self.assertIn('body:has(#list_surround a.animetitle[href*="/anime/"]) #list_surround #more42', css)
        self.assertIn('body:has(#list_surround a.animetitle[href*="/manga/"]) #list_surround #more42', css)
        self.assertIn('[href*="/anime/42/"]', css)
        self.assertNotIn('[href*="/manga/42/"]) td:has(a.animetitle)::after', css)
        self.assertNotIn("noctemsol/", css)
        self.assertNotIn("display:block!important;width:100%!important", css)

    def test_only_verified_public_favorites_are_used(self):
        parsed = moon.favorites_from_payload({
            "data": {
                "anime": [{"mal_id": 42}, {"malId": "105"}, {"mal_id": 42}],
                "manga": [{"mal_id": 4}],
            }
        })
        self.assertEqual(parsed, {"anime": [42, 105], "manga": [4]})
        self.assertEqual(moon.parse_id(True), None)
        self.assertEqual(moon.parse_id("-1"), None)
        css = moon.emit_css({
            "anime": {"42": self.entry},
            "manga": {},
            "favorites": parsed,
        })
        self.assertEqual(css.count('content:"✦ Favorite"'), 1)
        self.assertNotIn('href*="/anime/105/"', css)

    def test_public_list_refresh_keeps_account_separate(self):
        with patch.object(CORE, "user_list", side_effect=[
            {7: {"title": "Test Anime"}},
            {8: {"title": "Test Manga"}},
        ]), patch.object(CORE, "api", side_effect=[
            {"data": {"title": "Test Anime"}},
            {"data": {"title": "Test Manga"}},
            {"data": {"anime": [{"mal_id": 7}], "manga": []}},
        ]):
            cache = moon.build_cache(moon.empty_cache())
        self.assertEqual(cache["username"], "lunahelios")
        self.assertEqual(sorted(cache["anime"]), ["7"])
        self.assertEqual(sorted(cache["manga"]), ["8"])
        self.assertEqual(cache["favorites"]["anime"], [7])

    def test_empty_remote_lists_do_not_wipe_existing_cache(self):
        with patch.object(CORE, "user_list", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "refusing to clear"):
                moon.build_cache(moon.empty_cache())


if __name__ == "__main__":
    unittest.main()
