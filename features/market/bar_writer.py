"""Periodic job: ClickHouse ticks → MySQL market_bars for local K-line replay."""

from __future__ import annotations

import logging
import threading
import time

from features.market.bar_aggregator import aggregate_current_trade_dates, aggregate_recent

logger = logging.getLogger("stabx.bar_writer")

# Refresh current day often; backfill recent days less frequently.
_CURRENT_SEC = 60.0
_BACKFILL_EVERY = 30  # cycles (~30 min) between multi-day backfills
_BACKFILL_DAYS = 5

_thread: threading.Thread | None = None
_stop = threading.Event()
_cycle = 0


def start_bar_writer() -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_run, name="mysql-bar-writer", daemon=True)
    _thread.start()
    logger.info("MySQL bar aggregator started (every %ss)", int(_CURRENT_SEC))


def stop_bar_writer() -> None:
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=2.0)


def _run() -> None:
    global _cycle
    # First pass: backfill so K-line has history after restart.
    try:
        summary = aggregate_recent(days=_BACKFILL_DAYS)
        logger.info(
            "bar backfill done contracts=%s days=%s",
            summary.get("contracts"),
            summary.get("days"),
        )
    except Exception:
        logger.exception("bar backfill failed")

    while not _stop.is_set():
        if _stop.wait(_CURRENT_SEC):
            break
        _cycle += 1
        try:
            aggregate_current_trade_dates()
        except Exception:
            logger.exception("bar current-day aggregate failed")
        if _cycle % _BACKFILL_EVERY == 0:
            try:
                aggregate_recent(days=_BACKFILL_DAYS)
            except Exception:
                logger.exception("bar periodic backfill failed")
