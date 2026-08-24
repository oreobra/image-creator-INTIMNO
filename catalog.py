"""
catalog.py — INTIMNO product catalog loader and search.

Reads data from a public Google Sheets CSV export (no API key needed).
Caches the result to disk and auto-refreshes once per week.
Search is done locally with rapidfuzz — zero AI tokens consumed.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import time
from typing import TypedDict

import aiohttp

import config

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────
#  Types
# ──────────────────────────────────────────────────────────

class CatalogItem(TypedDict):
    article: str          # Артикул
    category: str         # НИЖНЕЕ БЕЛЬЕ | БЫСТРЫЕ ЗАПУСКИ
    wb: str               # Ссылка WB
    ozon: str             # Ссылка Ozon
    ishodniki: str        # Исходники
    predmetka: str        # Предметка
    na_modelyah: str      # На моделях
    infografika: str      # Инфографика
    comment: str          # Комментарий


# ──────────────────────────────────────────────────────────
#  In-memory store
# ──────────────────────────────────────────────────────────

_catalog: list[CatalogItem] = []
_last_csv_hash: str = ""
_loaded_at: float = 0.0

# Categories included in navigation/search
_INCLUDED_CATEGORIES_UPPER = {"НИЖНЕЕ БЕЛЬЕ", "БЫСТРЫЕ ЗАПУСКИ"}


# ──────────────────────────────────────────────────────────
#  CSV parsing
# ──────────────────────────────────────────────────────────

def _parse_csv(csv_text: str) -> list[CatalogItem]:
    """Parse the Google Sheets CSV into a list of CatalogItem dicts."""
    items: list[CatalogItem] = []
    current_category = ""

    reader = csv.reader(io.StringIO(csv_text))

    # Skip header row
    next(reader, None)

    for row in reader:
        # Pad short rows
        while len(row) < 8:
            row.append("")

        article   = row[0].strip()
        wb        = row[1].strip()
        ozon      = row[2].strip()
        ishodniki = row[3].strip()
        predmetka = row[4].strip()
        infograf  = row[5].strip()
        na_mod    = row[6].strip()
        comment   = row[7].strip()

        # Detect category header rows (ALL CAPS, no links in other columns)
        if (
            article
            and article.upper() == article
            and not wb
            and not ozon
            and not ishodniki
        ):
            current_category = article.strip()
            continue

        # Skip blank article rows
        if not article:
            continue

        # Only include the two target categories
        if current_category.upper() not in _INCLUDED_CATEGORIES_UPPER:
            continue

        # Normalise category name
        category = (
            "НИЖНЕЕ БЕЛЬЕ" if "НИЖНЕЕ БЕЛЬЕ" in current_category.upper()
            else "БЫСТРЫЕ ЗАПУСКИ"
        )

        # Treat placeholder strings as empty
        _PLACEHOLDERS = {"-", "исходники", "исходники тут", "предметка тут", "студия тут"}

        def _clean(v: str) -> str:
            return v if v and v not in _PLACEHOLDERS else ""

        items.append(CatalogItem(
            article=article,
            category=category,
            wb=_clean(wb),
            ozon=_clean(ozon),
            ishodniki=_clean(ishodniki),
            predmetka=_clean(predmetka),
            na_modelyah=_clean(na_mod),
            infografika=_clean(infograf),
            comment=comment,
        ))

    return items


# ──────────────────────────────────────────────────────────
#  Loading and caching
# ──────────────────────────────────────────────────────────

async def _fetch_csv() -> str:
    """Download the CSV export from Google Sheets."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            config.CATALOG_SHEET_URL,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            return await resp.text(encoding="utf-8", errors="replace")


def _save_cache(items: list[CatalogItem], csv_hash: str) -> None:
    """Persist catalog to disk so restarts don't re-fetch unnecessarily."""
    try:
        data = {"hash": csv_hash, "saved_at": time.time(), "items": items}
        with open(config.CATALOG_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        log.warning("Could not save catalog cache: %s", exc)


def _load_cache() -> tuple[list[CatalogItem], str] | None:
    """Load catalog from disk cache. Returns None if cache is missing/corrupt."""
    try:
        with open(config.CATALOG_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data["items"], data["hash"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None


async def refresh_catalog(force: bool = False) -> None:
    """
    Download the catalog CSV, parse it, and update the in-memory store.
    If the CSV hash hasn't changed (and force=False), skips the update.
    """
    global _catalog, _last_csv_hash, _loaded_at

    try:
        csv_text = await _fetch_csv()
    except Exception as exc:
        log.error("Failed to fetch catalog CSV: %s", exc)
        return

    new_hash = hashlib.md5(csv_text.encode("utf-8")).hexdigest()

    if not force and new_hash == _last_csv_hash:
        log.info("Catalog CSV unchanged, skipping parse.")
        _loaded_at = time.time()
        return

    items = _parse_csv(csv_text)
    _catalog = items
    _last_csv_hash = new_hash
    _loaded_at = time.time()

    _save_cache(items, new_hash)
    log.info("Catalog refreshed: %d items loaded.", len(items))


async def load_catalog() -> None:
    """
    Called once at bot startup.
    Tries disk cache first, then fetches fresh if needed.
    """
    global _catalog, _last_csv_hash, _loaded_at

    cached = _load_cache()
    if cached:
        _catalog, _last_csv_hash = cached
        _loaded_at = time.time()
        log.info("Catalog loaded from cache: %d items.", len(_catalog))
        # Refresh in background without blocking startup
        asyncio.create_task(refresh_catalog())
    else:
        log.info("No catalog cache found, fetching fresh…")
        await refresh_catalog(force=True)


async def schedule_weekly_refresh() -> None:
    """Background task: check for catalog updates once per week."""
    interval_seconds = config.CATALOG_REFRESH_INTERVAL_DAYS * 86_400
    while True:
        await asyncio.sleep(interval_seconds)
        log.info("Weekly catalog refresh triggered.")
        await refresh_catalog()


# ──────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────

def get_catalog() -> list[CatalogItem]:
    """Return the full cached catalog (only target categories)."""
    return _catalog


def get_by_category(category: str) -> list[CatalogItem]:
    """Return items for a given category (case-insensitive)."""
    cat_upper = category.upper()
    return [item for item in _catalog if item["category"].upper() == cat_upper]


def get_by_article(article: str) -> CatalogItem | None:
    """Exact lookup by article name."""
    for item in _catalog:
        if item["article"] == article:
            return item
    return None


def search_catalog(query: str, limit: int = 8) -> list[CatalogItem]:
    """
    Fuzzy search across article names.
    Uses rapidfuzz for speed — zero AI tokens, sub-millisecond.
    Falls back to simple substring match if rapidfuzz is unavailable.
    """
    if not query.strip():
        return []

    query_lower = query.lower().strip()

    try:
        from rapidfuzz import fuzz, process as rfprocess

        choices = {item["article"]: item for item in _catalog}
        results = rfprocess.extract(
            query_lower,
            choices.keys(),
            scorer=fuzz.partial_ratio,
            limit=limit,
            score_cutoff=45,
        )
        results.sort(key=lambda x: x[1], reverse=True)
        return [choices[name] for name, score, _ in results]

    except ImportError:
        log.warning("rapidfuzz not installed, falling back to substring search")
        hits = [
            item for item in _catalog
            if query_lower in item["article"].lower()
        ]
        return hits[:limit]
