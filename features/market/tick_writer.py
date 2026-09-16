"""Async batch writer: EVENT_TICK → ClickHouse. Never blocks EventEngine."""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any

from core.clickhouse import insert_ticks
from core.metrics import metrics

logger = logging.getLogger("stabx.tick_writer")

_BATCH = 400
_FLUSH_SEC = 1.0
_MAX_QUEUE = 50_000

_q: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=_MAX_QUEUE)
_thread: threading.Thread | None = None
_stop = threading.Event()
_drops = 0


def enqueue_tick(payload: dict[str, Any]) -> None:
    """Non-blocking. Drops if the queue is full (live chart still works)."""
    global _drops
    try:
        _q.put_nowait(dict(payload))
    except queue.Full:
        _drops += 1
        metrics.note_ch_drop()


def queue_stats() -> dict[str, int]:
    """P8: ClickHouse writer queue depth for /health metrics."""
    return {"depth": _q.qsize(), "max": _MAX_QUEUE, "drops": _drops}


def start_tick_writer() -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    metrics.bind_ch_depth(queue_stats)
    _thread = threading.Thread(target=_run, name="ch-tick-writer", daemon=True)
    _thread.start()
    logger.info("ClickHouse tick writer started")


def stop_tick_writer() -> None:
    _stop.set()
    try:
        _q.put_nowait(None)
    except queue.Full:
        pass
    if _thread is not None:
        _thread.join(timeout=2.0)


def _run() -> None:
    batch: list[dict[str, Any]] = []
    while not _stop.is_set():
        try:
            item = _q.get(timeout=_FLUSH_SEC)
        except queue.Empty:
            _flush(batch)
            batch = []
            continue
        if item is None:
            break
        batch.append(item)
        while len(batch) < _BATCH:
            try:
                nxt = _q.get_nowait()
            except queue.Empty:
                break
            if nxt is None:
                _flush(batch)
                return
            batch.append(nxt)
        if len(batch) >= _BATCH:
            _flush(batch)
            batch = []
    _flush(batch)


def _flush(batch: list[dict[str, Any]]) -> None:
    if not batch:
        return
    try:
        insert_ticks(batch)
    except Exception:
        logger.exception("ClickHouse tick insert failed (%s rows)", len(batch))
