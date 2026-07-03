#!/usr/bin/env python3
"""
Bazos.cz cheap track-car scanner.

Scans auto.bazos.cz listings and keeps the ones that look like cheap,
light, powerful (or formerly powerful/sporty) budget-racing candidates:

  - price <= MAX_PRICE_CZK
  - power >= MIN_KW, where detectable from the free-text ad (kW or PS)
  - flags whether STK (technical inspection) is mentioned at all

Bazos doesn't expose power/mileage/year as search filters, so this pulls
the raw listing pages and does all filtering itself via regex on the ad
text. Power and STK detection are best-effort text matching, not
guaranteed accurate -- always click through and read the actual ad.

Outputs a static HTML page (docs/index.html, for GitHub Pages) and keeps
a "seen" cache (data/seen.json) so re-runs only flag genuinely new ads
with a 🆕 badge instead of re-surfacing everything every day.

IMPORTANT -- READ BEFORE FIRST RUN:
bazos.cz's exact HTML/CSS structure was not directly verifiable while
building this (the site blocked an automated fetch attempt, though it's
fine with normal browser traffic and search engine crawlers). Run this
once locally first:

    pip install requests beautifulsoup4
    python scraper.py

Then check the printed "Fetched N raw listings" line.
  - If N > 0, you're good, no changes needed.
  - If N == 0, open https://auto.bazos.cz/ in your browser, right-click
    an ad card -> Inspect, and find the repeating wrapper <div> class
    name and the price/title element classes. Update the three CSS
    selectors marked "<-- adjust if needed" in parse_listings() below.
"""

import re
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---- CONFIG -------------------------------------------------------------
MAX_PRICE_CZK = 30_000
MIN_KW = 80
MAX_PAGES = 15  # 20 listings/page -> scans ~300 newest ads per run
BASE_URL = "https://auto.bazos.cz"
SEEN_FILE = Path("data/seen.json")
OUTPUT_HTML = Path("docs/index.html")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
}

KW_RE = re.compile(r"(\d{2,3})\s?kw", re.IGNORECASE)
PS_RE = re.compile(r"(\d{2,3})\s?(?:ps|k[oó]n[ií])", re.IGNORECASE)
STK_RE = re.compile(r"stk", re.IGNORECASE)
PRICE_RE = re.compile(r"(\d[\d\s]{2,8})\s?K[čc]", re.IGNORECASE)


def fetch_page(offset: int) -> str:
    url = f"{BASE_URL}/{offset}/" if offset else f"{BASE_URL}/"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def parse_listings(html: str):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.inzeraty")  # <-- adjust if needed
    listings = []
    for card in cards:
        link_tag = card.select_one("a")
        if not link_tag or not link_tag.get("href"):
            continue
        href = link_tag["href"]
        if not href.startswith("http"):
            href = BASE_URL + href
        title_el = card.select_one(".nadpis, h2, h3")  # <-- adjust if needed
        title_text = (
            title_el.get_text(strip=True) if title_el else link_tag.get_text(strip=True)
        )
        text_blob = card.get_text(" ", strip=True)  # <-- adjust if needed

        listings.append(
            {
                "url": href,
                "title": title_text,
                "raw_text": text_blob,
            }
        )
    return listings


def extract_price(text: str):
    m = PRICE_RE.search(text)
    if not m:
        return None
    digits = re.sub(r"\s", "", m.group(1))
    try:
        return int(digits)
    except ValueError:
        return None


def extract_kw(text: str):
    m = KW_RE.search(text)
    if m:
        return int(m.group(1))
    m = PS_RE.search(text)
    if m:
        ps = int(m.group(1))
        return round(ps * 0.7355)  # PS -> kW
    return None


def has_stk_mention(text: str) -> bool:
    return bool(STK_RE.search(text))


def scrape_all():
    all_listings = []
    for i in range(MAX_PAGES):
        offset = i * 20
        try:
            html = fetch_page(offset)
        except requests.RequestException as e:
            print(f"Failed to fetch offset {offset}: {e}")
            break
        listings = parse_listings(html)
        if not listings:
            break
        all_listings.extend(listings)
        time.sleep(1)  # be polite to their server
    return all_listings


def filter_listings(listings):
    results = []
    for item in listings:
        price = extract_price(item["raw_text"])
        if price is None or price > MAX_PRICE_CZK:
            continue
        kw = extract_kw(item["raw_text"])
        item["price"] = price
        item["kw"] = kw
        item["stk_mentioned"] = has_stk_mention(item["raw_text"])
        # Drop only if power WAS detected and is below threshold.
        # If power is unknown, keep it and flag it -- let Jan judge.
        if kw is not None and kw < MIN_KW:
            continue
        results.append(item)
    return results


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen_urls):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen_urls), ensure_ascii=False, indent=2))


def render_html(results, new_urls):
    results.sort(key=lambda x: (x["kw"] is None, -(x["kw"] or 0)))
    rows = []
    for r in results:
        badge = "🆕 " if r["url"] in new_urls else ""
        kw_text = f"{r['kw']} kW" if r["kw"] else "power unknown — check ad"
        stk_text = "STK mentioned" if r["stk_mentioned"] else "⚠️ no STK mention"
        title_safe = (
            r["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        rows.append(
            f"""
        <div class="card">
          <h3>{badge}<a href="{r['url']}" target="_blank" rel="noopener">{title_safe}</a></h3>
          <p>{r['price']:,} Kč &middot; {kw_text} &middot; {stk_text}</p>
        </div>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bazos track car scan</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; background:#111; color:#eee; }}
  .card {{ border: 1px solid #333; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }}
  .card h3 {{ margin: 0 0 0.4rem 0; }}
  a {{ color: #6db3ff; }}
  .meta {{ color: #999; font-size: 0.9rem; }}
</style>
</head>
<body>
  <h1>🏁 Bazos.cz track-car scan</h1>
  <p class="meta">Last run: {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; {len(results)} matches under {MAX_PRICE_CZK:,} Kč, {MIN_KW}kW+ (where detectable)</p>
  {''.join(rows) if rows else '<p>No matches this run.</p>'}
</body>
</html>"""
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")


def main():
    listings = scrape_all()
    print(f"Fetched {len(listings)} raw listings")
    results = filter_listings(listings)
    print(f"{len(results)} matched filters")

    seen = load_seen()
    current_urls = {r["url"] for r in results}
    new_urls = current_urls - seen

    render_html(results, new_urls)
    save_seen(seen | current_urls)


if __name__ == "__main__":
    main()
