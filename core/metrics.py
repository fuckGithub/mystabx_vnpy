"""Performance metrics — docs/09 §8.6 P8.

Latency / queue-depth baseline for Tick-2-Trade and fan-out hotspots.
R-Cubed (E3) can live as a sibling helper in this module later; keep P8 free of strategy math.
"""

from __future__ import annotations

import threading
import time
from array import array
from typing import Any

# Default ring sizes — health snapshots sort a copy; keep modest for GIL cost.
_LATENCY_CAP = 4096
_TICK_ARRIVAL_TTL_S = 60.0


class LatencyWindow:
    """Fixed-capacity ring of latency samples (milliseconds)."""

    __slots__ = ("_buf", "_n", "_i", "_lock")

    def __init__(self, capacity: int = _LATENCY_CAP) -> None:
        self._buf = array("d", [0.0]) * max(16, capacity)
        self._n = 0
        self._i = 0
        self._lock = threading.Lock()

    def observe(self, ms: float) -> None:
        if ms < 0:
            ms = 0.0
        with self._lock:
            self._buf[self._i] = float(ms)
            self._i = (self._i + 1) % len(self._buf)
            if self._n < len(self._buf):
                self._n += 1

    def snapshot(self) -> dict[str, float | int | None]:
        with self._lock:
            n = self._n
            if n == 0:
                return {"count": 0, "p50_ms": None, "p99_ms": None, "max_ms": None}
            if n == len(self._buf):
                samples = list(self._buf)
            else:
                samples = [self._buf[i] for i in range(n)]
        samples.sort()
        return {
            "count": n,
            "p50_ms": round(_percentile(samples, 50), 3),
            "p99_ms": round(_percentile(samples, 99), 3),
            "max_ms": round(samples[-1], 3),
        }


def _percentile(sorted_samples: list[float], pct: float) -> float:
    if not sorted_samples:
        return 0.0
    if len(sorted_samples) == 1:
        return sorted_samples[0]
    k = (pct / 100.0) * (len(sorted_samples) - 1)
    lo = int(k)
    hi = min(lo + 1, len(sorted_samples) - 1)
    frac = k - lo
    return sorted_samples[lo] * (1.0 - frac) + sorted_samples[hi] * frac


class Metrics:
    """Process-wide counters. Observe-only; never raises into the hot path."""

    def __init__(self) -> None:
        self.tick_to_trade_latency = LatencyWindow()
        self.tick_handler_latency = LatencyWindow()
        self.ws_fanout_latency = LatencyWindow()
        self.strategy_latency = LatencyWindow()  # filled when CTA workers exist
        self._tick_arrivals: dict[str, float] = {}
        self._arrival_lock = threading.Lock()
        self._pending_ws = 0
        self._pending_lock = threading.Lock()
        self._ch_drops = 0
        self._tick_seen = 0
        self._orders_observed = 0
        # Optional providers registered by subsystems (avoid import cycles).
        self._ch_depth_fn: Any = None
        self._sse_depth_fn: Any = None
        self._event_depth_fn: Any = None
        self._ipc_depth_fn: Any = None

    def note_tick_arrival(self, symbol: str, exchange: str) -> None:
        key = f"{exchange}.{symbol}"
        now = time.perf_counter()
        with self._arrival_lock:
            self._tick_arrivals[key] = now
            self._tick_seen += 1
            if len(self._tick_arrivals) > 8_000:
                cutoff = now - _TICK_ARRIVAL_TTL_S
                self._tick_arrivals = {k: v for k, v in self._tick_arrivals.items() if v >= cutoff}

    def observe_tick_handler(self, elapsed_ms: float) -> None:
        self.tick_handler_latency.observe(elapsed_ms)

    def observe_ws_fanout(self, elapsed_ms: float) -> None:
        self.ws_fanout_latency.observe(elapsed_ms)

    def observe_strategy(self, elapsed_ms: float) -> None:
        self.strategy_latency.observe(elapsed_ms)

    def observe_tick_to_trade(self, symbol: str, exchange: str) -> None:
        """Record ms from last matching tick arrival → send_order return."""
        key = f"{exchange}.{symbol}"
        now = time.perf_counter()
        with self._arrival_lock:
            arrived = self._tick_arrivals.get(key)
        if arrived is None or (now - arrived) > _TICK_ARRIVAL_TTL_S:
            return
        self.tick_to_trade_latency.observe((now - arrived) * 1000.0)
        self._orders_observed += 1

    def ws_fanout_begin(self) -> None:
        with self._pending_lock:
            self._pending_ws += 1

    def ws_fanout_end(self) -> None:
        with self._pending_lock:
            if self._pending_ws > 0:
                self._pending_ws -= 1

    def note_ch_drop(self) -> None:
        self._ch_drops += 1

    def bind_ch_depth(self, fn) -> None:
        self._ch_depth_fn = fn

    def bind_sse_depth(self, fn) -> None:
        self._sse_depth_fn = fn

    def bind_event_depth(self, fn) -> None:
        self._event_depth_fn = fn

    def bind_ipc_depth(self, fn) -> None:
        self._ipc_depth_fn = fn

    def ws_queue_depth(self) -> int:
        with self._pending_lock:
            return self._pending_ws

    def snapshot(self, *, thresholds: dict[str, float] | None = None) -> dict[str, Any]:
        thr = thresholds or {}
        ch = self._safe_call(self._ch_depth_fn) or {"depth": None, "max": None, "drops": self._ch_drops}
        if isinstance(ch, dict) and "drops" not in ch:
            ch = {**ch, "drops": self._ch_drops}
        sse_depth = self._safe_call(self._sse_depth_fn)
        event_depth = self._safe_call(self._event_depth_fn)
        ipc_depth = self._safe_call(self._ipc_depth_fn)

        out: dict[str, Any] = {
            "tick_to_trade_latency": self.tick_to_trade_latency.snapshot(),
            "tick_handler_latency": self.tick_handler_latency.snapshot(),
            "ws_fanout_latency": self.ws_fanout_latency.snapshot(),
            "strategy_latency": self.strategy_latency.snapshot(),
            "ws_queue_depth": self.ws_queue_depth(),
            "sse_queue_depth": sse_depth,
            "ch_queue_depth": ch,
            "event_queue_depth": event_depth,
            "ipc_queue_depth": ipc_depth,  # None until E1 WorkerManager
            "ticks_seen": self._tick_seen,
            "orders_with_t2t": self._orders_observed,
            "alerts": [],
        }
        out["alerts"] = _build_alerts(out, thr)
        return out

    @staticmethod
    def _safe_call(fn) -> Any:
        if fn is None:
            return None
        try:
            return fn()
        except Exception:
            return None


def _build_alerts(snap: dict[str, Any], thr: dict[str, float]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    t2t = snap.get("tick_to_trade_latency") or {}
    p99 = t2t.get("p99_ms")
    limit = thr.get("tick_to_trade_p99_ms", 50.0)
    if p99 is not None and p99 > limit:
        alerts.append(
            {
                "metric": "tick_to_trade_latency.p99",
                "value_ms": p99,
                "threshold_ms": limit,
                "level": "warn",
            }
        )
    ch = snap.get("ch_queue_depth") or {}
    depth = ch.get("depth") if isinstance(ch, dict) else None
    ch_warn = thr.get("ch_queue_warn", 40_000.0)
    if depth is not None and depth >= ch_warn:
        alerts.append(
            {
                "metric": "ch_queue_depth",
                "value": depth,
                "threshold": ch_warn,
                "level": "warn",
            }
        )
    ws_pending = snap.get("ws_queue_depth")
    ws_warn = thr.get("ws_pending_warn", 2_000.0)
    if isinstance(ws_pending, int) and ws_pending >= ws_warn:
        alerts.append(
            {
                "metric": "ws_queue_depth",
                "value": ws_pending,
                "threshold": ws_warn,
                "level": "warn",
            }
        )
    return alerts


metrics = Metrics()

# Tiny helpers used by hot paths without importing time at each call site.
perf_counter = time.perf_counter
