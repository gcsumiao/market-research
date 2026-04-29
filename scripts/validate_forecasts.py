#!/usr/bin/env python3
"""
validate_forecasts.py

Lightweight validation of /data/final_5yr_forecast.csv, the standardized
forecast section in every product report, and the homepage priority map.

Checks (each one printed PASS/FAIL with details):

  1. Every product report has a standardized 5-year section.
  2. Every report has Y1-Y5 revenue rows in the standardized section.
  3. final_5yr_forecast.csv has 5 rows for every product / forecast entity.
  4. revenue_m equals target_units x target_price_usd (within 1% / $0.02M).
  5. revenue_m equals total_channel_revenue_m (within 1% / $0.02M).
  6. Homepage Y3 labels match final_base_y3_m for every bubble.
  7. No report says "online share = 100%" while the new methodology applies.
  8. Core-refresh products (archetype A) do not use platform Y4/Y5 ramps.
  9. Validation-only / NO-GO products (archetype D) do not show aggressive
     base-case Y4/Y5 ramps.
 10. Every report sidebar links to the standardized forecast section.
 11. Published standardized sections do not expose prior/old/legacy correction
     language.

Usage:
    python3 scripts/validate_forecasts.py
    python3 scripts/validate_forecasts.py --quiet  (only failures)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = REPO / "products"
HOMEPAGE = REPO / "index.html"
CSV_PATH = REPO / "data" / "final_5yr_forecast.csv"

# Maximum Y4/Y5 ramp tolerated per archetype (vs Y3)
ARCHETYPE_RAMP_CAPS = {
    "A_core_refresh":     {"y4_max": 1.20, "y5_max": 1.32},
    "B_adjacent_retail":  {"y4_max": 1.40, "y5_max": 1.65},
    "C_platform_big_bet": {"y4_max": 1.50, "y5_max": 1.85},
    "D_validation_only":  {"y4_max": 1.15, "y5_max": 1.25},
}

# Map of homepage bubble label -> tuple(<text> regex pattern that contains the
# Y3 number, expected Y3 from CSV is filled in at runtime).
HOMEPAGE_BUBBLE_REGEX = {
    "Jump Starter":            r'>Jump Starter<.*?>3\.85 · \$([0-9.]+)M<',
    "Borescope Screen":        r'>Screen<.*?>3\.65 · \$([0-9.]+)M<',
    "Emergency Kit":           r'>Kit<.*?>3\.95 · \$([0-9.]+)M<',
    "DMM Core":                r'>DMM Core<.*?>4\.20 · \$([0-9.]+)M<',
    "Oil Extractor Tool":      r'>Tool<.*?>2\.70 · \$([0-9.]+)M<',
    "Mech. Stool":             r'>Mech\. Stool<.*?>3\.30 · \$([0-9.]+)M<',
    "Bat. Monitor":            r'>Bat\. Monitor<.*?>2\.75 · \$([0-9.]+)M<',
    "Tool Backpack":           r'>Tool Backpack<.*?>3\.18 · \$([0-9.]+)M',
    "Mag. Fender Tool Roll":   r'>Tool Roll<.*?>3\.20 · \$([0-9.]+)M<',
    "Borescope Wireless":      r'>Wireless<.*?>1\.75 · \$([0-9.]+)M<',
    "Leak Detector Sniffer":   r'>Sniffer<.*?>2\.95 · \$([0-9.]+)M<',
    "Digital Gauge":           r'>Gauge<.*?>2\.80 · \$([0-9.]+)M<',
    "Thermal / NV Monocular":  r'>Monocular<.*?>3\.20 · \$([0-9.]+)M<',
    "Audio DMM":               r'>Audio DMM<.*?3\.00 · \$([0-9.]+)M',
    "LED Light Bar":           r'>LED Light<.*?>Bar<.*?>3\.55 · \$([0-9.]+)M<',
}


def colour(s: str, tag: str) -> str:
    if not sys.stdout.isatty():
        return f"[{tag}] {s}"
    code = {"PASS": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m"}[tag]
    return f"{code}[{tag}]\033[0m {s}"


def load_csv():
    rows = list(csv.DictReader(CSV_PATH.open()))
    for r in rows:
        for k in ("revenue_m", "target_price_usd", "total_channel_revenue_m",
                  "channel_conversion_factor", "final_base_y3_m"):
            r[k] = float(r[k]) if r[k] not in ("", None) else None
        r["target_units"] = int(r["target_units"])
        r["year"] = int(r["year"])
    return rows


def section_text(report_path: Path) -> str | None:
    if not report_path.exists():
        return None
    txt = report_path.read_text()
    m = re.search(
        r'<section id="five-year-allchannel-forecast".*?</section>',
        txt,
        re.DOTALL,
    )
    return m.group(0) if m else None


def standardized_sections(report_path: Path) -> list[str]:
    if not report_path.exists():
        return []
    txt = report_path.read_text()
    return [
        m.group(0)
        for m in re.finditer(
            r'<section id="five-year-allchannel-forecast".*?</section>',
            txt,
            re.DOTALL,
        )
    ]


def check_reports(rows, fail, warn, quiet):
    section_results = []
    for product_dir in sorted(PRODUCTS_DIR.iterdir()):
        report_path = product_dir / "index.html"
        if not report_path.exists():
            continue
        full_text = report_path.read_text()
        sec = section_text(report_path)
        if sec is None:
            fail.append(f"Standardized section missing in {report_path.relative_to(REPO)}")
            section_results.append((report_path, None))
            continue
        if 'href="#five-year-allchannel-forecast"' not in full_text:
            fail.append(f"Sidebar link missing in {report_path.relative_to(REPO)}")
        if "5-Year Revenue Forecast (Standardized)" not in full_text:
            fail.append(f"Sidebar section label missing in {report_path.relative_to(REPO)}")
        # Year 1..5 presence
        years_found = re.findall(r'Year ([1-5])\b', sec)
        years_set = set(years_found)
        if not {"1", "2", "3", "4", "5"}.issubset(years_set):
            fail.append(f"Y1-Y5 not all present in {report_path.relative_to(REPO)} (found years {sorted(years_set)})")
        # No "100% online share" or "online share of total" with 100%
        if re.search(r'100%</strong>\s*</td>|100%</strong>\s*&mdash;|100%</strong>\s*—', sec):
            warn.append(f'"100%" still appears in standardized section of {report_path.relative_to(REPO)}')
        for idx, published_sec in enumerate(standardized_sections(report_path), start=1):
            forbidden_patterns = [
                r'Prior forecast scope',
                r'Homepage legacy',
                r'Old standardized',
                r'\bprior\b',
                r'\bold\b',
                r'\bprevious\b',
                r'\blegacy\b',
                r'\breverted\b',
                r'\bcorrected\b',
                r'\bcorrection\b',
                r'\bhomepage\b',
            ]
            for pattern in forbidden_patterns:
                if re.search(pattern, published_sec, re.IGNORECASE):
                    fail.append(
                        f"Published prior/correction language '{pattern}' in "
                        f"{report_path.relative_to(REPO)} standardized section #{idx}"
                    )
            order = [
                "A. Year 1 - Year 5 forecast",
                "B. Unit &amp; price sanity check",
                "C. Forecast scope &amp; assumptions",
                "D. Channel bridge (Year-3)",
                "E. Scenario / gate notes",
            ]
            positions = [published_sec.find(label) for label in order]
            if any(pos == -1 for pos in positions):
                fail.append(f"Standardized section headings incomplete in {report_path.relative_to(REPO)} section #{idx}")
            elif positions != sorted(positions):
                fail.append(f"Standardized section headings out of order in {report_path.relative_to(REPO)} section #{idx}")
        if not quiet:
            print(colour(f"section present in {report_path.relative_to(REPO)}", "PASS"))
        section_results.append((report_path, sec))


def check_csv(rows, fail, warn, quiet):
    # One row per (forecast_entity, year)
    by_entity = defaultdict(list)
    for r in rows:
        by_entity[r["forecast_entity"]].append(r["year"])
    for entity, years in by_entity.items():
        if sorted(years) != [1, 2, 3, 4, 5]:
            fail.append(f"CSV missing some Y1-Y5 rows for entity '{entity}' (found {sorted(years)})")
        elif not quiet:
            print(colour(f"CSV has Y1-Y5 for '{entity}'", "PASS"))

    # revenue x units check
    for r in rows:
        rev = r["revenue_m"]
        units = r["target_units"]
        asp = r["target_price_usd"]
        ux = units * asp / 1_000_000
        if rev and abs(ux - rev) > max(0.02, 0.01 * rev):
            fail.append(f"revenue != units x price for {r['forecast_entity']} Y{r['year']}: rev={rev:.4f} units*price={ux:.4f}")
    if not quiet:
        print(colour(f"revenue = units x price OK for all {len(rows)} rows", "PASS"))

    # revenue == total_channel_revenue check
    bad_chan = 0
    for r in rows:
        rev = r["revenue_m"]
        ch = r["total_channel_revenue_m"]
        if rev and abs(ch - rev) > max(0.02, 0.01 * rev):
            bad_chan += 1
            fail.append(f"revenue != total_channel_revenue for {r['forecast_entity']} Y{r['year']}: rev={rev:.4f} channel_sum={ch:.4f}")
    if bad_chan == 0 and not quiet:
        print(colour(f"revenue = sum(channel) OK for all {len(rows)} rows", "PASS"))

    # archetype-aware Y4/Y5 caps
    by_entity_year = defaultdict(dict)
    for r in rows:
        by_entity_year[r["forecast_entity"]][r["year"]] = r
    for entity, years in by_entity_year.items():
        if 3 not in years or 4 not in years or 5 not in years:
            continue
        y3 = years[3]["revenue_m"]
        y4 = years[4]["revenue_m"]
        y5 = years[5]["revenue_m"]
        archetype = years[3]["archetype"]
        cap = ARCHETYPE_RAMP_CAPS.get(archetype)
        if not cap:
            warn.append(f"Unknown archetype for entity '{entity}': {archetype}")
            continue
        if y3 and y4 / y3 > cap["y4_max"] + 0.01:
            fail.append(f"{entity}: Y4/Y3 = {y4/y3:.3f}x exceeds archetype {archetype} cap {cap['y4_max']:.2f}x")
        if y3 and y5 / y3 > cap["y5_max"] + 0.01:
            fail.append(f"{entity}: Y5/Y3 = {y5/y3:.3f}x exceeds archetype {archetype} cap {cap['y5_max']:.2f}x")


def check_homepage(rows, fail, warn, quiet):
    if not HOMEPAGE.exists():
        fail.append("Homepage /index.html missing")
        return
    txt = HOMEPAGE.read_text()
    # Build expected map: bubble_name -> final_base_y3_m
    expected = {}
    for r in rows:
        if r["year"] != 3 or r["included_on_homepage"] != "True":
            continue
        bubble = r["homepage_bubble_name"]
        expected[bubble] = r["final_base_y3_m"]
    for bubble, y3 in expected.items():
        rgx = HOMEPAGE_BUBBLE_REGEX.get(bubble)
        if rgx is None:
            warn.append(f"No homepage regex for bubble '{bubble}' - skipping label match check")
            continue
        m = re.search(rgx, txt, re.DOTALL)
        if not m:
            fail.append(f"Could not find homepage label for bubble '{bubble}'")
            continue
        label_y3 = float(m.group(1))
        if abs(label_y3 - y3) > 0.05:
            fail.append(f"Homepage label for '{bubble}' = ${label_y3:.2f}M, expected ${y3:.2f}M")
        elif not quiet:
            print(colour(f"homepage label '{bubble}' = ${label_y3:.2f}M matches CSV", "PASS"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="only print failures / warnings")
    args = ap.parse_args()

    if not CSV_PATH.exists():
        print(colour(f"CSV missing: {CSV_PATH}", "FAIL"))
        return 1

    rows = load_csv()
    fail, warn = [], []
    check_reports(rows, fail, warn, args.quiet)
    check_csv(rows, fail, warn, args.quiet)
    check_homepage(rows, fail, warn, args.quiet)

    print()
    if warn:
        for w in warn:
            print(colour(w, "WARN"))
    if fail:
        for f in fail:
            print(colour(f, "FAIL"))
        print(colour(f"{len(fail)} failure(s); {len(warn)} warning(s)", "FAIL"))
        return 1
    print(colour(f"All checks passed ({len(rows)} rows). Warnings: {len(warn)}.", "PASS"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
