# Moonlit Elysion · lunahelios

An original Sailor Moon-inspired Classic MyAnimeList list stylesheet for both
anime and manga. It uses the lunar crest of Luna and a line-art Pegasus for
Helios, with a navy, lavender and pearl palette.

## Install

Choose the **Classic** design in MyAnimeList List Style Design, then open the
Advanced CSS editor for that design. Paste the following two lines and save:

```css
@\import "https://noctemsol21.github.io/noctemsol-mal-kunye/lunahelios/moonlit-elysion.css";
body {}
```

Apply the Classic design to **both Anime List and Manga List**. The escaped
`@\import` form is needed in MAL's editor; the hosted stylesheet itself uses
valid, ordinary `@import` rules.

## What updates automatically

- `kunye.css` adds a themed Details panel to entries on the publicly available
  anime and manga lists. The panel is opened by MAL's own More control.
- `cache.json` stores the public metadata for **lunahelios** only.
- Favorite indicators are derived from the profile's public anime and manga
  favorites when the endpoint is available. No one else's favorite IDs are
  included or hard-coded.
- Cover previews are requested through separate `lunahelios/anime` and
  `lunahelios/manga` cover imports, preventing ID collisions.

If the third-party metadata service is temporarily unavailable, the last
successfully generated cache remains in the repository. Items lacking metadata
keep MAL's native Details panel.

## Test on MAL

1. Open Anime List in the owner's account. Check row alignment, TV Special,
   a very long title, title-hover cover, Favorite, Edit and Details.
2. Check the same items in a signed-out visitor window (Edit must be absent).
3. Open Manga List. Repeat the checks, including titles with the same numeric
   MAL ID as an anime.
4. Check at 100% browser zoom and at a narrow window. Portrait previews are
   disabled on very narrow viewports.

The files in `docs/` and `scripts/generate.py` for **noctemsol** are separate
and are never written by this generator.
