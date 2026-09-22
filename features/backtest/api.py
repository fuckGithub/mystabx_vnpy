"""CTA backtester REST API — model-centric run (load from MySQL → execute → persist)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.db import User
from core.deps import current_user, require_admin
from core.runtime import runtime
from core.serialize import trade_payload
from core.strategy_names import strategy_display_name

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

# Track last model-centric run so persist can attach results without racey params.
_last_model_run: dict[str, Any] = {}


def _bt():
    engine = runtime.backtester
    if engine is None:
        raise HTTPException(status_code=503, detail="回测引擎未加载（缺少 vnpy_ctabacktester）")
    return engine


class BacktestRunBody(BaseModel):
    class_name: str | None = None
    vt_symbol: str | None = None
    interval: str | None = None
    start: str
    end: str
    rate: float | None = None
    slippage: float | None = None
    size: float | None = None
    pricetick: float | None = None
    capital: float | None = None
    setting: dict = Field(default_factory=dict)
    strategy_name: str | None = None  # optional legacy instance path
    model_id: int | None = None
    model_version_id: int | None = None


def _parse_dt(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"无效日期: {value}") from exc


@router.get("/strategies")
def list_backtest_strategies(user: User = Depends(current_user)) -> list[dict]:
    _ = user
    engine = _bt()
    skip = {"EliteCtaTemplate", "CtaTemplate", "TargetPosTemplate"}
    rows = []
    for name in engine.get_strategy_class_names():
        if name in skip:
            continue
        try:
            params = engine.get_default_setting(name)
        except Exception:
            params = {}
        rows.append(
            {
                "class_name": name,
                "display_name": strategy_display_name(name),
                "parameters": params or {},
            }
        )
    return rows


@router.post("/run")
def run_backtest(body: BacktestRunBody, user: User = Depends(require_admin)) -> dict:
    """Run backtest. Prefer model_id: load 合约/参数/基础配置/源码 from MySQL then execute."""
    _ = user
    from core import model_store, strategy_loader

    engine = _bt()
    if getattr(engine, "thread", None) and engine.thread.is_alive():
        raise HTTPException(status_code=409, detail="回测正在运行")

    global _last_model_run
    _last_model_run = {}

    ctx: dict[str, Any] | None = None
    setting = dict(body.setting or {})
    class_name = (body.class_name or "").strip()
    vt_symbol = (body.vt_symbol or "").strip()
    interval = body.interval or "1m"
    rate = 0.0 if body.rate is None else float(body.rate)
    slippage = 0.0 if body.slippage is None else float(body.slippage)
    size = 10.0 if body.size is None else float(body.size)
    pricetick = 1.0 if body.pricetick is None else float(body.pricetick)
    capital = 1_000_000.0 if body.capital is None else float(body.capital)

    if body.model_id:
        try:
            ctx = strategy_loader.ensure_model_loaded_from_db(
                model_id=body.model_id,
                model_version_id=body.model_version_id,
                runtime_override=setting or None,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"从数据库加载模型失败: {exc}") from exc
        class_name = str(ctx["class_name"])
        # DB 合约 / 基础配置 take precedence unless request overrides explicitly
        if not vt_symbol:
            vt_symbol = str(ctx.get("vt_symbol") or "")
        cfg = dict(ctx.get("base_config") or {})
        if body.interval is None and cfg.get("interval"):
            interval = str(cfg["interval"])
        if body.rate is None and cfg.get("rate") is not None:
            rate = float(cfg["rate"])
        if body.slippage is None and cfg.get("slippage") is not None:
            slippage = float(cfg["slippage"])
        if body.size is None and cfg.get("size") is not None:
            size = float(cfg["size"])
        if body.pricetick is None and cfg.get("pricetick") is not None:
            pricetick = float(cfg["pricetick"])
        if body.capital is None and cfg.get("capital") is not None:
            capital = float(cfg["capital"])
        setting = dict(ctx.get("setting") or {})
    else:
        if not class_name:
            raise HTTPException(status_code=400, detail="class_name 或 model_id 必填")
        if not vt_symbol:
            raise HTTPException(status_code=400, detail="vt_symbol 不能为空")
        try:
            strategy_loader.ensure_class_loaded_from_db(
                class_name,
                strategy_name=(body.strategy_name or None),
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"从数据库加载策略失败: {exc}") from exc
        if body.strategy_name:
            setting = model_store.resolve_pinned_setting(
                strategy_name=body.strategy_name,
                runtime_override=setting,
            )

    if not vt_symbol:
        raise HTTPException(status_code=400, detail="合约 vt_symbol 为空，请先在模型中配置")
    if class_name not in getattr(engine, "classes", {}):
        raise HTTPException(status_code=400, detail=f"找不到策略类 {class_name}")

    # Ensure backtester reads MySQL market_bars (SimNow 录制归集)，并清掉 lru 缓存
    try:
        from features.backtest.market_bars_database import install_market_bars_database

        install_market_bars_database()
    except Exception:
        pass

    ok = engine.start_backtesting(
        class_name,
        vt_symbol,
        interval,
        _parse_dt(body.start),
        _parse_dt(body.end),
        rate,
        slippage,
        size,
        pricetick,
        capital,
        setting,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="启动回测失败（可能已有任务在跑）")

    run_params = {
        "class_name": class_name,
        "vt_symbol": vt_symbol,
        "interval": interval,
        "start": body.start,
        "end": body.end,
        "rate": rate,
        "slippage": slippage,
        "size": size,
        "pricetick": pricetick,
        "capital": capital,
        "setting": setting,
        "model_id": body.model_id,
        "model_version_id": (ctx or {}).get("model_version_id") or body.model_version_id,
    }

    run_meta = None
    if body.model_id:
        try:
            run_meta = model_store.record_backtest_run(
                strategy_name=str((ctx or {}).get("model_code") or ""),
                model_id=body.model_id,
                model_version_id=run_params["model_version_id"],
                run_params=run_params,
                statistics={},
                result_detail={},
                status="running",
                note="模型回测已启动",
            )
            _last_model_run = {
                "model_id": body.model_id,
                "model_version_id": run_params["model_version_id"],
                "run_id": run_meta.get("id") if run_meta else None,
                "run_params": run_params,
                "strategy_name": str((ctx or {}).get("model_code") or ""),
            }
        except Exception:
            run_meta = None
    elif body.strategy_name:
        binding = model_store.instance_binding(body.strategy_name)
        try:
            run_meta = model_store.record_backtest_run(
                strategy_name=body.strategy_name,
                instance_version_id=binding.get("current_version_id"),
                model_version_id=binding.get("model_version_id"),
                model_id=binding.get("model_id"),
                run_params=run_params,
                statistics={},
                status="running",
                note="回测已启动",
            )
        except Exception:
            run_meta = None

    return {
        "ok": True,
        "setting": setting,
        "class_name": class_name,
        "vt_symbol": vt_symbol,
        "run_context": {
            "model_id": body.model_id,
            "model_version_id": run_params.get("model_version_id"),
            "version_label": (ctx or {}).get("version_label"),
            "base_config": (ctx or {}).get("base_config"),
        }
        if ctx
        else None,
        "backtest_run": run_meta,
        "note": "回测历史从 MySQL market_bars 加载（SimNow 录制归集）；区间内无 bar 时结果为空。",
    }


def _collect_result_payload(engine) -> dict[str, Any]:
    stats = engine.get_result_statistics() or {}
    if not isinstance(stats, dict):
        try:
            stats = dict(stats)
        except Exception:
            stats = {"raw": str(stats)}

    trades: list[dict] = []
    try:
        trades = [trade_payload(t) for t in (engine.get_all_trades() or [])]
    except Exception:
        trades = []

    daily: list[dict] = []
    try:
        for row in engine.get_all_daily_results() or []:
            if hasattr(row, "__dict__"):
                daily.append(
                    {
                        k: getattr(row, k)
                        for k in ("date", "close_price", "net_pnl", "balance", "drawdown", "turnover")
                        if hasattr(row, k)
                    }
                )
            elif isinstance(row, dict):
                daily.append(row)
    except Exception:
        daily = []

    return {
        "statistics": stats,
        "trades": trades,
        "daily_results": daily,
        "logs": [],
    }


@router.post("/persist-result")
def persist_backtest_result(
    strategy_name: str | None = None,
    model_id: int | None = None,
    model_version_id: int | None = None,
    user: User = Depends(require_admin),
) -> dict:
    """Snapshot backtester results onto model detail (preferred) or instance version."""
    from core import model_store

    _ = user
    engine = _bt()
    payload = _collect_result_payload(engine)
    stats = payload.get("statistics") or {}

    mid = model_id
    mvid = model_version_id
    name = (strategy_name or "").strip()
    if mid is None and _last_model_run.get("model_id"):
        mid = int(_last_model_run["model_id"])
        mvid = mvid or _last_model_run.get("model_version_id")
        name = name or str(_last_model_run.get("strategy_name") or "")

    if mid is not None:
        row = model_store.record_backtest_run(
            strategy_name=name,
            model_id=int(mid),
            model_version_id=int(mvid) if mvid else None,
            run_params=_last_model_run.get("run_params") or {},
            statistics=stats if isinstance(stats, dict) else {},
            result_detail=payload,
            status="done" if stats else "empty",
            note="模型回测结果已写入详情",
        )
        return row

    if not name:
        raise HTTPException(status_code=400, detail="strategy_name 或 model_id 必填")
    binding = model_store.instance_binding(name)
    row = model_store.record_backtest_run(
        strategy_name=name,
        instance_version_id=binding.get("current_version_id"),
        model_version_id=binding.get("model_version_id"),
        model_id=binding.get("model_id"),
        run_params={},
        statistics=stats if isinstance(stats, dict) else {},
        result_detail=payload,
        status="done" if stats else "empty",
        note="回测结果快照",
    )
    return row


@router.get("/status")
def backtest_status(user: User = Depends(current_user)) -> dict:
    _ = user
    engine = _bt()
    running = bool(getattr(engine, "thread", None) and engine.thread.is_alive())
    stats = engine.get_result_statistics()
    return {
        "running": running,
        "has_result": stats is not None,
        "statistics": stats,
        "last_model_run": {
            "model_id": _last_model_run.get("model_id"),
            "model_version_id": _last_model_run.get("model_version_id"),
        }
        if _last_model_run
        else None,
    }


@router.get("/result")
def backtest_result(user: User = Depends(current_user)) -> dict:
    _ = user
    engine = _bt()
    stats = engine.get_result_statistics()
    df = engine.get_result_df()
    daily = []
    try:
        daily_results = engine.get_all_daily_results()
        for row in daily_results or []:
            if hasattr(row, "__dict__"):
                daily.append(
                    {
                        k: getattr(row, k)
                        for k in ("date", "close_price", "net_pnl", "balance", "drawdown")
                        if hasattr(row, k)
                    }
                )
            elif isinstance(row, dict):
                daily.append(row)
    except Exception:
        daily = []

    curve = []
    if df is not None and hasattr(df, "to_dict"):
        try:
            reset = df.reset_index()
            for rec in reset.to_dict(orient="records"):
                item = {}
                for k, v in rec.items():
                    key = str(k)
                    if hasattr(v, "isoformat"):
                        item[key] = v.isoformat()
                    elif isinstance(v, float) and v != v:  # NaN
                        item[key] = None
                    else:
                        item[key] = v
                curve.append(item)
        except Exception:
            curve = []

    return {
        "statistics": stats,
        "daily_results": daily,
        "df": curve,
        "empty": stats is None,
        "note": "无结果时多为所选区间内 MySQL market_bars 无数据（请先连 SimNow 录制行情）。" if stats is None else None,
    }


@router.get("/trades")
def backtest_trades(user: User = Depends(current_user)) -> list[dict]:
    _ = user
    engine = _bt()
    try:
        trades = engine.get_all_trades() or []
    except Exception:
        return []
    return [trade_payload(t) for t in trades]
