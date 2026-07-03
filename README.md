# Bazos.cz track-car scanner

Scans auto.bazos.cz daily for cheap (≤30,000 Kč), reasonably powerful
(≥80 kW where detectable) cars — budget track/race candidates — and
publishes the results as a page you can bookmark and open every morning.

## How it works

- A GitHub Actions job runs once a day (06:00 UTC).
- It fetches the newest ~300 listings from auto.bazos.cz.
- It filters by price and detected power (regex on the free-text ad —
  bazos has no structured power field), and flags whether "STK" is
  mentioned.
- It writes `docs/index.html` and commits it back to the repo.
- GitHub Pages serves that file at a stable URL you just open in your
  browser each morning.
- `data/seen.json` tracks which ads you've already seen, so only new
  ones get the 🆕 badge.

## One-time setup (10 minutes)

1. **Create a new GitHub repo** (must be public for free GitHub Pages),
   e.g. `bazos-track-car-scanner`.

2. **Add these files** to the repo (this whole folder — `scraper.py`,
   `.github/workflows/daily-scan.yml`, this README). Commit and push.

3. **Validate the scraper works before relying on it.** Bazos.cz's raw
   HTML structure wasn't directly verifiable while I built this — the
   site blocked one automated fetch attempt, though it's fine with
   normal browser/crawler traffic. Run it locally once:

   ```bash
   pip install requests beautifulsoup4
   python scraper.py
   ```

   Check the printed output:
   - `Fetched N raw listings` — if N > 0, it's working, skip to step 4.
   - If N == 0, the site's HTML class names have likely drifted from
     what's in the script. Open https://auto.bazos.cz/ in a browser,
     right-click an ad card → **Inspect**, and find:
     - the repeating wrapper `<div>` around each ad
     - the title/link element
     Update the three lines marked `# <-- adjust if needed` near the
     top of `parse_listings()` in `scraper.py` to match, then re-run.

4. **Enable GitHub Pages**: repo → Settings → Pages → Source: "Deploy
   from a branch" → Branch: `main`, folder: `/docs` → Save. Your page
   will be live at `https://<your-username>.github.io/<repo-name>/`.

5. **Enable Actions** (usually on by default for a new repo): repo →
   Actions tab → confirm workflows are enabled.

6. **Trigger a first run manually**: Actions tab → "Daily bazos scan" →
   "Run workflow". Check that it commits `docs/index.html` and
   `data/seen.json`, and that the Pages URL shows results.

After that, it runs itself every morning.

## Tuning the filters

Edit the constants near the top of `scraper.py`:

```python
MIN_PRICE_CZK = 15_000   # floor price in Kč (filters out parts-only/junk ads)
MAX_PRICE_CZK = 30_000   # ceiling price in Kč
MIN_KW = 80               # minimum power, only enforced when detectable
TARGET_HITS = 20          # keep scanning deeper pages until this many matches are found
MAX_PAGES = 150           # hard safety cap (150 pages ≈ 3000 ads) in case matches are rare
```

The scan now stops as soon as it finds `TARGET_HITS` matching ads, rather
than scanning a fixed number of pages every time. On a day with lots of
matches near the top it'll be a short, fast run; on a slow day it'll dig
deeper (up to `MAX_PAGES`) to try to reach 20 hits. If it hits the
`MAX_PAGES` cap without reaching the target, the Action log will say so
— that's a signal the filters are tight relative to what's currently
listed, not a bug.

Commit the change — the next scheduled run (or a manual "Run workflow")
picks it up.

## Known limitations

- **Power/STK/mileage/year are free-text guesses.** Bazos doesn't
  expose these as structured search fields, so the script regex-matches
  patterns like "80kW" or "STK" in the ad text. It will miss ads that
  phrase things unusually, and "STK mentioned" just means the word
  appears — it doesn't confirm validity dates. Always click through.
- **Scans until it finds 20 matches, or gives up after ~3000 ads.**
  It no longer scans a fixed number of pages — it keeps going deeper
  into the listings until it hits `TARGET_HITS` matches or the
  `MAX_PAGES` safety cap, whichever comes first. This means run time
  varies day to day: a run with lots of early matches finishes fast, a
  run with few matches takes longer and makes more requests. If it hits
  the safety cap without reaching 20 matches, that's expected on days
  when very little in your price/power range has been posted recently
  — not a sign something's broken.
- **No email delivery yet.** This publishes to a GitHub Pages URL you
  check manually. If you want it emailed instead, say so — it's a
  small addition (GitHub Action step using SMTP + a secret for
  credentials).
