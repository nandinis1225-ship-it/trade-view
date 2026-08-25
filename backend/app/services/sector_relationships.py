"""Centralized sector relationship graph for cross-sector news propagation.

One-hop propagation only: secondary impacts are derived from each primary sector
impact in the event payload. No recursive / chained propagation.
"""

from __future__ import annotations

import json
import math
from typing import Any

from app.models import NewsEvent
from app.services.sector_service import TRADEVERSE_SECTORS

# Canonical slugs — must match tradeverse_universe.json / sector_service.TRADEVERSE_SECTORS
CANONICAL_SECTOR_SLUGS = frozenset(slug for slug, _, _ in TRADEVERSE_SECTORS)

# Normalize timeline / legacy sector names → canonical slug keys
SECTOR_ALIASES: dict[str, str] = {
    "financials": "financials",
    "finance": "financials",
    "financial services": "financials",
    "banking": "financials",
    "it": "it",
    "technology": "it",
    "tech": "it",
    "automobiles": "automobiles",
    "automotive": "automobiles",
    "auto": "automobiles",
    "transportation": "automobiles",
    "energy": "energy",
    "power": "energy",
    "industrials": "industrials",
    "industrial": "industrials",
    "manufacturing": "industrials",
    "infrastructure": "infrastructure",
    "infra": "infrastructure",
    "real estate": "real_estate",
    "real_estate": "real_estate",
    "metals": "metals",
    "metal": "metals",
    "industrial minerals": "metals",
    "consumer": "consumer",
    "healthcare": "consumer",
    "broad market": "broad_market",
    "broad_market": "broad_market",
    "power / infrastructure": "infrastructure",
}

# Directional one-hop relationships: primary_sector → {related_sector: coefficient}
# Coefficients are bounded to [-1.0, +1.0]. Zero means no link (omit entry).
SECTOR_RELATIONSHIPS: dict[str, dict[str, float]] = {
    "financials": {
        "real_estate": 0.65,
        "infrastructure": 0.35,
        "consumer": 0.25,
    },
    "real_estate": {
        "financials": 0.60,
        "infrastructure": 0.50,
        "metals": 0.25,
        "consumer": 0.20,
    },
    "infrastructure": {
        "industrials": 0.60,
        "energy": 0.50,
        "metals": 0.40,
        "financials": 0.30,
    },
    "energy": {
        "industrials": 0.30,
        "automobiles": -0.25,
        "consumer": -0.10,
    },
    "metals": {
        "industrials": 0.45,
        "infrastructure": 0.35,
        "automobiles": 0.15,
    },
    "automobiles": {
        "metals": 0.25,
        "financials": 0.20,
        "consumer": 0.35,
        "energy": -0.20,
    },
    "it": {
        "financials": 0.15,
        "consumer": 0.10,
    },
    "consumer": {
        "automobiles": 0.35,
        "financials": 0.20,
    },
    "industrials": {
        "infrastructure": 0.35,
        "metals": 0.30,
        "energy": 0.20,
    },
}

# Per-sector multipliers for explicit market-wide events (base × multiplier)
MARKET_WIDE_SECTOR_MULTIPLIERS: dict[str, float] = {
    "financials": 1.00,
    "it": 0.90,
    "infrastructure": 0.85,
    "metals": 0.80,
    "industrials": 0.85,
    "energy": 0.80,
    "automobiles": 0.75,
    "real_estate": 0.70,
    "consumer": 0.70,
}

COEFFICIENT_MIN = -1.0
COEFFICIENT_MAX = 1.0


def normalize_sector_slug(raw: str) -> str:
    key = str(raw).strip().lower()
    return SECTOR_ALIASES.get(key, key)


def _clamp_coefficient(value: float) -> float:
    return max(COEFFICIENT_MIN, min(COEFFICIENT_MAX, value))


def _bound_secondary(secondary: float, primary: float) -> float:
    """Secondary absolute impact cannot exceed the originating primary impact."""
    cap = abs(primary)
    if abs(secondary) > cap:
        return math.copysign(cap, secondary)
    return secondary


def _merge_sector_impact(current: float | None, incoming: float, *, is_primary: bool) -> float:
    if current is None:
        return incoming
    if is_primary:
        # Primary sector always keeps the strongest primary assignment.
        if abs(incoming) >= abs(current):
            return incoming
        return current
    # Secondary: keep the dominant (largest absolute) secondary contribution.
    if abs(incoming) > abs(current):
        return incoming
    return current


def parse_primary_sector_impacts(raw: str | None) -> dict[str, float]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    primary: dict[str, float] = {}
    for key, value in data.items():
        slug = normalize_sector_slug(str(key))
        if slug == "broad_market":
            continue
        try:
            primary[slug] = float(value)
        except (TypeError, ValueError):
            continue
    return primary


def expand_sector_impacts(
    primary_impacts: dict[str, float],
    *,
    market_wide_base: float | None = None,
) -> dict[str, float]:
    """Expand primary sector impacts through the relationship graph (one hop only)."""
    expanded: dict[str, float] = {}
    primary_slugs = set(primary_impacts.keys())

    if market_wide_base is not None:
        for slug, multiplier in MARKET_WIDE_SECTOR_MULTIPLIERS.items():
            if slug not in CANONICAL_SECTOR_SLUGS:
                continue
            impact = market_wide_base * multiplier
            expanded[slug] = _merge_sector_impact(expanded.get(slug), impact, is_primary=True)

    for primary_slug, primary_pct in primary_impacts.items():
        if primary_slug not in CANONICAL_SECTOR_SLUGS and primary_slug != "broad_market":
            continue

        expanded[primary_slug] = _merge_sector_impact(
            expanded.get(primary_slug),
            primary_pct,
            is_primary=True,
        )

        for related_raw, coeff_raw in SECTOR_RELATIONSHIPS.get(primary_slug, {}).items():
            related_slug = normalize_sector_slug(related_raw)
            if related_slug not in CANONICAL_SECTOR_SLUGS:
                continue
            coeff = _clamp_coefficient(float(coeff_raw))
            if coeff == 0.0:
                continue

            secondary = _bound_secondary(primary_pct * coeff, primary_pct)

            # Primary sector assignment always dominates for that sector.
            if related_slug in primary_slugs:
                continue

            expanded[related_slug] = _merge_sector_impact(
                expanded.get(related_slug),
                secondary,
                is_primary=False,
            )

    return expanded


def expanded_sector_map_for_event(event: NewsEvent) -> dict[str, float]:
    """Resolved sector impact targets for an event (primary + one-hop secondary)."""
    primary = parse_primary_sector_impacts(event.sector_impacts_json)

    market_wide_base: float | None = None
    if event.market_wide and event.market_wide_impact_pct is not None:
        market_wide_base = float(event.market_wide_impact_pct)
    elif not primary and event.market_wide_impact_pct is not None:
        # Legacy flat market-wide without per-sector payload
        market_wide_base = float(event.market_wide_impact_pct)

    if market_wide_base is not None and not primary:
        return expand_sector_impacts({}, market_wide_base=market_wide_base)

    if market_wide_base is not None and primary:
        # Rare: both declared — apply market-wide base then overlay explicit primaries.
        merged = expand_sector_impacts({}, market_wide_base=market_wide_base)
        for slug, pct in expand_sector_impacts(primary).items():
            if slug in primary:
                merged[slug] = pct
            elif slug not in merged or abs(pct) > abs(merged[slug]):
                merged[slug] = pct
        return merged

    return expand_sector_impacts(primary)
