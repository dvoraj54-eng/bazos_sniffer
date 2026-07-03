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
MAX_PRICE_CZK = 30_000   # ceiling price in Kč
MIN_KW = 80               # minimum power, only enforced when detectable
MAX_PAGES = 15            # how many listing pages (20 ads each) to scan per run
```

Commit the change — the next scheduled run (or a manual "Run workflow")
picks it up.

## Known limitations

- **Power/STK/mileage/year are free-text guesses.** Bazos doesn't
  expose these as structured search fields, so the script regex-matches
  patterns like "80kW" or "STK" in the ad text. It will miss ads that
  phrase things unusually, and "STK mentioned" just means the word
  appears — it doesn't confirm validity dates. Always click through.
- **Only scans the newest ~300 ads/day** (`MAX_PAGES × 20`). Bazos has
  no way to filter by price server-side reliably, so very cheap ads
  buried deep in older listings on a single run might be missed if the
  day was unusually busy. Raise `MAX_PAGES` if you want deeper coverage
  (slower runs, more requests).
- **No email delivery yet.** This publishes to a GitHub Pages URL you
  check manually. If you want it emailed instead, say so — it's a
  small addition (GitHub Action step using SMTP + a secret for
  credentials).
