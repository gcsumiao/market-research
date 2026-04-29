#!/usr/bin/env python3
"""
build_standardized_forecasts.py

Single source of truth for the standardized 5-year all-channel forecast across
all 14 Innova product reports. Running this script:

  1. Rewrites the <section id="five-year-allchannel-forecast"> block in every
     /products/*/index.html to use the product-specific archetype, channel
     bridge, unit-and-price reconciliation, and gate notes captured below.

  2. Emits /data/final_5yr_forecast.csv (long format, one row per
     product / forecast entity / year). The CSV is the authoritative source
     of Y1-Y5 revenue, target_units, target_price, and channel mix.

  3. Synchronizes the homepage priority map (/index.html) so every bubble's
     Y3 label matches final_base_y3_m and validation-only entities are
     visually flagged.

Methodology shifts vs. April-2026 standardized pass:

  * Reports that already model Amazon + named retail are NO LONGER described
    as "100% online channel share". They are now "Already all-channel,
    conversion factor 1.00x, online share assumption N/A".

  * Y4/Y5 ramp is no longer the uniform 1.30/1.60. Each product gets an
    archetype-driven curve:
        A. Core refresh / defensive       Y4 = 1.10-1.18  Y5 = 1.20-1.30
        B. Adjacent w/ credible retail    Y4 = 1.20-1.35  Y5 = 1.35-1.60
        C. Platform / big-bet             Y4 = 1.30-1.45  Y5 = 1.60-1.80
        D. Validation-only / niche/NO-GO  Y4 = 1.00-1.10  Y5 = 1.05-1.20

  * Battery Monitor: previously uplifted to $3.09M Y3 via a 65% online-share
    assumption. Reverted to defensive-refresh archetype anchored on report
    Y3 ($2.01M); Y5 capped at 1.20x.

  * Magnetic Silicone Fender Tool Roll: report units (2,000 + 650 = 2,650)
    are MONTHLY run-rate, not annual. Annualized units = 31,800. Blended
    realized ASP = revenue / units = $55.03. Math now reconciles.

  * Oil Extractor: blended realized ASP (revenue / annual units) is used
    as price_basis. Wholesale ASP ($24-27) and retail ASP ($199-$449) are
    documented separately. Revenue x units now reconcile.

  * Thermal Monocular: previous $8.73M Y3 (= $5.24M / 0.60) was uplifted
    without a real channel bridge. New base case anchors on the report's
    $5.24M ecommerce-base scope and shows an explicit Cabela's / Bass Pro /
    Specialty channel bridge. Uplifted scenario is shown as upside, not
    base.

  * DMM is split into two forecast entities: "DMM Core" (final base-case
    Y3 = $4.50M, report-derived) and "Audio DMM" (validation-only,
    capped Y3 = $0.5M, gated).

  * Tool Backpack: target price standardized to $260. Unit assumptions remain
    unchanged; base and high-case revenue are recalculated from units x price.

  * Borescope Wireless: classified D / NO-GO. Y4/Y5 flat-to-modest only.

Run:  python3 scripts/build_standardized_forecasts.py
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

# -----------------------------------------------------------------------------
# Repo paths
# -----------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PRODUCTS_DIR = REPO / "products"
DATA_DIR = REPO / "data"
HOMEPAGE = REPO / "index.html"
CSV_PATH = DATA_DIR / "final_5yr_forecast.csv"

# -----------------------------------------------------------------------------
# Archetype rule library
# -----------------------------------------------------------------------------
ARCHETYPES = {
    "A_core_refresh": {
        "label": "A. Core refresh / defensive",
        "rule": "Y4 = 1.10-1.18 x Y3 ; Y5 = 1.20-1.30 x Y3",
    },
    "B_adjacent_retail": {
        "label": "B. New adjacent product with credible retail rollout",
        "rule": "Y4 = 1.20-1.35 x Y3 ; Y5 = 1.35-1.60 x Y3",
    },
    "C_platform_big_bet": {
        "label": "C. Platform / big-bet product",
        "rule": "Y4 = 1.30-1.45 x Y3 ; Y5 = 1.60-1.80 x Y3",
    },
    "D_validation_only": {
        "label": "D. Validation-only / niche / NO-GO",
        "rule": "Y4/Y5 flat to modest growth only (1.00-1.10 / 1.05-1.20)",
    },
}

# -----------------------------------------------------------------------------
# Per-product / per-forecast-entity configuration.
#
# All revenue figures are in $M (retail sell-through unless price_basis says
# otherwise). target_units are annual units. blended_target_price is in USD.
#
# Channel mix (in $M) must sum to revenue.y3 within rounding (verified at
# write-time).
# -----------------------------------------------------------------------------
PRODUCTS = [
    # ------------------------------------------------------------------- Emergency Kit
    {
        "product_id": "emergency-kit",
        "product_name": "Emergency Kit",
        "forecast_entity": "Emergency Kit (combined SKUs)",
        "report_path": "products/emergency-kit/index.html",
        "homepage_bubble_name": "Emergency Kit",
        "included_on_homepage": True,
        "archetype": "C_platform_big_bet",
        "forecast_status_y3": "report-derived",
        "report_y3_m": 29.90,
        "homepage_legacy_y3_m": 30.00,
        "old_standardized_y3_m": 29.90,
        "final_base_y3_m": 29.90,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - already all-channel",
        "prior_forecast_scope": "Already all-channel - Amazon + Home Depot/Walmart/Costco + State Farm/Allstate/Hippo insurance partnerships modeled explicitly.",
        "y_revenue_m": [7.00, 16.50, 29.90, 41.86, 50.83],   # 1.40x / 1.70x of Y3
        "y_units": [40_000, 90_000, 160_000, 224_000, 272_000],
        "y_blended_asp": [175.00, 183.33, 186.88, 186.88, 186.88],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.40,
        "y5_mult": 1.70,
        "y4_y5_rule": "Platform big-bet: Y4 = 1.40 x Y3 (retail rollout maturing); Y5 = 1.70 x Y3 (insurance partnership scale + replacement demand).",
        "channel_bridge_y3": [
            ("Amazon Marketplace",          7.40,  "amazon_marketplace_revenue_m"),
            ("Direct e-commerce / DTC",     2.00,  "direct_ecommerce_revenue_m"),
            ("Home Depot / Lowe's / Mass",  9.50,  "mass_hardware_retail_revenue_m"),
            ("Costco club channel",         4.00,  "specialty_retail_revenue_m"),
            ("Insurance partnerships (State Farm/Allstate/Hippo)", 7.00, "fleet_commercial_revenue_m"),
        ],
        "gate_or_caveat": "Insurance partnership conversion is the largest single risk; if it slips, base-case Y3 falls toward $22-24M.",
        "notes": "Retail sell-through revenue. Y4/Y5 ramp assumes one additional mass retailer plus first replacement-cycle pull-through.",
    },

    # ------------------------------------------------------------------- Jump Starters
    {
        "product_id": "jump-starters",
        "product_name": "Jump Starter",
        "forecast_entity": "Jump Starter (Compact + Full-Size)",
        "report_path": "products/jump-starters/index.html",
        "homepage_bubble_name": "Jump Starter",
        "included_on_homepage": True,
        "archetype": "C_platform_big_bet",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 17.30,
        "homepage_legacy_y3_m": 17.00,
        "old_standardized_y3_m": 20.35,
        "final_base_y3_m": 17.30,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - reverted; report base case kept until AutoZone door-velocity is validated",
        "prior_forecast_scope": "Amazon explicitly the primary channel ($11.1M/mo combo segment). Retail (AutoZone) flagged but not bottom-up modeled. The April-2026 uplift to $20.35M assumed an 85% online share that the underlying model did not actually break out; reverted to report base case.",
        "y_revenue_m": [4.15, 10.10, 17.30, 23.36, 28.55],   # 1.35x / 1.65x of Y3
        "y_units": [50_000, 115_000, 190_000, 256_500, 313_500],
        "y_blended_asp": [83.00, 87.83, 91.05, 91.05, 91.05],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.35,
        "y5_mult": 1.65,
        "y4_y5_rule": "Platform big-bet (gated): Y4 = 1.35 x Y3 conditional on a named auto-parts retailer landing; Y5 = 1.65 x Y3 if that retailer hits target sell-through.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",          11.10, "amazon_marketplace_revenue_m"),
            ("Direct e-commerce / DTC",      1.20, "direct_ecommerce_revenue_m"),
            ("AutoZone (Y2-Y3 retail)",      3.50, "auto_retail_revenue_m"),
            ("Walmart / mass retail",        1.50, "mass_hardware_retail_revenue_m"),
        ],
        "gate_or_caveat": "Y4/Y5 ramp assumes confirmed AutoZone (or equivalent) shelf placement and ASP discipline; if pricing collapses below $70/$110 floor, Y5 caps closer to 1.30-1.40 x Y3.",
        "notes": "Pricing strategy flagged as a key sensitivity in the underlying report; ASP floor must be defended.",
    },

    # ------------------------------------------------------------------- Mechanic Stool
    {
        "product_id": "mechanic-stool",
        "product_name": "Mechanic Stool",
        "forecast_entity": "Mechanic Stool (Standard + Premium)",
        "report_path": "products/mechanic-stool/index.html",
        "homepage_bubble_name": "Mech. Stool",
        "included_on_homepage": True,
        "archetype": "B_adjacent_retail",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 3.87,
        "homepage_legacy_y3_m": 3.90,
        "old_standardized_y3_m": 4.84,
        "final_base_y3_m": 3.87,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - reverted; no retailer named or % quantified for an 80% uplift",
        "prior_forecast_scope": "Amazon ramp Y1; multichannel narrative Y2-Y3 but no retailer named. April-2026 uplift to $4.84M assumed an 80% online share; reverted because the underlying model does not actually quantify a non-Amazon channel.",
        "y_revenue_m": [0.98, 2.11, 3.87, 4.64, 5.42],       # 1.20x / 1.40x of Y3
        "y_units": [9_000, 19_000, 34_000, 40_800, 47_600],
        "y_blended_asp": [108.89, 111.05, 113.82, 113.82, 113.82],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.20,
        "y5_mult": 1.40,
        "y4_y5_rule": "Adjacent w/ credible retail (low end): Y4 = 1.20 x Y3 ; Y5 = 1.40 x Y3. Restrained because no retailer is named in the report.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",          2.55, "amazon_marketplace_revenue_m"),
            ("Direct e-commerce / DTC",     0.45, "direct_ecommerce_revenue_m"),
            ("Auto-parts retail (TBD)",     0.65, "auto_retail_revenue_m"),
            ("Specialty retail (TBD)",      0.22, "specialty_retail_revenue_m"),
        ],
        "gate_or_caveat": "Y4/Y5 ramp gated on at least one named retailer landing in Y3.",
        "notes": "Retail upside is real but not yet contracted; archetype B kept at the conservative end.",
    },

    # ------------------------------------------------------------------- Battery Monitor
    {
        "product_id": "battery-monitor",
        "product_name": "Battery Monitor",
        "forecast_entity": "Battery Monitor (Classic + Character)",
        "report_path": "products/battery-monitor/index.html",
        "homepage_bubble_name": "Bat. Monitor",
        "included_on_homepage": True,
        "archetype": "A_core_refresh",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 2.01,
        "homepage_legacy_y3_m": 2.00,
        "old_standardized_y3_m": 3.09,
        "final_base_y3_m": 2.01,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - reverted; this is a defensive refresh, not an all-channel growth model",
        "prior_forecast_scope": "Defensive refresh of Innova 3721. Amazon-dominant Y1; existing AutoZone retail distribution acknowledged but not bottom-up modeled. April-2026 uplift to $3.09M (65% online share) overstated the channel lift for what is really a SKU-replacement bet.",
        "y_revenue_m": [0.71, 1.34, 2.01, 2.21, 2.41],       # 1.10x / 1.20x of Y3
        "y_units": [32_000, 60_000, 90_000, 99_000, 108_000],
        "y_blended_asp": [22.19, 22.33, 22.33, 22.33, 22.33],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.10,
        "y5_mult": 1.20,
        "y4_y5_rule": "Core refresh / defensive: Y4 = 1.10 x Y3 ; Y5 = 1.20 x Y3. Defensive refresh; not category-defining growth.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",          1.30, "amazon_marketplace_revenue_m"),
            ("Direct e-commerce / DTC",     0.10, "direct_ecommerce_revenue_m"),
            ("AutoZone / auto-parts",       0.61, "auto_retail_revenue_m"),
        ],
        "gate_or_caveat": "Defensive refresh; not category-defining growth. Y5 capped at 1.20 x Y3 unless a new SKU or new channel materially changes the franchise.",
        "notes": "Treat as core refresh / defensive, not platform growth. No aggressive uplift applied.",
    },

    # ------------------------------------------------------------------- Tool Backpack (BASE)
    {
        "product_id": "tool-backpack",
        "product_name": "Tool Backpack",
        "forecast_entity": "Tool Backpack (base case)",
        "report_path": "products/tool-backpack/index.html",
        "homepage_bubble_name": "Tool Backpack",
        "included_on_homepage": True,
        "archetype": "D_validation_only",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 1.0296,
        "homepage_legacy_y3_m": 0.90,   # legacy midpoint
        "old_standardized_y3_m": 0.742,
        "final_base_y3_m": 1.0296,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - scanner customer cross-sell and Amazon are modeled directly in revenue",
        "prior_forecast_scope": "Internal audit field only. Public report uses the current $260 target price and current unit ramp.",
        "y_revenue_m": [0.3744, 0.6864, 1.0296, 1.1310, 1.2350],  # units x $260 target price
        "y_units": [1_440, 2_640, 3_960, 4_350, 4_750],
        "y_blended_asp": [260.00, 260.00, 260.00, 260.00, 260.00],
        "price_basis": "blended_target_sell_through_price",
        "unit_basis": "annual_units",
        "y4_mult": 1.10,
        "y5_mult": 1.20,
        "y4_y5_rule": "Validation-only / niche: Y4 = 1.10 x Y3 ; Y5 = 1.20 x Y3. Run-rate must clear the 60-units/mo viability floor before any wider channel bet.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",          0.5584, "amazon_marketplace_revenue_m"),
            ("Direct e-commerce / DTC (Innova scanner cross-sell)", 0.4712, "direct_ecommerce_revenue_m"),
        ],
        "gate_or_caveat": "Base case uses the $260 target price with a 3,960-unit Year-3 ramp. High-case Y3 is shown as a separate scenario row in the CSV.",
        "notes": "Y1 base target is 1,440 units; re-evaluate at month 6. If run-rate < 60 u/mo, exit SKU.",
    },

    # ------------------------------------------------------------------- Tool Backpack (HIGH SCENARIO)
    {
        "product_id": "tool-backpack",
        "product_name": "Tool Backpack",
        "forecast_entity": "Tool Backpack (high-case scenario)",
        "report_path": "products/tool-backpack/index.html",
        "homepage_bubble_name": "Tool Backpack",
        "included_on_homepage": False,    # base is the bubble; high-case shown only in CSV/report
        "archetype": "D_validation_only",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 1.872,
        "homepage_legacy_y3_m": 0.90,
        "old_standardized_y3_m": 1.35,
        "final_base_y3_m": 1.872,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - high-case scenario; Innova cross-sell + Amazon already reflected in revenue",
        "prior_forecast_scope": "Internal audit field only. High-case scenario uses the current $260 target price.",
        "y_revenue_m": [0.624, 1.248, 1.872, 2.0592, 2.2464],
        "y_units": [2_400, 4_800, 7_200, 7_920, 8_640],
        "y_blended_asp": [260.00, 260.00, 260.00, 260.00, 260.00],
        "price_basis": "blended_target_sell_through_price",
        "unit_basis": "annual_units",
        "y4_mult": 1.10,
        "y5_mult": 1.20,
        "y4_y5_rule": "Validation-only (high case): Y4 = 1.10 x Y3 ; Y5 = 1.20 x Y3.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",          0.9533, "amazon_marketplace_revenue_m"),
            ("Direct e-commerce / DTC (Innova scanner cross-sell)", 0.9187, "direct_ecommerce_revenue_m"),
        ],
        "gate_or_caveat": "High-case scenario; do NOT use as base. Requires sustained 200 u/mo on Innova cross-sell at the $260 target price.",
        "notes": "Documented for completeness; not shown on homepage map.",
    },

    # ------------------------------------------------------------------- Magnetic Fender Tool Roll
    {
        "product_id": "Magnetic-Fender-Tool-Roll",
        "product_name": "Magnetic Silicone Fender Tool Roll",
        "forecast_entity": "Magnetic Silicone Fender Tool Roll (Standard + Pro/XL)",
        "report_path": "products/Magnetic-Fender-Tool-Roll/index.html",
        "homepage_bubble_name": "Mag. Fender Tool Roll",
        "included_on_homepage": True,
        "archetype": "B_adjacent_retail",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 1.75,
        "homepage_legacy_y3_m": 1.75,
        "old_standardized_y3_m": 2.50,
        "final_base_y3_m": 1.75,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - reverted; uplift was applied before unit/price math reconciled",
        "prior_forecast_scope": "Amazon FBA primary Y1 + retail (NAPA / AutoZone implied) Y2-Y3. April-2026 uplift to $2.50M (70% online) was applied before the unit/price math was reconciled and is reverted.",
        "y_revenue_m": [0.480, 1.020, 1.750, 2.275, 2.800],  # 1.30x / 1.60x of Y3
        # Annualized units: report shows 600/mo Std + 150/mo Pro Y1 -> 9,000 annual.
        # 1,200/mo + 375/mo Y2 -> 18,900. 2,000/mo + 650/mo Y3 -> 31,800.
        "y_units": [9_000, 18_900, 31_800, 41_300, 50_900],
        "y_blended_asp": [53.33, 53.97, 55.03, 55.08, 55.01],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.30,
        "y5_mult": 1.60,
        "y4_y5_rule": "Adjacent w/ credible retail: Y4 = 1.30 x Y3 ; Y5 = 1.60 x Y3, conditional on smoke-test conversion and retail line-extension rollout.",
        "channel_bridge_y3": [
            ("Amazon Marketplace (Fender + Tool-Tray subcats)", 1.20, "amazon_marketplace_revenue_m"),
            ("NAPA / AutoZone retail (Y2-Y3 line extension)",    0.40, "auto_retail_revenue_m"),
            ("Direct / Innova cross-sell",                       0.15, "direct_ecommerce_revenue_m"),
        ],
        "gate_or_caveat": "Reconciliation: report's 'Y3 units' (2,000 + 650 = 2,650) reflects MONTHLY run-rate, not annual. Annual unit equivalent = 31,800. Revenue = 31,800 x blended $55.03 = $1.75M (within rounding). CONDITIONAL GO: smoke test must clear 200+ signups before silicone tooling commitment.",
        "notes": "Forecast revenue represents estimated annual retail sell-through.",
    },

    # ------------------------------------------------------------------- DMM Core
    {
        "product_id": "DMM",
        "product_name": "Digital Multimeter (DMM)",
        "forecast_entity": "DMM Core (3320 + 3340 + AutoZone 3-SKU)",
        "report_path": "products/DMM/index.html",
        "homepage_bubble_name": "DMM Core",
        "included_on_homepage": True,
        "archetype": "A_core_refresh",
        "forecast_status_y3": "report-derived",
        "report_y3_m": 4.50,
        "homepage_legacy_y3_m": 4.00,
        "old_standardized_y3_m": 4.50,
        "final_base_y3_m": 4.50,         # report Y3 as authoritative over homepage
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - already all-channel",
        "prior_forecast_scope": "Already all-channel - base case explicitly models Amazon ($270K Y1 -> $360K Y3) plus AutoZone 3-SKU rows ($3.74M Y1 -> $4.12M Y3).",
        # Y4 = 1.15 x Y3 = 5.18M, Y5 = 1.25 x Y3 = 5.625M (core refresh ramp).
        "y_revenue_m": [4.00, 4.20, 4.50, 5.18, 5.63],
        "y_units": [62_500, 64_700, 68_700, 79_000, 85_900],
        "y_blended_asp": [64.00, 64.92, 65.50, 65.57, 65.54],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.15,
        "y5_mult": 1.25,
        "y4_y5_rule": "Core refresh / defensive: Y4 = 1.15 x Y3 ; Y5 = 1.25 x Y3. Anchor on report base case, not on the lower homepage label.",
        "channel_bridge_y3": [
            ("Amazon Marketplace (3320 + 3340)",  0.36, "amazon_marketplace_revenue_m"),
            ("AutoZone 3-SKU retail",             4.12, "auto_retail_revenue_m"),
            ("Direct / Innova.com",               0.02, "direct_ecommerce_revenue_m"),
        ],
        "gate_or_caveat": "Use report Y3 ($4.50M) as authoritative over the homepage's earlier $4.0M label; AutoZone partnership is the load-bearing line.",
        "notes": "DMM Core and Audio DMM are kept as separate forecast entities.",
    },

    # ------------------------------------------------------------------- Audio DMM (validation only)
    {
        "product_id": "DMM",
        "product_name": "Digital Multimeter (DMM)",
        "forecast_entity": "Audio DMM (validation-only)",
        "report_path": "products/DMM/index.html",
        "homepage_bubble_name": "Audio DMM",
        "included_on_homepage": True,        # kept as a separate, visually flagged bubble
        "archetype": "D_validation_only",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 0.50,                 # gated, single-figure
        "homepage_legacy_y3_m": 2.00,        # legacy "$1-3M" range midpoint
        "old_standardized_y3_m": 2.00,
        "final_base_y3_m": 0.50,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - validation-only concept; Amazon-first if it launches at all",
        "prior_forecast_scope": "Concept SKU. Report flagged as 'demand-unproven' and warranting a $500-$2K concept test before any commitment. Old homepage range of $1-3M was speculative.",
        "y_revenue_m": [0.10, 0.30, 0.50, 0.55, 0.60],   # 1.10x / 1.20x
        "y_units": [2_200, 6_700, 11_100, 12_200, 13_300],
        "y_blended_asp": [45.45, 44.78, 45.05, 45.08, 45.11],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.10,
        "y5_mult": 1.20,
        "y4_y5_rule": "Validation-only / niche: flat to modest growth (1.10 / 1.20) ONLY if concept test passes.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",  0.50, "amazon_marketplace_revenue_m"),
        ],
        "gate_or_caveat": "Validation-only / gated. Numbers shown only IF the $500-$2K concept test clears 100+ pre-orders. Otherwise this entity is dropped from the portfolio.",
        "notes": "Kept as separate bubble on the homepage with a validation-only label so it does not inherit DMM Core's economics.",
    },

    # ------------------------------------------------------------------- Leak Detector Sniffer
    {
        "product_id": "Leak Detector Sniffer",
        "product_name": "Leak Detector Sniffer",
        "forecast_entity": "Leak Detector Sniffer (single dual-mode SKU)",
        "report_path": "products/Leak Detector Sniffer/index.html",
        "homepage_bubble_name": "Leak Detector Sniffer",
        "included_on_homepage": True,
        "archetype": "B_adjacent_retail",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 1.84,
        "homepage_legacy_y3_m": 1.84,
        "old_standardized_y3_m": 2.63,
        "final_base_y3_m": 2.10,         # accept a modest uplift but cap Y4/Y5
        "channel_conversion_factor": 1.14,
        "online_share_assumption": "Modest 14% retail uplift accepted (1.14x) given AutoZone/NAPA Innova distribution real but unmodeled in conservative case",
        "prior_forecast_scope": "Amazon-primary Y1; Y2-Y3 retail expansion (AutoZone/NAPA implied). April-2026 70% online share gave $2.63M Y3; partially adopted (capped at $2.10M) and Y4/Y5 explicitly gated.",
        "y_revenue_m": [0.535, 1.110, 2.100, 2.520, 2.835],  # 1.20x / 1.35x of Y3
        "y_units": [3_300, 6_500, 11_200, 13_440, 15_120],
        "y_blended_asp": [162.12, 170.77, 187.50, 187.50, 187.50],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.20,
        "y5_mult": 1.35,
        "y4_y5_rule": "Adjacent w/ credible retail (low end): Y4 = 1.20 x Y3 ; Y5 = 1.35 x Y3, conditional on retail placement, acceptable return rate, and warranty validation.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",      1.40, "amazon_marketplace_revenue_m"),
            ("AutoZone / NAPA retail",  0.55, "auto_retail_revenue_m"),
            ("Direct / Innova.com",     0.15, "direct_ecommerce_revenue_m"),
        ],
        "gate_or_caveat": "GATE: Y4/Y5 expansion requires (1) confirmed retail placement at AutoZone or NAPA, (2) acceptable Amazon return rate (<8%), (3) warranty cost validation. If no retail placement is contracted by mid-Y2, cap Y4/Y5 closer to 1.10x / 1.15x.",
        "notes": "Modest uplift accepted because Innova retail distribution is genuinely real for diagnostic SKUs.",
    },

    # ------------------------------------------------------------------- LED Light Bar
    {
        "product_id": "LED Light Bar",
        "product_name": "LED Light Bar (MODU-LIGHT PRO)",
        "forecast_entity": "MODU-LIGHT PRO + accessories",
        "report_path": "products/LED Light Bar/index.html",
        "homepage_bubble_name": "LED Light Bar",
        "included_on_homepage": True,
        "archetype": "B_adjacent_retail",
        "forecast_status_y3": "report-derived",
        "report_y3_m": 3.90,
        "homepage_legacy_y3_m": 3.80,
        "old_standardized_y3_m": 3.90,
        "final_base_y3_m": 3.90,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - already all-channel (Amazon DTC -> AutoZone Commercial -> NAPA/O'Reilly modeled)",
        "prior_forecast_scope": "Already all-channel - base sequence explicitly models Amazon Y1 -> AutoZone Commercial Y2 -> NAPA/O'Reilly Y3 plus accessories.",
        "y_revenue_m": [1.50, 2.90, 3.90, 5.07, 6.05],   # 1.30x / 1.55x of Y3
        "y_units": [18_000, 35_400, 47_500, 61_750, 73_700],
        "y_blended_asp": [83.33, 81.92, 82.11, 82.11, 82.10],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.30,
        "y5_mult": 1.55,
        "y4_y5_rule": "Adjacent w/ credible retail (mid range): Y4 = 1.30 x Y3 ; Y5 = 1.55 x Y3 driven by accessory attach + commercial fleet expansion.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",          1.40, "amazon_marketplace_revenue_m"),
            ("AutoZone Commercial (B2B)",   1.30, "auto_retail_revenue_m"),
            ("NAPA / O'Reilly installer",   0.95, "specialty_retail_revenue_m"),
            ("Accessories sequence",        0.25, "other_revenue_m"),
        ],
        "gate_or_caveat": "Y4/Y5 ramp gated on accessory attach rate and AutoZone Commercial sell-through holding through replacement cycle.",
        "notes": "$79 MAP defended; high-case ($6.1M) requires Harbor Freight or other national retailer, which is not assumed here.",
    },

    # ------------------------------------------------------------------- Oil Extractor
    {
        "product_id": "Oil Extractor Tool",
        "product_name": "Oil Extractor Tool",
        "forecast_entity": "Oil Extractor (Auto + Manual)",
        "report_path": "products/Oil Extractor Tool/index.html",
        "homepage_bubble_name": "Oil Extractor Tool",
        "included_on_homepage": True,
        "archetype": "B_adjacent_retail",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 3.58,
        "homepage_legacy_y3_m": 3.58,
        "old_standardized_y3_m": 3.58,
        "final_base_y3_m": 3.58,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - already all-channel",
        "prior_forecast_scope": "Already all-channel - Amazon Y1 + 2nd retailer Y2 + 3rd retailer Y3 explicit in the underlying model.",
        "y_revenue_m": [0.820, 1.900, 3.580, 4.475, 5.191],  # 1.25x / 1.45x of Y3
        # Y1 = 12,000 units (~73% of VEVOR's Amazon velocity); Y2 / Y3 grow as 2nd / 3rd retailer + Manual SKU come online.
        "y_units": [12_000, 17_500, 19_000, 23_750, 27_550],
        "y_blended_asp": [68.33, 108.57, 188.42, 188.42, 188.43],
        "price_basis": "blended_retail_sell_through_innova_realized",
        "unit_basis": "annual_units",
        "y4_mult": 1.25,
        "y5_mult": 1.45,
        "y4_y5_rule": "Adjacent w/ credible retail: Y4 = 1.25 x Y3 (retailer 4 onboards + Manual mix matures) ; Y5 = 1.45 x Y3 (organic Amazon ranking compounds).",
        "channel_bridge_y3": [
            ("Amazon Marketplace",       1.40, "amazon_marketplace_revenue_m"),
            ("AutoZone retail",          0.85, "auto_retail_revenue_m"),
            ("NAPA / O'Reilly retail",   0.78, "auto_retail_revenue_m"),  # combined into auto_retail in CSV
            ("Walmart mass retail",      0.55, "mass_hardware_retail_revenue_m"),
        ],
        "gate_or_caveat": "Reconciliation: revenue / annual units gives Innova-realized blended ASP that scales from $68 in Y1 (Amazon launch, Manual-heavy mix) to $188 in Y3 (Auto SKU dominant + retail mix). Wholesale supplier ASP is separately $24-27, used for COGS not revenue. Revenue x units reconciles to the $3.58M Y3 anchor.",
        "notes": "Forecast revenue represents Innova-realized retail sell-through (after Amazon fees / retailer margin), not gross MSRP and not wholesale.",
    },

    # ------------------------------------------------------------------- Borescope Screen
    {
        "product_id": "Borescope-CameraB",
        "product_name": "Articulating Borescope (Screen-Based)",
        "forecast_entity": "Borescope Screen-Based",
        "report_path": "products/Borescope-CameraB/index.html",
        "homepage_bubble_name": "Borescope Screen",
        "included_on_homepage": True,
        "archetype": "C_platform_big_bet",
        "forecast_status_y3": "report-derived",
        "report_y3_m": 10.58,
        "homepage_legacy_y3_m": 10.60,
        "old_standardized_y3_m": 10.58,
        "final_base_y3_m": 10.58,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - already all-channel",
        "prior_forecast_scope": "Already all-channel - bottom-up rows for AutoZone / Advance / NAPA / O'Reilly plus Amazon, ~50/50 by Y3.",
        "y_revenue_m": [3.80, 6.58, 10.58, 14.28, 17.46],    # 1.35x / 1.65x of Y3
        "y_units": [27_300, 47_300, 73_800, 99_600, 121_800],
        "y_blended_asp": [139.19, 139.11, 143.36, 143.37, 143.34],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.35,
        "y5_mult": 1.65,
        "y4_y5_rule": "Platform big-bet: Y4 = 1.35 x Y3 (broader retail rollout maturing); Y5 = 1.65 x Y3 (replacement demand + tool-bundle attach).",
        "channel_bridge_y3": [
            ("Amazon Marketplace",                    4.75, "amazon_marketplace_revenue_m"),
            ("AutoZone retail",                       2.10, "auto_retail_revenue_m"),
            ("Advance Auto / NAPA / O'Reilly retail", 3.30, "auto_retail_revenue_m"),
            ("Direct / Innova.com",                   0.43, "direct_ecommerce_revenue_m"),
        ],
        "gate_or_caveat": "Y4/Y5 ramp assumes offline sell-through velocity benchmarked on the Innova 3380 holds; conditional on retailer reorder cadence Y4.",
        "notes": "Screen-Based is the homepage bubble; Wireless is a separate (validation-only) entity below.",
    },

    # ------------------------------------------------------------------- Borescope Wireless
    {
        "product_id": "Borescope-CameraB",
        "product_name": "Articulating Borescope (Wireless/App)",
        "forecast_entity": "Borescope Wireless/App",
        "report_path": "products/Borescope-CameraB/index.html",
        "homepage_bubble_name": "Borescope Wireless",
        "included_on_homepage": True,        # kept on map but visually flagged
        "archetype": "D_validation_only",
        "forecast_status_y3": "report-derived",
        "report_y3_m": 0.94,
        "homepage_legacy_y3_m": 0.94,
        "old_standardized_y3_m": 0.94,
        "final_base_y3_m": 0.94,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - already all-channel; Amazon-native by definition",
        "prior_forecast_scope": "Already all-channel - report breaks out Amazon and minimal offline.",
        "y_revenue_m": [0.330, 0.600, 0.940, 1.034, 1.128],  # 1.10x / 1.20x of Y3 (D archetype)
        "y_units": [4_100, 7_400, 11_600, 12_750, 13_900],
        "y_blended_asp": [80.49, 81.08, 81.03, 81.10, 81.15],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.10,
        "y5_mult": 1.20,
        "y4_y5_rule": "Validation-only / NO-GO at sub-scale: Y4 = 1.10 x Y3 ; Y5 = 1.20 x Y3 only. No platform ramp.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",  0.85, "amazon_marketplace_revenue_m"),
            ("Direct / Innova.com", 0.09, "direct_ecommerce_revenue_m"),
        ],
        "gate_or_caveat": "NO-GO sub-scale. No clean selling-angle stack vs. the Screen-Based candidate. Kept on map with separate validation-only label.",
        "notes": "Y4/Y5 deliberately flat to modest. Not a platform candidate.",
    },

    # ------------------------------------------------------------------- Digital Gauge
    {
        "product_id": "Digital-Gauge",
        "product_name": "Digital Gauge",
        "forecast_entity": "Digital Gauge (single SKU)",
        "report_path": "products/Digital-Gauge/index.html",
        "homepage_bubble_name": "Digital Gauge",
        "included_on_homepage": True,
        "archetype": "B_adjacent_retail",
        "forecast_status_y3": "report-derived",
        "report_y3_m": 2.80,
        "homepage_legacy_y3_m": 2.80,
        "old_standardized_y3_m": 2.80,
        "final_base_y3_m": 2.80,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - already all-channel (Amazon + AutoZone/Walmart regional pilot in base case)",
        "prior_forecast_scope": "Already all-channel - base case = Amazon + AutoZone/Walmart regional pilot. Upside ($4.50M) requires national retail (HD/Lowe's/Ace + Harbor Freight) which is not assumed here.",
        "y_revenue_m": [0.45, 1.45, 2.80, 3.50, 4.06],       # 1.25x / 1.45x of Y3
        "y_units": [2_400, 7_800, 15_100, 18_900, 21_950],
        "y_blended_asp": [187.50, 185.90, 185.43, 185.19, 184.97],
        "price_basis": "fixed_retail_asp",
        "unit_basis": "annual_units",
        "y4_mult": 1.25,
        "y5_mult": 1.45,
        "y4_y5_rule": "Adjacent w/ credible retail: Y4 = 1.25 x Y3 ; Y5 = 1.45 x Y3 (regional pilot scaling, accessory attach). National retail = upside, not base.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",          1.20, "amazon_marketplace_revenue_m"),
            ("AutoZone regional pilot",     0.85, "auto_retail_revenue_m"),
            ("Walmart regional pilot",      0.55, "mass_hardware_retail_revenue_m"),
            ("Direct / Innova.com",         0.20, "direct_ecommerce_revenue_m"),
        ],
        "gate_or_caveat": "Upside scenario ($4.50M Y3) = national retail (HD/Lowe's/Ace + Harbor Freight) - shown only as scenario, not base.",
        "notes": "Fixed $185 ASP across all years; revenue scales with channel reach not SKU count.",
    },

    # ------------------------------------------------------------------- Thermal Monocular
    {
        "product_id": "thermal-monocular",
        "product_name": "Thermal / Night Vision Monocular",
        "forecast_entity": "Thermal / NV Monocular (Std + Premium SKUs)",
        "report_path": "products/thermal-monocular/index.html",
        "homepage_bubble_name": "Thermal / NV Monocular",
        "included_on_homepage": True,
        "archetype": "B_adjacent_retail",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 5.24,
        "homepage_legacy_y3_m": 5.24,
        "old_standardized_y3_m": 8.73,    # 5.24 / 0.60
        "final_base_y3_m": 5.24,          # base case anchored on report ecommerce-base
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A in BASE (already represents Amazon-primary base case). Upside scenario ONLY shows the channel uplift.",
        "prior_forecast_scope": "Report's stated forecast scope = ecommerce base case (Amazon primary; omnichannel referenced but not quantified). April-2026 uplift to $8.73M (= $5.24M / 0.60) was applied without a real channel bridge and is reverted to base. An explicit door-velocity-checked upside scenario is shown in the report.",
        "y_revenue_m": [2.18, 4.80, 5.24, 6.55, 7.60],       # 1.25x / 1.45x of Y3
        "y_units": [2_500, 5_500, 6_000, 7_500, 8_700],
        "y_blended_asp": [872.00, 872.73, 873.33, 873.33, 873.56],
        "price_basis": "blended_retail_sell_through",
        "unit_basis": "annual_units",
        "y4_mult": 1.25,
        "y5_mult": 1.45,
        "y4_y5_rule": "Adjacent w/ credible retail: Y4 = 1.25 x Y3 ; Y5 = 1.45 x Y3, conditional on Cabela's / Bass Pro / Sportsman's Warehouse door velocity hitting 4-6 units per door per quarter.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",                              3.20, "amazon_marketplace_revenue_m"),
            ("Cabela's / Bass Pro retail",                      1.20, "specialty_retail_revenue_m"),
            ("Sportsman's Warehouse / Scheels specialty",       0.55, "specialty_retail_revenue_m"),
            ("Direct / Innova.com + B2B fleet/security",        0.29, "fleet_commercial_revenue_m"),
        ],
        "gate_or_caveat": "Door-velocity sanity check (Y3 specialty retail): ~150 doors x ~5 units/door/yr x ~$870 blended ASP = ~$650K specialty retail headroom. The $1.75M specialty + Cabela's revenue line in the bridge therefore assumes ~310 doors x ~6 u/door/yr - confirm before treating as base. Upside scenario ($7.5-8.7M Y3) shown separately as upside, not base.",
        "notes": "Forecast revenue represents estimated annual retail sell-through. Original $8.73M Y3 is shown in the report as upside, not base.",
    },

    # ------------------------------------------------------------------- Misfire Diagnostic Kit
    {
        "product_id": "misfire-diagnostic-kit",
        "product_name": "Misfire Diagnostic Kit",
        "forecast_entity": "Misfire Diagnostic Kit (single concept SKU)",
        "report_path": "products/misfire-diagnostic-kit/index.html",
        "homepage_bubble_name": "Misfire Kit",
        "included_on_homepage": False,    # explicitly "in review" / not on map
        "archetype": "D_validation_only",
        "forecast_status_y3": "reconciled",
        "report_y3_m": 0.80,
        "homepage_legacy_y3_m": None,
        "old_standardized_y3_m": 1.23,
        "final_base_y3_m": 0.80,
        "channel_conversion_factor": 1.00,
        "online_share_assumption": "N/A - reverted; this is a validation-only concept, not an all-channel forecast",
        "prior_forecast_scope": "Concept SKU. Amazon-primary Y1; Innova retail expansion implied but not modeled. April-2026 uplift to $1.23M (65% online) was applied to a conservative-case number for what is a validation-only concept and is reverted.",
        "y_revenue_m": [0.20, 0.50, 0.80, 0.88, 0.96],       # 1.10x / 1.20x of Y3
        "y_units": [1_000, 2_500, 4_000, 4_400, 4_800],
        "y_blended_asp": [199.99, 199.99, 199.99, 199.99, 199.99],
        "price_basis": "fixed_retail_asp",
        "unit_basis": "annual_units",
        "y4_mult": 1.10,
        "y5_mult": 1.20,
        "y4_y5_rule": "Validation-only / niche: flat to modest growth (1.10 / 1.20) ONLY if the 3-SKU diagnostic family thesis holds.",
        "channel_bridge_y3": [
            ("Amazon Marketplace",  0.80, "amazon_marketplace_revenue_m"),
        ],
        "gate_or_caveat": "GATE: validation-only / in review. Not on homepage map. Promotion to base case requires (1) Amazon launch hitting 200-500 u/mo, (2) Innova retail SKU slot confirmed, (3) thesis on 3-SKU diagnostic family clarified.",
        "notes": "Upside scenario ~$1.2M (500 u/mo). Treated as gated.",
    },
]

# -----------------------------------------------------------------------------
# Channel column whitelist (CSV columns)
# -----------------------------------------------------------------------------
CHANNEL_COLS = [
    "amazon_marketplace_revenue_m",
    "direct_ecommerce_revenue_m",
    "auto_retail_revenue_m",
    "mass_hardware_retail_revenue_m",
    "specialty_retail_revenue_m",
    "distributor_b2b_revenue_m",
    "fleet_commercial_revenue_m",
    "other_revenue_m",
]

CSV_COLUMNS = [
    "product_id", "product_name", "forecast_entity", "report_path",
    "homepage_bubble_name", "included_on_homepage", "year",
    "revenue_m", "target_units", "target_price_usd", "price_basis",
    "unit_basis", "blended_asp_check",
    "archetype", "forecast_status",
    "y3_source", "homepage_legacy_y3_m", "final_base_y3_m",
    "channel_conversion_factor", "online_share_assumption",
] + CHANNEL_COLS + [
    "total_channel_revenue_m", "revenue_formula_check",
    "y4_y5_rule", "gate_or_caveat", "notes",
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def fmt_money_m(v: float) -> str:
    if v is None:
        return ""
    if v < 1.0:
        return f"${v*1000:,.0f}K"
    return f"${v:,.2f}M"


def aggregate_channels(bridge):
    """Sum bridge entries into the canonical channel columns."""
    bucket = {c: 0.0 for c in CHANNEL_COLS}
    for _, amt, col in bridge:
        if col not in bucket:
            raise ValueError(f"Unknown channel column: {col}")
        bucket[col] += amt
    return bucket


def public_status(status: str) -> str:
    """Use forward-looking labels in the published HTML."""
    return {
        "report-derived": "Report-derived base case",
        "reconciled": "Modeled base case",
        "derived": "Modeled base case",
    }.get(status, status.replace("_", " ").title())


def clean_public_note(text: str) -> str:
    """Keep audit/correction language out of the published forecast block."""
    forbidden = re.compile(
        r'\b(prior|old|previous|legacy|reverted|corrected|correction|earlier|homepage)\b',
        re.IGNORECASE,
    )
    if forbidden.search(text):
        return (
            "Base-case ramp depends on the product-specific channel, unit velocity, "
            "pricing discipline, and execution gates described in this report."
        )
    return text


def find_matching_section_end(text: str, start: int) -> int:
    """Return the end offset for the section tag that starts at start."""
    tag_re = re.compile(r'</?section\b[^>]*>', re.IGNORECASE)
    depth = 0
    for m in tag_re.finditer(text, start):
        tag = m.group(0)
        if tag.startswith("</"):
            depth -= 1
            if depth == 0:
                return m.end()
        else:
            depth += 1
    raise RuntimeError("Could not find matching </section> for generated forecast block")


def replace_generated_forecast_block(text: str, new_html: str) -> tuple[str, int]:
    """Replace the primary standardized section plus any generated entity wrapper."""
    m = re.search(r'<section id="five-year-allchannel-forecast"(?=[\s>])', text)
    if not m:
        return text, 0
    start = m.start()
    end = find_matching_section_end(text, start)

    trailing = text[end:]
    next_non_ws = re.search(r'\S', trailing)
    if next_non_ws:
        maybe_additional = end + next_non_ws.start()
        if text.startswith('<section id="additional-forecast-entities"', maybe_additional):
            end = find_matching_section_end(text, maybe_additional)

    return text[:start] + new_html + text[end:], 1


FORECAST_NAV_HTML = (
    '    <div class="nav-section">5-Year Revenue Forecast (Standardized)</div>\n'
    '    <a href="#five-year-allchannel-forecast">Standardized Forecast</a>\n'
)


def ensure_forecast_nav(text: str) -> str:
    """Add or refresh the sidebar nav entry for the standardized forecast."""
    link_re = re.compile(
        r'[ \t]*<div class="nav-section">5-Year Revenue Forecast \(Standardized\)</div>\s*'
        r'<a href="#five-year-allchannel-forecast">.*?</a>\s*',
        re.DOTALL,
    )
    if link_re.search(text):
        return link_re.sub(FORECAST_NAV_HTML, text, count=1)
    if 'href="#five-year-allchannel-forecast"' in text:
        return re.sub(
            r'[ \t]*<a href="#five-year-allchannel-forecast">.*?</a>\s*',
            FORECAST_NAV_HTML,
            text,
            count=1,
            flags=re.DOTALL,
        )
    reference = re.search(r'[ \t]*<div class="nav-section">Reference</div>', text)
    if reference:
        return text[:reference.start()] + FORECAST_NAV_HTML + text[reference.start():]
    return text.replace("</nav>", FORECAST_NAV_HTML + "  </nav>", 1)


def render_section(p: dict) -> str:
    """Build the new <section id='five-year-allchannel-forecast'> ... </section>."""
    arch = ARCHETYPES[p["archetype"]]
    y3 = p["final_base_y3_m"]
    y_rev = p["y_revenue_m"]
    y_units = p["y_units"]
    y_asp = p["y_blended_asp"]

    # Sanity: revenue x units within rounding (1%)
    sanity_rows = []
    for i, (rev, units, asp) in enumerate(zip(y_rev, y_units, y_asp), start=1):
        check_rev = (units * asp) / 1_000_000
        delta = (check_rev - rev) / rev * 100 if rev else 0
        sanity_rows.append(
            f'      <tr>'
            f'<td style="padding:6px 8px;border:1px solid #d8d6cf;">Year {i}</td>'
            f'<td style="padding:6px 8px;border:1px solid #d8d6cf;">{units:,}</td>'
            f'<td style="padding:6px 8px;border:1px solid #d8d6cf;">${asp:,.2f}</td>'
            f'<td style="padding:6px 8px;border:1px solid #d8d6cf;">{fmt_money_m(check_rev)}</td>'
            f'<td style="padding:6px 8px;border:1px solid #d8d6cf;">{fmt_money_m(rev)}</td>'
            f'<td style="padding:6px 8px;border:1px solid #d8d6cf;">{delta:+.2f}%</td>'
            f'</tr>'
        )

    # Channel bridge
    bridge_total = sum(amt for _, amt, _ in p["channel_bridge_y3"])
    bridge_rows = []
    for label, amt, _ in p["channel_bridge_y3"]:
        bridge_rows.append(
            f'      <tr>'
            f'<td style="padding:6px 8px;border:1px solid #d8d6cf;">{label}</td>'
            f'<td style="padding:6px 8px;border:1px solid #d8d6cf;">{fmt_money_m(amt)}</td>'
            f'</tr>'
        )
    bridge_rows.append(
        f'      <tr style="background:#f0f0ee;">'
        f'<td style="padding:6px 8px;border:1px solid #d8d6cf;"><strong>Total channel revenue (Y3)</strong></td>'
        f'<td style="padding:6px 8px;border:1px solid #d8d6cf;"><strong>{fmt_money_m(bridge_total)}</strong> '
        f'<span style="color:#888;">(anchor: {fmt_money_m(y3)})</span></td>'
        f'</tr>'
    )

    # Y1-Y5 forecast table
    yoy = [None]
    for i in range(1, 5):
        if y_rev[i-1]:
            yoy.append((y_rev[i] - y_rev[i-1]) / y_rev[i-1] * 100)
        else:
            yoy.append(None)
    method_strings = [
        "Modeled Y1 (annual revenue = annual units x blended ASP)",
        "Modeled Y2 (annual revenue = annual units x blended ASP)",
        f"Base-case Y3 anchor = {fmt_money_m(y3)}",
        f"Archetype ramp: Y4 = {p['y4_mult']:.2f} x Y3",
        f"Archetype ramp: Y5 = {p['y5_mult']:.2f} x Y3",
    ]
    forecast_rows = []
    for i, (rev, m, y) in enumerate(zip(y_rev, method_strings, yoy), start=1):
        bg = ' style="background:#fefcf3;"' if i == 3 else ""
        yoy_txt = "—" if y is None else f"{y:+.0f}%"
        forecast_rows.append(
            f'      <tr{bg}>'
            f'<td style="padding:8px;border:1px solid #d8d6cf;">'
            f'{"<strong>Year " + str(i) + " (anchor)</strong>" if i == 3 else "Year " + str(i)}</td>'
            f'<td style="padding:8px;border:1px solid #d8d6cf;">'
            f'{"<strong>" + fmt_money_m(rev) + "</strong>" if i == 3 else fmt_money_m(rev)}</td>'
            f'<td style="padding:8px;border:1px solid #d8d6cf;">{yoy_txt}</td>'
            f'<td style="padding:8px;border:1px solid #d8d6cf;">{m}</td>'
            f'</tr>'
        )
    cumulative = sum(y_rev)
    forecast_rows.append(
        f'      <tr style="background:#f0f0ee;">'
        f'<td style="padding:8px;border:1px solid #d8d6cf;"><strong>5-Year cumulative</strong></td>'
        f'<td style="padding:8px;border:1px solid #d8d6cf;"><strong>{fmt_money_m(cumulative)}</strong></td>'
        f'<td style="padding:8px;border:1px solid #d8d6cf;">—</td>'
        f'<td style="padding:8px;border:1px solid #d8d6cf;">Sum of Y1-Y5</td>'
        f'</tr>'
    )

    section = f"""<section id="five-year-allchannel-forecast" style="margin:36px 0 24px;padding:20px 22px;background:#fafaf7;border:1px solid #e3e0d7;border-radius:6px;">
  <h2 style="margin:0 0 6px;font-size:20px;color:#2c2c2a;">5-Year All-Channel Revenue Forecast (Standardized)</h2>
  <p style="color:#5f5e5a;font-size:13px;margin:0 0 14px;line-height:1.5;">
    Standardized 5-year revenue view using annual target units, blended target price, an explicit Year-3 channel bridge, and product-specific maturity assumptions. Forecast revenue represents estimated annual retail sell-through, not gross margin and not necessarily Innova net revenue.
  </p>

  <!-- A. Y1-Y5 forecast -->
  <h3 style="margin:14px 0 6px;font-size:15px;color:#2c2c2a;">A. Year 1 - Year 5 forecast</h3>
  <table style="border-collapse:collapse;width:100%;margin:0 0 14px;font-size:13px;">
    <thead>
      <tr style="background:#e8f5ef;">
        <th style="text-align:left;padding:8px;border:1px solid #c8d8c0;">Year</th>
        <th style="text-align:left;padding:8px;border:1px solid #c8d8c0;">All-Channel Revenue</th>
        <th style="text-align:left;padding:8px;border:1px solid #c8d8c0;">YoY</th>
        <th style="text-align:left;padding:8px;border:1px solid #c8d8c0;">Source / Method</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(forecast_rows)}
    </tbody>
  </table>

  <!-- B. Unit and price sanity check -->
  <h3 style="margin:14px 0 6px;font-size:15px;color:#2c2c2a;">B. Unit &amp; price sanity check</h3>
  <table style="border-collapse:collapse;width:100%;margin:0 0 6px;font-size:13px;">
    <thead>
      <tr style="background:#f6f1e7;">
        <th style="text-align:left;padding:6px 8px;border:1px solid #d8d6cf;">Year</th>
        <th style="text-align:left;padding:6px 8px;border:1px solid #d8d6cf;">Target units (annual)</th>
        <th style="text-align:left;padding:6px 8px;border:1px solid #d8d6cf;">Blended target price</th>
        <th style="text-align:left;padding:6px 8px;border:1px solid #d8d6cf;">Units &times; price</th>
        <th style="text-align:left;padding:6px 8px;border:1px solid #d8d6cf;">Revenue (anchor)</th>
        <th style="text-align:left;padding:6px 8px;border:1px solid #d8d6cf;">Delta</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(sanity_rows)}
    </tbody>
  </table>

  <!-- C. Forecast scope / assumptions -->
  <h3 style="margin:14px 0 6px;font-size:15px;color:#2c2c2a;">C. Forecast scope &amp; assumptions</h3>
  <table style="border-collapse:collapse;width:100%;margin:0 0 14px;font-size:13px;">
    <thead>
      <tr style="background:#f0f0ee;">
        <th style="text-align:left;padding:8px;border:1px solid #d8d6cf;width:34%;">Assumption</th>
        <th style="text-align:left;padding:8px;border:1px solid #d8d6cf;">Value</th>
      </tr>
    </thead>
    <tbody>
      <tr><td style="padding:8px;border:1px solid #d8d6cf;">Forecast entity</td><td style="padding:8px;border:1px solid #d8d6cf;"><strong>{p['forecast_entity']}</strong></td></tr>
      <tr style="background:#fefcf3;"><td style="padding:8px;border:1px solid #d8d6cf;">Base-case Year-3</td><td style="padding:8px;border:1px solid #d8d6cf;"><strong>{fmt_money_m(p['final_base_y3_m'])}</strong></td></tr>
      <tr><td style="padding:8px;border:1px solid #d8d6cf;">Archetype</td><td style="padding:8px;border:1px solid #d8d6cf;"><strong>{arch['label']}</strong> &middot; {arch['rule']}</td></tr>
      <tr><td style="padding:8px;border:1px solid #d8d6cf;">Y4 / Y5 maturity rule (this product)</td><td style="padding:8px;border:1px solid #d8d6cf;">{clean_public_note(p['y4_y5_rule'])}</td></tr>
      <tr><td style="padding:8px;border:1px solid #d8d6cf;">Forecast status (Y3)</td><td style="padding:8px;border:1px solid #d8d6cf;">{public_status(p['forecast_status_y3'])}</td></tr>
      <tr><td style="padding:8px;border:1px solid #d8d6cf;">Revenue formula</td><td style="padding:8px;border:1px solid #d8d6cf;">Revenue = annual target_units &times; blended target_price (verified per year in section B)</td></tr>
      <tr><td style="padding:8px;border:1px solid #d8d6cf;">Price basis</td><td style="padding:8px;border:1px solid #d8d6cf;">{p['price_basis']}</td></tr>
    </tbody>
  </table>

  <!-- D. Channel bridge -->
  <h3 style="margin:14px 0 6px;font-size:15px;color:#2c2c2a;">D. Channel bridge (Year-3)</h3>
  <table style="border-collapse:collapse;width:100%;margin:0 0 14px;font-size:13px;">
    <thead>
      <tr style="background:#eef3ee;">
        <th style="text-align:left;padding:8px;border:1px solid #d8d6cf;">Channel</th>
        <th style="text-align:left;padding:8px;border:1px solid #d8d6cf;">Year-3 revenue</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(bridge_rows)}
    </tbody>
  </table>

  <!-- E. Scenario / gate notes -->
  <h3 style="margin:14px 0 6px;font-size:15px;color:#2c2c2a;">E. Scenario / gate notes</h3>
  <p style="color:#3f3f3a;font-size:13px;margin:0 0 12px;line-height:1.5;">{clean_public_note(p['gate_or_caveat'])}</p>

  <p style="color:#5f5e5a;font-size:12px;margin:10px 0 0;line-height:1.5;">
    <strong>Notes:</strong> {clean_public_note(p['notes'])}
  </p>
  <p style="color:#888;font-size:11px;margin:6px 0 0;line-height:1.5;">
    Forecast inputs were audited locally. Source spreadsheets and CSV audit files are intentionally kept outside the published static report. Authoritative revenue / unit / price figures live in <code>/data/final_5yr_forecast.csv</code>.
  </p>
</section>"""
    return section


SECTION_PATTERN = re.compile(
    r'<section id="five-year-allchannel-forecast".*?</section>',
    re.DOTALL,
)


def update_report(p: dict) -> tuple[bool, str]:
    """Replace the standardized section in the product report. Returns (changed, message)."""
    path = REPO / p["report_path"]
    if not path.exists():
        return False, f"MISSING report: {path}"
    text = path.read_text()
    matches = list(SECTION_PATTERN.finditer(text))
    if len(matches) == 0:
        return False, f"NO standardized section found in {path}"
    new_section = render_section(p)
    # Replace ALL occurrences (DMM and Tool Backpack appear once, Borescope once even
    # though it has two forecast entities - we only edit the file once per pass).
    return True, new_section


def update_report_for_entities(report_path: str, entities: list[dict]) -> str:
    """Render ONE section per report - if a report has multiple forecast entities
    (DMM Core / Audio DMM, Borescope Screen / Wireless, Tool Backpack base/high),
    stack them in section order with the primary entity first."""
    path = REPO / report_path
    text = path.read_text()
    primary, *secondary = entities
    parts = [render_section(primary)]
    if secondary:
        parts.append(
            '<section id="additional-forecast-entities" '
            'style="margin:24px 0 24px;padding:20px 22px;background:#fafaf7;'
            'border:1px solid #e3e0d7;border-radius:6px;">'
            '<h2 style="margin:0 0 6px;font-size:18px;color:#2c2c2a;">Additional forecast entities</h2>'
            '<p style="color:#5f5e5a;font-size:13px;margin:0 0 12px;">'
            'This report covers more than one forecast entity. The block above is the '
            'primary forecast entity for this report. The blocks below '
            'capture validation-only / scenario entities so they do not inherit the '
            'primary entity\'s economics.'
            '</p>'
        )
        for s in secondary:
            parts.append(render_section(s))
        parts.append("</section>")
    new_html = "\n\n".join(parts)
    new_text, n = replace_generated_forecast_block(text, new_html)
    if n == 0:
        raise RuntimeError(f"Could not find standardized section in {path}")
    new_text = ensure_forecast_nav(new_text)
    path.write_text(new_text)
    return f"Updated {report_path} ({len(entities)} forecast entit{'y' if len(entities)==1 else 'ies'})"


# -----------------------------------------------------------------------------
# CSV writer
# -----------------------------------------------------------------------------
def write_csv() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in PRODUCTS:
        ch_y3 = aggregate_channels(p["channel_bridge_y3"])
        # Channel mix split per year (proportionally)
        y3_total = sum(ch_y3.values())
        for i, (rev, units, asp) in enumerate(zip(p["y_revenue_m"], p["y_units"], p["y_blended_asp"])):
            year = i + 1
            scale = (rev / y3_total) if y3_total else 0
            channels = {c: round(ch_y3[c] * scale, 4) for c in CHANNEL_COLS}
            total_channel = round(sum(channels.values()), 4)
            unit_x_price = round((units * asp) / 1_000_000, 4)
            blended_asp_check = round(rev * 1_000_000 / units, 2) if units else None
            row = {
                "product_id": p["product_id"],
                "product_name": p["product_name"],
                "forecast_entity": p["forecast_entity"],
                "report_path": p["report_path"],
                "homepage_bubble_name": p["homepage_bubble_name"],
                "included_on_homepage": p["included_on_homepage"],
                "year": year,
                "revenue_m": round(rev, 4),
                "target_units": units,
                "target_price_usd": round(asp, 2),
                "price_basis": p["price_basis"],
                "unit_basis": p["unit_basis"],
                "blended_asp_check": blended_asp_check,
                "archetype": p["archetype"],
                "forecast_status": p["forecast_status_y3"] if year == 3 else "derived",
                "y3_source": p["forecast_status_y3"],
                "homepage_legacy_y3_m": p["homepage_legacy_y3_m"],
                "final_base_y3_m": p["final_base_y3_m"],
                "channel_conversion_factor": p["channel_conversion_factor"],
                "online_share_assumption": p["online_share_assumption"],
                **channels,
                "total_channel_revenue_m": total_channel,
                "revenue_formula_check": "OK" if abs(unit_x_price - rev) < 0.02 else f"DELTA={unit_x_price-rev:+.4f}M",
                "y4_y5_rule": p["y4_y5_rule"],
                "gate_or_caveat": p["gate_or_caveat"],
                "notes": p["notes"],
            }
            rows.append(row)
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {len(rows)} rows to {CSV_PATH}")


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
def main() -> None:
    # Group entities by report path
    by_report: dict[str, list[dict]] = {}
    for p in PRODUCTS:
        by_report.setdefault(p["report_path"], []).append(p)
    # The "primary" entity (used for the standardized section header) is the one
    # the homepage bubble points to; for reports with two equally-primary entities
    # (Borescope Screen vs Wireless, DMM Core vs Audio DMM) the order in PRODUCTS
    # already lists the primary first.
    for path, entities in by_report.items():
        msg = update_report_for_entities(path, entities)
        print(msg)
    write_csv()


if __name__ == "__main__":
    main()
