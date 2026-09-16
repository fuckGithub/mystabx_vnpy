"""CTA backtester REST API — minimal start / result (docs/09 阶段 B)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.db import User
from core.deps import current_user, require_admin
from core.runtime import runtime
from core.serialize import trade_payload

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


def _bt():
    engine = runtime.backtester
    if engine is None:
        raise HTTPException(status_code=503, detail="回测引擎未加载（缺少 vnpy_ctabacktester）")
    return engine


class BacktestRunBody(BaseModel):
    class_name: str
    vt_symbol: str
    interval: str = "1m"
    start: str
    end: str
    rate: float = 0.0
    slippage: float = 0.0
    size: float = 10
    pricetick: float = 1.0
    capital: float = 1_000_000
    setting: dict = Field(default_factory=dict)


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
        rows.append({"class_name": name, "parameters": params or {}})
    return rows


@router.post("/run")
def run_backtest(body: BacktestRunBody, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _bt()
    if getattr(engine, "thread", None) and engine.thread.is_alive():
        raise HTTPException(status_code=409, detail="回测正在运行")
    ok = engine.start_backtesting(
        body.class_name,
        body.vt_symbol,
        body.interval,
        _parse_dt(body.start),
        _parse_dt(body.end),
        body.rate,
        body.slippage,
        body.size,
        body.pricetick,
        body.capital,
        body.setting,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="启动回测失败（可能已有任务在跑）")
    return {
        "ok": True,
        "note": "若本地无历史 bar / 未配置 RQData，回测结果为空属正常；请先完成数据入库（P1-2）。",
    }


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
                daily.append({k: getattr(row, k) for k in ("date", "close_price", "net_pnl", "balance", "drawdown") if hasattr(row, k)})
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
        "note": "无结果时多为历史数据为空（未配置 RQData / 本地库无 bar）。" if stats is None else None,
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
