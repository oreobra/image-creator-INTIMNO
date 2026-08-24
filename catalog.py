"""
catalog.py — INTIMNO product catalog loader and search.

Downloads the Google Sheets workbook as XLSX (preserves hyperlinks!),
caches to disk, and auto-refreshes once per week.
Search is done locally with rapidfuzz — zero AI tokens consumed.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import time
from typing import TypedDict

import aiohttp
import openpyxl

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
    ishodniki: str        # URL исходников (Яндекс Диск)
    predmetka: str        # URL предметки (Google Drive)
    predmetka_label: str  # Название папки если нет URL
    na_modelyah: str      # URL «на моделях» (Google Drive)
    infografika: str      # URL инфографики
    comment: str          # Комментарий


# ──────────────────────────────────────────────────────────
#  In-memory store
# ──────────────────────────────────────────────────────────

_catalog: list[CatalogItem] = []
_loaded_at: float = 0.0

# Categories included in navigation/search
_INCLUDED_CATEGORIES_UPPER = {"НИЖНЕЕ БЕЛЬЕ", "БЫСТРЫЕ ЗАПУСКИ"}

# Placeholder strings that mean "no data"
_PLACEHOLDERS = {
    "", "-", "—", "нет", "нет ссылки",
    "исходники", "исходники тут",
    "предметка тут", "студия тут", "студия",
}


# ──────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────

def _cell_url(cell) -> str:
    """Return the hyperlink URL of a cell, or '' if none."""
    if cell.hyperlink and cell.hyperlink.target:
        return cell.hyperlink.target.strip()
    return ""


def _cell_val(cell) -> str:
    """Return the text value of a cell as a stripped string."""
    v = cell.value
    if v is None:
        return ""
    return str(v).strip()


def _clean(v: str) -> str:
    """Return v or '' if it is a known placeholder."""
    return "" if v.lower() in _PLACEHOLDERS else v


def _best_url(cell) -> str:
    """
    Best URL for a cell:
    1. Hyperlink target (Google Drive chip, or linked text)
    2. Cell value if it starts with http
    3. ''
    """
    url = _cell_url(cell)
    if url:
        return url
    val = _cell_val(cell)
    if val.startswith("http"):
        # Take first non-empty line (multi-line cells)
        for line in val.splitlines():
            line = line.strip()
            if line.startswith("http"):
                return line
    return ""


# ──────────────────────────────────────────────────────────
#  XLSX parsing
# ──────────────────────────────────────────────────────────

def _parse_xlsx(xlsx_bytes: bytes) -> list[CatalogItem]:
    """Parse the Google Sheets XLSX export into CatalogItem list."""
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    ws = wb.active

    items: list[CatalogItem] = []
    current_category = ""

    rows = list(ws.iter_rows())
    # Skip header row (row 0)
    for row in rows[1:]:
        # Pad to at least 8 columns
        while len(row) < 8:
            row = list(row) + [None]  # type: ignore[assignment]

        article_cell   = row[0]
        wb_cell        = row[1]
        ozon_cell      = row[2]
        ish_cell       = row[3]
        pred_cell      = row[4]
        inf_cell       = row[5]
        mod_cell       = row[6]
        comment_cell   = row[7]

        article = _cell_val(article_cell)

        # Detect category header rows (ALL CAPS, no other content)
        if (
            article
            and article.upper() == article
            and not _cell_val(wb_cell)
            and not _cell_val(ozon_cell)
            and not _cell_val(ish_cell)
        ):
            current_category = article
            continue

        if not article:
            continue

        if current_category.upper() not in _INCLUDED_CATEGORIES_UPPER:
            continue

        category = (
            "НИЖНЕЕ БЕЛЬЕ" if "НИЖНЕЕ БЕЛЬЕ" in current_category.upper()
            else "БЫСТРЫЕ ЗАПУСКИ"
        )

        wb_url   = _clean(_best_url(wb_cell))
        ozon_url = _clean(_best_url(ozon_cell))
        ish_url  = _clean(_best_url(ish_cell))
        pred_url = _clean(_best_url(pred_cell))
        inf_url  = _clean(_best_url(inf_cell))
        mod_url  = _clean(_best_url(mod_cell))

        # Folder label for predmetka when no URL available
        pred_label = ""
        if not pred_url:
            pred_label = _clean(_cell_val(pred_cell))

        # Comment: use hyperlink if present, else text
        comment_url = _cell_url(comment_cell)
        comment_txt = _clean(_cell_val(comment_cell))
        if comment_url:
            comment = comment_txt or "ссылка"
            # We'll store URL in comment for now; it will show as text
            comment = f"{comment_txt} ({comment_url})" if comment_txt else comment_url
        else:
            comment = comment_txt

        items.append(CatalogItem(
            article=article,
            category=category,
            wb=wb_url,
            ozon=ozon_url,
            ishodniki=ish_url,
            predmetka=pred_url,
            predmetka_label=pred_label,
            na_modelyah=mod_url,
            infografika=inf_url,
            comment=comment,
        ))

    return items


# ──────────────────────────────────────────────────────────
#  Loading and caching
# ──────────────────────────────────────────────────────────

# XLSX download URL (public, no auth required)
_XLSX_URL = config.CATALOG_SHEET_URL.replace("format=csv", "format=xlsx")


async def _fetch_xlsx() -> bytes:
    """Download the XLSX export from Google Sheets."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            _XLSX_URL,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            resp.raise_for_status()
            return await resp.read()


def _save_cache(items: list[CatalogItem]) -> None:
    """Persist catalog to disk."""
    try:
        data = {"saved_at": time.time(), "items": items}
        with open(config.CATALOG_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        log.warning("Could not save catalog cache: %s", exc)


def _load_cache() -> list[CatalogItem] | None:
    """Load catalog from disk cache."""
    try:
        with open(config.CATALOG_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        age_days = (time.time() - data.get("saved_at", 0)) / 86_400
        if age_days > config.CATALOG_REFRESH_INTERVAL_DAYS:
            log.info("Cache is %d days old, will refresh.", int(age_days))
        return data["items"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None


async def refresh_catalog() -> None:
    """Download XLSX, parse it, update in-memory store and cache."""
    global _catalog, _loaded_at

    try:
        xlsx_bytes = await _fetch_xlsx()
    except Exception as exc:
        log.error("Failed to fetch catalog XLSX: %s", exc)
        return

    items = _parse_xlsx(xlsx_bytes)
    _catalog = items
    _loaded_at = time.time()
    _save_cache(items)
    log.info("Catalog refreshed: %d items loaded.", len(items))


async def load_catalog() -> None:
    """Called once at bot startup."""
    global _catalog, _loaded_at

    cached = _load_cache()
    if cached:
        _catalog = cached
        _loaded_at = time.time()
        log.info("Catalog loaded from cache: %d items.", len(_catalog))
        # Refresh in background without blocking startup
        asyncio.create_task(refresh_catalog())
    else:
        log.info("No catalog cache found, fetching fresh…")
        await refresh_catalog()


async def schedule_weekly_refresh() -> None:
    """Background task: refresh catalog once per week."""
    interval_seconds = config.CATALOG_REFRESH_INTERVAL_DAYS * 86_400
    while True:
        await asyncio.sleep(interval_seconds)
        log.info("Weekly catalog refresh triggered.")
        await refresh_catalog()


# ──────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────

def get_catalog() -> list[CatalogItem]:
    return _catalog


def get_by_category(category: str) -> list[CatalogItem]:
    cat_upper = category.upper()
    return [item for item in _catalog if item["category"].upper() == cat_upper]


def get_by_article(article: str) -> CatalogItem | None:
    for item in _catalog:
        if item["article"] == article:
            return item
    return None


def search_catalog(query: str, limit: int = 8) -> list[CatalogItem]:
    """Fuzzy search across article names — zero AI tokens."""
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
