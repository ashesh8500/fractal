"""
Streamlit Strategy Workbench

A lean UI to:
- Chat with an LLM (LM Studio local or API) to draft/edit strategies constrained to BaseStrategy API
- Validate and load strategies
- Run backtests on selected symbols/time windows
- Visualize results with Plotly
- Persist chat and created strategies under portfolio_lib.services.strategy.custom

Usage from repo root (or portfolio_lib directory):
    streamlit run -m portfolio_lib.ui.strategy_workbench
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Type

import numpy as np
import pandas as pd
from pydantic import BaseModel

from portfolio_lib.models.strategy import BacktestConfig, StrategyConfig
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.strategy.base import BaseStrategy  # noqa: F401

try:
    # Prefer relative import when run as a module
    from .agent_tools import (
        ensure_custom_pkg,
        instantiate_strategy,
        list_available_strategies,
        read_strategy_source,
        validate_strategy,
        write_new_strategy,
    )
except Exception:
    # Fallback: add package root to sys.path and import absolute
    import os
    import sys

    sys.path.append(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    )
    import importlib

    _agt = importlib.import_module("portfolio_lib.ui.agent_tools")
    ensure_custom_pkg = getattr(_agt, "ensure_custom_pkg")
    list_available_strategies = getattr(_agt, "list_available_strategies")
    read_strategy_source = getattr(_agt, "read_strategy_source")
    validate_strategy = getattr(_agt, "validate_strategy")
    write_new_strategy = getattr(_agt, "write_new_strategy")
    instantiate_strategy = getattr(_agt, "instantiate_strategy")

# LangChain imports will be done inside main() when needed to avoid optional dep errors


# Status tracking constants
PRESET_STAGES = [
    "symbols_configured",
    "strategy_defined", 
    "backtest_run",
    "results_reviewed",
    "strategy_saved"
]


def _status_badge(status: str) -> str:
    """Generate status badge emoji and text."""
    s = (status or "").strip().lower()
    if s == "in_progress":
        return "🔵 in_progress"
    if s == "done":
        return "✅ done"
    if s == "error":
        return "❌ error"
    return "🟡 pending"


def _sanitize_args_for_display(args: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize tool arguments for display, hiding sensitive data."""
    safe = {}
    for k, v in (args or {}).items():
        lk = str(k).lower()
        if lk in {"api_key", "authorization", "access_token", "secret", "openai_api_key"}:
            safe[k] = "***"
        elif lk in {"api_base", "base_url"}:
            safe[k] = "***"
        elif lk in {"code"} and isinstance(v, str) and len(v) > 200:
            safe[k] = f"[code snippet {len(v)} chars]"
        else:
            safe[k] = v
    return safe


def _parse_tool_json(text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON tool call from text with multiple fallback strategies."""
    if not text:
        return None
        
    # Try direct JSON parse first
    try:
        obj = json.loads(text.strip())
        if isinstance(obj, dict) and obj.get("tool"):
            return obj
    except Exception:
        pass
    
    # Find JSON object in text using improved regex
    import re
    json_pattern = r'\{(?:[^{}]|{[^{}]*})*"tool"(?:[^{}]|{[^{}]*})*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            obj = json.loads(match)
            if isinstance(obj, dict) and obj.get("tool"):
                return obj
        except Exception:
            continue
    
    # Try extracting from end of text
    try:
        start = text.rfind("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict) and obj.get("tool"):
                return obj
    except Exception:
        pass
    
    return None


def _to_csv(records: List[Dict[str, Any]]) -> str:
    """Convert list of records to CSV string."""
    if not records:
        return ""
    import csv
    import io
    cols = sorted({k for r in records for k in r.keys()})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in records:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue()


def _store_dir() -> str:
    """Get or create storage directory for sessions."""
    import os
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".workbench_store"))
    os.makedirs(base, exist_ok=True)
    return base


def _save_session(st, session_name: Optional[str] = None) -> Dict[str, Any]:
    """Save current session state to file."""
    import os
    import time
    
    data = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "session_name": session_name or st.session_state.get("_session_name"),
        "chat": st.session_state.get("chat", []),
        "backtest_results": st.session_state.get("backtest_results", []),
        "status_map": st.session_state.get("status_map", {}),
        "symbols": st.session_state.get("_last_symbols"),
        "years": st.session_state.get("_last_years"),
        "initial_capital": st.session_state.get("_last_initial_capital"),
        "commission": st.session_state.get("_last_commission"),
        "slippage": st.session_state.get("_last_slippage"),
        "rebalance": st.session_state.get("_last_rebalance"),
        "benchmark": st.session_state.get("_last_benchmark"),
    }
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    name_part = f"-{session_name}" if session_name else ""
    filename = f"session{name_part}-{timestamp}.json"
    path = os.path.join(_store_dir(), filename)
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"ok": True, "path": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _list_saved_sessions(limit: int = 25) -> List[Dict[str, Any]]:
    """List previously saved sessions."""
    import os
    base = _store_dir()
    try:
        files = [os.path.join(base, f) for f in os.listdir(base) if f.startswith("session-") and f.endswith(".json")]
    except Exception:
        return []
    
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    out = []
    for p in files[:limit]:
        try:
            mtime = os.path.getmtime(p)
            out.append({
                "path": p,
                "mtime": mtime,
                "label": f"{os.path.basename(p)} — {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}"
            })
        except Exception:
            continue
    return out


def _load_session_from_file(path: str, st) -> Dict[str, Any]:
    """Load session from file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Restore session state
        st.session_state["_session_name"] = data.get("session_name")
        st.session_state["chat"] = data.get("chat", [])
        st.session_state["backtest_results"] = data.get("backtest_results", [])
        st.session_state["status_map"] = data.get("status_map", {})
        
        # Store loaded config for reference
        st.session_state["_loaded_config"] = {
            "symbols": data.get("symbols"),
            "years": data.get("years"),
            "initial_capital": data.get("initial_capital"),
            "commission": data.get("commission"),
            "slippage": data.get("slippage"),
            "rebalance": data.get("rebalance"),
            "benchmark": data.get("benchmark"),
        }
        
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Tool schemas for LangChain tool-calling
class RegisterStrategy(BaseModel):
    """Register a new strategy class to custom folder."""

    class_name: str
    code: str
    strategy_name: Optional[str] = None


class BacktestStrategy(BaseModel):
    """Backtest inline strategy code and return metrics."""

    code: str
    symbols: Optional[List[str]] = None
    years: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: Optional[float] = None
    commission: Optional[float] = None
    slippage: Optional[float] = None
    rebalance: Optional[str] = None
    benchmark: Optional[str] = None


def _plot_equity_curve(res) -> Any:
    import importlib

    go = importlib.import_module("plotly.graph_objects")
    # local import ensures optional dependency
    s = pd.Series(
        res.portfolio_values, index=pd.to_datetime(res.timestamps)
    ).sort_index()
    s = s / float(s.iloc[0]) if len(s) else s
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=s.index, y=s.values, mode="lines", name=res.strategy_name)
    )
    fig.update_layout(title="Growth of $1", xaxis_title="Date", yaxis_title="Growth")
    return fig


def _build_close_frame(price_history: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    series = []
    for sym, df in price_history.items():
        if df is None or df.empty:
            continue
        col = (
            "close"
            if "close" in df.columns
            else ("Close" if "Close" in df.columns else None)
        )
        if not col:
            continue
        # Normalize index to tz-naive to align with backtest timestamps
        idx = pd.to_datetime(df.index)
        try:
            idx = idx.tz_localize(None)  # if tz-aware
        except Exception:
            try:
                idx = idx.tz_convert(None)  # if tz-aware with tz set
            except Exception:
                pass
        s = pd.Series(df[col].values, index=idx, name=sym)
        series.append(s)
    if not series:
        return pd.DataFrame()
    closes = pd.concat(series, axis=1).sort_index().ffill()
    return closes


def _plot_growth_with_benchmark(
    res,
    price_history: Dict[str, pd.DataFrame],
    benchmark: str,
    initial_holdings: Dict[str, float],
) -> Optional[Any]:
    import importlib

    go = importlib.import_module("plotly.graph_objects")
    idx = pd.to_datetime(res.timestamps)
    if len(idx) == 0:
        return None
    closes = _build_close_frame(price_history)
    if closes.empty:
        return None
    closes = closes.reindex(idx).ffill()
    # Strategy equity
    strat = pd.Series(res.portfolio_values, index=idx)
    strat_g = strat / float(strat.iloc[0])
    # Benchmark equity
    if benchmark in closes.columns:
        bench = closes[benchmark].astype(float)
        bench_g = bench / float(bench.iloc[0]) if len(bench) else pd.Series(index=idx, dtype=float)
    else:
        bench_g = pd.Series(index=idx, dtype=float)
    # Baseline: buy-and-hold initial holdings
    inter_syms = [s for s in initial_holdings.keys() if s in closes.columns]
    if inter_syms:
        px = closes[inter_syms]
        shares = pd.Series({s: float(initial_holdings.get(s, 0.0)) for s in inter_syms})
        base_val = (px * shares).sum(axis=1)
        base_g = base_val / float(base_val.iloc[0])
    else:
        base_g = pd.Series(index=idx, dtype=float)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=idx, y=strat_g.values, mode="lines", name="Strategy"))
    if len(bench_g) and bench_g.notna().any():
        fig.add_trace(
            go.Scatter(x=idx, y=bench_g.values, mode="lines", name="Benchmark")
        )
    if len(base_g) and base_g.notna().any():
        fig.add_trace(
            go.Scatter(
                x=idx, y=base_g.values, mode="lines", name="Baseline (B&H initial)"
            )
        )
    fig.update_layout(
        title="Growth of $1 (Strategy vs Benchmark vs Baseline)",
        xaxis_title="Date",
        yaxis_title="Growth",
    )
    return fig


def _plot_allocations(res, price_history: Dict[str, pd.DataFrame]) -> Optional[Any]:
    import importlib
    import numpy as np

    go = importlib.import_module("plotly.graph_objects")
    idx = pd.to_datetime(res.timestamps)
    if not getattr(res, "holdings_history", None) or len(idx) == 0:
        return None
    closes = _build_close_frame(price_history).reindex(idx).ffill()
    if closes.empty:
        return None
    # Build weights over time with carry-forward when missing, and detect weight-like inputs
    weights = []
    last_w = pd.Series(0.0, index=closes.columns)
    for i, ts in enumerate(idx):
        hh = res.holdings_history[i] if i < len(res.holdings_history) else {}
        if not hh:
            weights.append(last_w)
            continue
        # If holdings sum to ~1, treat them as weights directly
        try:
            hh_series = pd.Series({k: float(hh.get(k, 0.0)) for k in closes.columns})
            ssum = float(hh_series.sum())
        except Exception:
            hh_series = pd.Series(0.0, index=closes.columns)
            ssum = 0.0
        if 0.98 <= ssum <= 1.02:
            w = hh_series.clip(lower=0.0)
            w = w / float(w.sum()) if float(w.sum()) > 0 else w
            last_w = w
            weights.append(w)
            continue
        # Otherwise compute weights from shares * price
        prices = closes.loc[ts].reindex(closes.columns).astype(float)
        pos_val = hh_series * prices
        tot = float(pos_val.sum())
        if not (tot > 0) or not np.isfinite(tot):
            weights.append(last_w)
            continue
        w = (pos_val / tot).clip(lower=0.0)
        last_w = w
        weights.append(w)
    wdf = pd.concat(weights, axis=1).T
    wdf.index = idx
    # Order symbols by mean weight and include all for fidelity
    means = wdf.mean().sort_values(ascending=False)
    ordered_cols = list(means.index)
    wdf_top = wdf[ordered_cols].fillna(0.0)
    # Ensure non-negative weights
    wdf_top = wdf_top.clip(lower=0.0)
    fig = go.Figure()
    for col in ordered_cols:
        fig.add_trace(
            go.Scatter(
                x=wdf_top.index,
                y=wdf_top[col].values,
                mode="lines",
                name=col,
                stackgroup="one",
                # weights are already normalized; no additional group normalization
            )
        )
    # Add vertical markers at rebalance timestamps if available
    rb_dates = []
    try:
        for d in getattr(res, "rebalance_details", []) or []:
            ts = d.get("timestamp")
            if ts is not None:
                try:
                    rb_dates.append(pd.to_datetime(ts))
                except Exception:
                    pass
    except Exception:
        pass
    for rb_date in rb_dates:
        fig.add_shape(
            dict(
                xref="x",
                yref="paper",
                x0=rb_date,
                x1=rb_date,
                y0=0,
                y1=1,
                line_color="#cccccc",
                line_width=1,
            )
        )
    fig.update_layout(
        title="Portfolio Allocation",
        xaxis_title="Date",
    yaxis_title="Weight",
    yaxis=dict(range=[0, 1]),
    )
    try:
        if (wdf_top.sum(axis=1) <= 1e-9).all():
            fig.add_annotation(text="No allocation changes recorded (all zero weights)", xref="paper", yref="paper", x=0.01, y=0.95, showarrow=False, font=dict(color="#aaa"))
    except Exception:
        pass
    return fig


def _plot_trades(res, price_history: Dict[str, pd.DataFrame]) -> Optional[Any]:
    import importlib

    go = importlib.import_module("plotly.graph_objects")
    trades = getattr(res, "executed_trades", [])
    if not trades:
        return None
    # pick the most-traded symbol that has price data
    df_tr = pd.DataFrame(trades)
    if "symbol" not in df_tr.columns:
        return None
    counts = df_tr["symbol"].value_counts() if not df_tr.empty else pd.Series(dtype=int)
    sym = None
    for s in counts.index.tolist():
        if s in price_history and not price_history[s].empty:
            sym = s
            break
    if sym is None:
        # fallback to any available symbol
        symbols = [s for s, d in price_history.items() if d is not None and not d.empty]
        if not symbols:
            return None
        sym = symbols[0]
    df = price_history[sym]
    s = df["close"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=f"{sym} close"))
    buys_x, buys_y, sells_x, sells_y = [], [], [], []
    for t in trades:
        ts = pd.to_datetime(t.get("timestamp"))
        px = t.get("price", np.nan)
        if t.get("action") == "buy":
            buys_x.append(ts)
            buys_y.append(px)
        elif t.get("action") == "sell":
            sells_x.append(ts)
            sells_y.append(px)
    if buys_x:
        fig.add_trace(
            go.Scatter(
                x=buys_x,
                y=buys_y,
                mode="markers",
                name="BUY",
                marker=dict(color="green", symbol="triangle-up"),
            )
        )
    if sells_x:
        fig.add_trace(
            go.Scatter(
                x=sells_x,
                y=sells_y,
                mode="markers",
                name="SELL",
                marker=dict(color="red", symbol="triangle-down"),
            )
        )
    fig.update_layout(title="Executed Trades", xaxis_title="Date", yaxis_title="Price")
    return fig


def _extract_code_and_class(raw: str) -> Optional[Dict[str, str]]:
    """Best-effort extract Python code and class name from raw text.
    - Prefer fenced code blocks ``` ... ```
    - Else, if text contains a class that subclasses BaseStrategy, return whole text
    """
    try:
        if not raw:
            return None
        import re
        code = None
        # fenced code
        m = re.search(r"```(?:python)?\n([\s\S]*?)```", raw, re.IGNORECASE)
        if m:
            code = m.group(1).strip()
        else:
            # If it looks like code, take the whole thing
            if "class" in raw and "BaseStrategy" in raw:
                code = raw
        if not code:
            return None
        m2 = re.search(r"class\s+([A-Za-z_]\w*)\s*\(\s*BaseStrategy\s*\)", code)
        cls = m2.group(1) if m2 else None
        if not cls:
            return None
        return {"code": code, "class_name": cls}
    except Exception:
        return None


def _fetch_models(api_base: str, api_key: str = "") -> List[str]:
    """Query OpenAI-compatible /models endpoint to list available model ids."""
    try:
        import requests  # type: ignore
    except Exception:
        return []
    url = api_base.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data") or []
        models = [it.get("id") for it in items if isinstance(it, dict) and it.get("id")]
        return [str(m) for m in models]
    except Exception:
        return []


def _parse_tool_call(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Parse a JSON tool call from model output (DEPRECATED).
    This function is disabled to prioritize native LangChain tool calling.
    Returns None to force reliance on native tool calls from the API.
    """
    return None


def _instantiate_strategy_from_source(
    code: str, class_name: Optional[str] = None
) -> BaseStrategy:
    """Exec code and return an instance of the single subclass of BaseStrategy.
    If class_name is provided, use it; else auto-detect unique subclass.
    """
    ns: Dict[str, Any] = {}
    exec(code, ns, ns)
    # find subclasses
    cls_candidates: List[Type[BaseStrategy]] = []
    for v in ns.values():
        try:
            if (
                isinstance(v, type)
                and issubclass(v, BaseStrategy)
                and v is not BaseStrategy
            ):
                cls_candidates.append(v)
        except Exception:
            continue

    def _construct(cls: Type[BaseStrategy]) -> BaseStrategy:
        try:
            return cls()  # type: ignore[call-arg]
        except TypeError:
            # Try providing a default name
            default_name = getattr(cls, "name", cls.__name__)
            try:
                return cls(default_name)  # type: ignore[call-arg]
            except Exception:
                return cls(name=default_name)  # type: ignore[call-arg]

    if class_name:
        for c in cls_candidates:
            if c.__name__ == class_name:
                return _construct(c)
        raise ValueError(f"Strategy class {class_name} not found in code")
    if len(cls_candidates) != 1:
        raise ValueError(
            f"Expected exactly one BaseStrategy subclass, found {len(cls_candidates)}"
        )
    return _construct(cls_candidates[0])


def _run_backtest_on_code(
    code: str,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    initial_capital: float,
    commission: float,
    slippage: float,
    rebalance: str,
    benchmark: str,
) -> Tuple[Any, Optional[Any], Dict[str, Any]]:
    """Instantiate a strategy from source and run a backtest; return charts and metrics.
    Returns: (growth_fig, alloc_or_trade_fig, metrics_dict)
    """
    strat = _instantiate_strategy_from_source(code)
    data = YFinanceDataService()
    svc = BacktestingService(data)
    bt_cfg = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage,
        benchmark=benchmark,
    )
    price_history = data.fetch_price_history(
        symbols, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    )
    valid = [s for s in symbols if s in price_history and not price_history[s].empty]
    if len(valid) < 2:
        raise ValueError("Not enough symbols with data to backtest")
    start_prices = {s: float(price_history[s]["close"].iloc[0]) for s in valid}
    cap_per = initial_capital / len(valid)
    initial_holdings = {s: cap_per / start_prices[s] for s in valid}
    cfg = StrategyConfig(name=strat.name, rebalance_frequency=rebalance)
    res = svc.run_backtest(strat, cfg, bt_cfg, initial_holdings)

    growth = _plot_growth_with_benchmark(
        res, price_history, benchmark, initial_holdings
    ) or _plot_equity_curve(res)
    alloc_or_trades = _plot_allocations(res, price_history) or _plot_trades(
        res, price_history
    )
    metrics = {
        "total_return": round(res.total_return, 6),
        "annualized_return": round(res.annualized_return, 6),
        "volatility": round(res.volatility, 6),
        "sharpe_ratio": round(res.sharpe_ratio, 6),
        "max_drawdown": round(res.max_drawdown, 6),
        "benchmark_return": round(res.benchmark_return, 6),
        "total_trades": int(res.total_trades),
    }
    return growth, alloc_or_trades, metrics


def main():
    global st
    import streamlit as st  # type: ignore

    st.set_page_config(page_title="Strategy Workbench", layout="wide")
    st.title("Strategy Workbench")

    ensure_custom_pkg()

    # Sidebar: Data and Backtest Settings
    with st.sidebar:
        st.header("Data & Backtest")
        symbols_str = st.text_input(
            "Symbols (comma-separated)",
            value="AAPL,MSFT,NVDA,AMZN,GOOGL,QQQ",
        )
        symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
        years = st.slider("Years", 1, 10, 3)
        initial_capital = st.number_input(
            "Initial Capital", value=100000.0, step=1000.0
        )
        commission = st.number_input(
            "Commission", value=0.0005, step=0.0001, format="%f"
        )
        slippage = st.number_input("Slippage", value=0.0002, step=0.0001, format="%f")
        rebalance = st.selectbox(
            "Rebalance", ["daily", "weekly", "monthly", "quarterly"], index=2
        )
        benchmark = st.text_input("Benchmark", value="QQQ")

        st.header("LLM Settings")
        provider = st.selectbox(
            "Provider", ["None", "OpenAI-compatible", "LiteLLM (LM Studio)"]
        )
        # Default to LM Studio OpenAI-compatible endpoint
        default_base = "http://localhost:1234/v1"
        api_base = st.text_input("API Base (OpenAI-compatible)", value=default_base)
        api_key = st.text_input("API Key", type="password")
        # Models: use session state to keep list between reruns
        st.session_state.setdefault("model_options", [])
        if st.button("Refresh Models"):
            st.session_state.model_options = _fetch_models(api_base, api_key)
        model_options: List[str] = st.session_state.get("model_options", [])
        model = st.selectbox(
            "Model", options=(model_options or ["gpt-4o-mini"]), accept_new_options=True
        )

    # Chat session state
    if "chat" not in st.session_state:
        st.session_state.chat = []  # list of dicts {role, content}
    
    # Initialize status tracking
    st.session_state.setdefault("status_map", {})
    st.session_state.setdefault("backtest_results", [])
    for stage in PRESET_STAGES:
        st.session_state["status_map"].setdefault(stage, {"status": "pending", "note": ""})
    
    # Store current sidebar values for session persistence
    st.session_state["_last_symbols"] = symbols
    st.session_state["_last_years"] = years
    st.session_state["_last_initial_capital"] = initial_capital
    st.session_state["_last_commission"] = commission
    st.session_state["_last_slippage"] = slippage
    st.session_state["_last_rebalance"] = rebalance
    st.session_state["_last_benchmark"] = benchmark
    
    # Update status based on configuration
    if symbols and len(symbols) >= 2:
        st.session_state["status_map"]["symbols_configured"] = {"status": "done", "note": f"{len(symbols)} symbols configured"}
    else:
        st.session_state["status_map"]["symbols_configured"] = {"status": "pending", "note": "Need at least 2 symbols"}

    # Status Panel
    with st.expander("🔄 Strategy Workbench Status", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            for stage in PRESET_STAGES:
                info = st.session_state["status_map"].get(stage, {"status": "pending", "note": ""})
                cols = st.columns([2, 1, 3])
                cols[0].markdown(f"**{stage.replace('_', ' ').title()}**")
                cols[1].markdown(_status_badge(info.get("status", "pending")))
                cols[2].markdown(info.get("note", ""))
        
        with col2:
            st.markdown("**Quick Actions**")
            session_name = st.text_input("Session Name", value=st.session_state.get("_session_name", ""), key="session_name_input")
            if st.button("💾 Save Session", help="Save current chat and results"):
                result = _save_session(st, session_name)
                if result["ok"]:
                    st.success("Session saved!")
                    st.session_state["_session_name"] = session_name
                else:
                    st.error(f"Save failed: {result['error']}")
            
            if st.button("🧹 Clear All", help="Clear chat and reset status"):
                st.session_state.pop("chat", None)
                st.session_state.pop("backtest_results", None)
                st.session_state["status_map"] = {stage: {"status": "pending", "note": ""} for stage in PRESET_STAGES}
                st.rerun()

    # Load Previous Session
    saved_sessions = _list_saved_sessions()
    if saved_sessions:
        with st.expander("📁 Load Previous Session", expanded=False):
            session_labels = [s["label"] for s in saved_sessions]
            selected_session = st.selectbox("Choose Session", ["— select —"] + session_labels, key="session_loader")
            if selected_session != "— select —":
                session_info = next((s for s in saved_sessions if s["label"] == selected_session), None)
                if session_info and st.button("🔄 Load Selected"):
                    result = _load_session_from_file(session_info["path"], st)
                    if result["ok"]:
                        st.success("Session loaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"Load failed: {result['error']}")

    # Results Dashboard
    if st.session_state.get("backtest_results"):
        with st.expander(f"📊 Backtest Results Dashboard ({len(st.session_state['backtest_results'])} runs)", expanded=False):
            results = st.session_state["backtest_results"]
            
            # Summary metrics
            if results:
                latest = results[-1]
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Latest Return", f"{latest['metrics'].get('total_return', 0):.2%}")
                col2.metric("Latest Sharpe", f"{latest['metrics'].get('sharpe_ratio', 0):.2f}")
                col3.metric("Latest Max DD", f"{latest['metrics'].get('max_drawdown', 0):.2%}")
                col4.metric("Total Runs", len(results))
                
                # Results table
                df_results = []
                for i, r in enumerate(results):
                    df_results.append({
                        "Run": i + 1,
                        "Timestamp": r["timestamp"][:19],  # Remove microseconds
                        "Symbols": ", ".join(r["symbols"][:3]) + ("..." if len(r["symbols"]) > 3 else ""),
                        "Return": f"{r['metrics'].get('total_return', 0):.2%}",
                        "Sharpe": f"{r['metrics'].get('sharpe_ratio', 0):.2f}",
                        "Max DD": f"{r['metrics'].get('max_drawdown', 0):.2%}",
                        "Trades": r['metrics'].get('total_trades', 0),
                    })
                
                st.dataframe(df_results, use_container_width=True, hide_index=True)
                
                # Export options
                col1, col2 = st.columns(2)
                with col1:
                    results_json = json.dumps(results, indent=2, default=str)
                    st.download_button(
                        "📥 Download Results (JSON)",
                        data=results_json,
                        file_name=f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                with col2:
                    results_csv = _to_csv(df_results)
                    st.download_button(
                        "📥 Download Summary (CSV)",
                        data=results_csv,
                        file_name=f"backtest_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

    # Strategy Management Tabs
    tab_chat, tab_backtest, tab_store = st.tabs(["Chat", "Backtest", "Store/Load"])

    with tab_chat:
        st.subheader("Constrained Strategy Builder")
        chat_mode = st.radio(
            "Chat Mode", ["Discuss", "Implement"], horizontal=True, key="chat_mode"
        )
        st.markdown(
            "Flow: 1) Acknowledge understanding of the requested strategy, 2) Preview a brief plan, 3) Emit a single JSON tool call to register the strategy."
        )

        # Show available strategies
        st.markdown("### Available Strategies")
        st.code("\n".join(list_available_strategies()) or "<none>")

        # Chat history with simple edit affordance
        for i, msg in enumerate(st.session_state.chat):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                with st.expander("Edit", expanded=False):
                    new_text = st.text_area(
                        f"Edit message {i}", value=msg["content"], key=f"edit_{i}"
                    )
                    cols = st.columns(2)
                    if cols[0].button("Save", key=f"save_{i}"):
                        st.session_state.chat[i]["content"] = new_text
                        st.rerun()
                    if cols[1].button("Delete", key=f"del_{i}"):
                        st.session_state.chat.pop(i)
                        st.rerun()

        user_input = st.chat_input("Describe the strategy to create or modify…")
        if user_input:
            # Show user message immediately in the UI
            with st.chat_message("user"):
                st.markdown(user_input)
            st.session_state.chat.append({"role": "user", "content": user_input})
            if provider == "None":
                st.info("Select an LLM Provider in the sidebar to chat with tools.")
                st.stop()

                    # Build a system prompt for native tool calling
            if chat_mode == "Discuss":
                sys_prompt = textwrap.dedent(
                    """
                    You are an expert quant Python assistant focused on strategy exploration.
                    
                    Available tools:
                    - backtest_strategy: Run backtests on inline strategy code
                    - register_strategy: Save strategy to file (only in Implement mode)
                    
                    Flow:
                    1) Discuss the strategy idea and approach
                    2) When ready to test, use the backtest_strategy tool with the strategy code
                    
                    Code Requirements for strategies:
                    - Define exactly one class that subclasses portfolio_lib.services.strategy.base.BaseStrategy
                    - Constructor: super().__init__("<short_name>")
                    - Implement execute(self, portfolio_weights, price_history, current_prices, config) -> StrategyResult
                    - Use portfolio_lib.models.strategy.Trade and TradeAction; Trade.quantity is a weight fraction delta (0..1)
                    - Keep it simple and fast. No I/O or network calls.
                    
                    Use tools when appropriate - the system will handle tool calling automatically.
                    """
                ).strip()
            else:
                sys_prompt = textwrap.dedent(
                    """
                    You are an expert quant Python assistant.
                    
                    Available tools:
                    - register_strategy: Save strategy files to the custom folder
                    - backtest_strategy: Run backtests on inline strategy code
                    
                    Workflow:
                    1) Understand the strategy request and discuss the approach
                    2) Use backtest_strategy to test the strategy
                    3) Use register_strategy to save the final strategy to file
                    
                    Code Requirements for strategies:
                    - Define exactly one class that subclasses portfolio_lib.services.strategy.base.BaseStrategy
                    - Constructor: super().__init__("<short_name>")
                    - Implement execute(self, portfolio_weights, price_history, current_prices, config) -> StrategyResult
                    - Use portfolio_lib.models.strategy.Trade and TradeAction; Trade.quantity is a weight fraction delta (0..1)
                    - No external I/O, no network calls.
                    - Compute must be simple and fast.
                    
                    Use tools when appropriate - the system will handle tool calling automatically.
                    """
                ).strip()            # Choose model and set up tools + streaming
            llm = None
            tools = []
            try:
                # Streaming callback to Streamlit
                from langchain_core.messages import (  # type: ignore
                    HumanMessage,
                    SystemMessage,
                )
                from langchain_core.tools import tool as lc_tool  # type: ignore

                # Define tools via decorators using our Pydantic schemas
                # Capture sidebar defaults for tool fallbacks
                defaults_local = {
                    "symbols": symbols,
                    "years": years,
                    "initial_capital": initial_capital,
                    "commission": commission,
                    "slippage": slippage,
                    "rebalance": rebalance,
                    "benchmark": benchmark,
                }

                @lc_tool(args_schema=RegisterStrategy)
                def register_strategy(
                    class_name: str, code: str, strategy_name: Optional[str] = None
                ) -> str:
                    """Save a strategy file to custom folder. Returns module path and class."""
                    if chat_mode != "Implement":
                        return "Switch to Implement mode to register strategies."
                    mod_path, cls = write_new_strategy(
                        class_name, strategy_name or class_name, source=code
                    )
                    return f"Registered {mod_path}:{cls}"

                @lc_tool(args_schema=BacktestStrategy)
                def backtest_strategy(
                    code: str,
                    symbols: Optional[List[str]] = None,
                    years: Optional[int] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    initial_capital: Optional[float] = None,
                    commission: Optional[float] = None,
                    slippage: Optional[float] = None,
                    rebalance: Optional[str] = None,
                    benchmark: Optional[str] = None,
                ) -> str:
                    """Run a backtest on inline code; returns a compact JSON metrics summary."""
                    # Resolve parameters with fallbacks to sidebar defaults
                    syms = symbols if symbols else defaults_local.get("symbols", [])
                    syms = [s for s in syms if isinstance(s, str) and s.strip()]
                    if not syms:
                        return json.dumps({"error": "No symbols"})
                    yrs_val = (
                        int(years)
                        if years is not None
                        else int(defaults_local.get("years", 3))
                    )
                    if start_date and end_date:
                        start_dt = pd.to_datetime(start_date).to_pydatetime()
                        end_dt = pd.to_datetime(end_date).to_pydatetime()
                    else:
                        end_dt = datetime.today()
                        start_dt = end_dt - timedelta(days=365 * max(1, yrs_val))
                    init_cap = (
                        float(initial_capital)
                        if initial_capital is not None
                        else float(defaults_local.get("initial_capital", 100000.0))
                    )
                    comm = (
                        float(commission)
                        if commission is not None
                        else float(defaults_local.get("commission", 0.0005))
                    )
                    slip = (
                        float(slippage)
                        if slippage is not None
                        else float(defaults_local.get("slippage", 0.0002))
                    )
                    reb = (
                        str(rebalance)
                        if rebalance is not None
                        else str(defaults_local.get("rebalance", "monthly"))
                    )
                    bench = (
                        str(benchmark)
                        if benchmark is not None
                        else str(defaults_local.get("benchmark", "QQQ"))
                    )
                    # Ensure benchmark price data is available for plotting
                    if bench and bench not in syms:
                        syms = syms + [bench]
                    fig1, fig2, metrics = _run_backtest_on_code(
                        code,
                        [str(s).upper() for s in syms],
                        start_dt,
                        end_dt,
                        init_cap,
                        comm,
                        slip,
                        reb,
                        bench,
                    )
                    # Render charts in UI while returning JSON summary for the tool output
                    st.plotly_chart(fig1, use_container_width=True)
                    if fig2 is not None:
                        st.plotly_chart(fig2, use_container_width=True)
                    st.json(metrics)
                    result_json = json.dumps(
                        {
                            "tool": "backtest_result",
                            "symbols": syms,
                            "start": pd.to_datetime(start_dt).isoformat(),
                            "end": pd.to_datetime(end_dt).isoformat(),
                            "metrics": metrics,
                        }
                    )
                    # Append concise summary to chat history, too
                    st.session_state.chat.append(
                        {"role": "assistant", "content": result_json}
                    )
                    return result_json

                tools = [register_strategy, backtest_strategy]
                # Provider selection
                if provider == "OpenAI-compatible":
                    from langchain_openai import ChatOpenAI  # type: ignore

                    llm = ChatOpenAI(
                        model=model,
                        openai_api_key=api_key or "",
                        openai_api_base=api_base or None,
                        streaming=True,
                    )
                elif provider == "LiteLLM (LM Studio)":
                    try:
                        from langchain_litellm import ChatLiteLLM  # type: ignore

                        llm = ChatLiteLLM(
                            model=model,
                            api_key=api_key or "sk-ignored",
                            base_url=api_base or "http://localhost:1234/v1",
                            streaming=True,
                        )
                    except Exception:
                        from langchain_community.chat_models import (
                            ChatLiteLLM,  # type: ignore
                        )

                        llm = ChatLiteLLM(
                            model=model,
                            api_key=api_key or "sk-ignored",
                            base_url=api_base or "http://localhost:1234/v1",
                            streaming=True,
                        )
            except Exception:
                llm = None

            if llm is None:
                st.warning(
                    "LangChain back-end not available. Install langchain and a provider."
                )
            else:
                with st.spinner("Asking model…"):
                    # Streaming container for assistant text
                    stream_box = st.empty()
                    
                    # Bind tools
                    try:
                        llm_with_tools = (
                            llm.bind_tools(tools) if hasattr(llm, "bind_tools") else llm
                        )
                    except Exception:
                        llm_with_tools = llm
                    # Build messages
                    msgs = [
                        SystemMessage(content=sys_prompt),
                        HumanMessage(content=user_input),
                    ]
                    # --- Stream response and collect native tool calls ---
                    chunks = []
                    text = ""
                    tc_buffer: Dict[str, Dict[str, Any]] = {}
                    tc_order: List[str] = []
                    last_tc_id_by_name: Dict[str, str] = {}
                    last_tc_id_global: Optional[str] = None
                    try:
                        for chunk in llm_with_tools.stream(msgs):
                            chunks.append(chunk)
                            # Extract and display text content
                            content = getattr(chunk, "content", None)
                            if content and isinstance(content, str):
                                text += content
                                stream_box.markdown(text)
                            # Structured tool_calls
                            for tc in (getattr(chunk, "tool_calls", []) or []):
                                name = getattr(tc, "name", None) or (tc.get("name") if isinstance(tc, dict) else None)
                                args = getattr(tc, "args", None) or (tc.get("args") if isinstance(tc, dict) else None)
                                tc_id = getattr(tc, "id", None) or (tc.get("id") if isinstance(tc, dict) else None)
                                if not tc_id:
                                    if name and name in last_tc_id_by_name:
                                        tc_id = last_tc_id_by_name[name]
                                    elif last_tc_id_global:
                                        tc_id = last_tc_id_global
                                    else:
                                        tc_id = f"tc_{len(tc_order)}"
                                if tc_id not in tc_buffer:
                                    tc_buffer[tc_id] = {"name": name, "args_str": "", "args": {}}
                                    tc_order.append(tc_id)
                                if name:
                                    tc_buffer[tc_id]["name"] = name
                                    last_tc_id_by_name[name] = tc_id
                                last_tc_id_global = tc_id
                                if isinstance(args, dict) and args:
                                    tc_buffer[tc_id]["args"] = args
                            # additional_kwargs fragments (tool_calls and legacy function_call)
                            addl = getattr(chunk, "additional_kwargs", {}) or {}
                            for entry in (addl.get("tool_calls", []) or []):
                                try:
                                    f = entry.get("function", {}) if isinstance(entry, dict) else {}
                                    name = f.get("name")
                                    part = f.get("arguments", "")
                                    tc_id = entry.get("id")
                                    if not tc_id:
                                        if name and name in last_tc_id_by_name:
                                            tc_id = last_tc_id_by_name[name]
                                        elif last_tc_id_global:
                                            tc_id = last_tc_id_global
                                        else:
                                            tc_id = f"tc_{len(tc_order)}"
                                    if tc_id not in tc_buffer:
                                        tc_buffer[tc_id] = {"name": name, "args_str": "", "args": {}}
                                        tc_order.append(tc_id)
                                    if name:
                                        tc_buffer[tc_id]["name"] = name
                                        last_tc_id_by_name[name] = tc_id
                                    last_tc_id_global = tc_id
                                    if isinstance(part, str):
                                        tc_buffer[tc_id]["args_str"] += part
                                except Exception:
                                    pass
                            # Legacy single function_call shape
                            try:
                                fcall = addl.get("function_call")
                                if isinstance(fcall, dict) and (fcall.get("name") or fcall.get("arguments")):
                                    name = fcall.get("name")
                                    part = fcall.get("arguments", "")
                                    tc_id = "function_call_0"
                                    if tc_id not in tc_buffer:
                                        tc_buffer[tc_id] = {"name": name, "args_str": "", "args": {}}
                                        tc_order.append(tc_id)
                                    if name:
                                        tc_buffer[tc_id]["name"] = name
                                        last_tc_id_by_name[name] = tc_id
                                    last_tc_id_global = tc_id
                                    if isinstance(part, str):
                                        tc_buffer[tc_id]["args_str"] += part
                            except Exception:
                                pass
                    except Exception as e:
                        stream_box.markdown(f"Streaming error: {e}")
                        
                    # Store assistant text in chat
                    if text:
                        st.session_state.chat.append({"role": "assistant", "content": text})

                    # Execute native tool calls (primary method)
                    def _coerce_args(a):
                        # Some providers send args as JSON string; parse best-effort
                        if a is None:
                            return {}
                        if isinstance(a, str):
                            try:
                                parsed = json.loads(a)
                                return parsed if isinstance(parsed, dict) else {}
                            except Exception:
                                return {}
                        return a if isinstance(a, dict) else {}

                    # Finalize calls by parsing accumulated args_str if needed
                    finalized_calls: List[Dict[str, Any]] = []
                    for tc_id in tc_order:
                        rec = tc_buffer.get(tc_id, {})
                        name = rec.get("name")
                        args = rec.get("args") or {}
                        if (not args) and rec.get("args_str"):
                            try:
                                parsed = json.loads(rec["args_str"])  # dict expected
                                if isinstance(parsed, dict):
                                    args = parsed
                            except Exception:
                                # try trimming common partials
                                try:
                                    s = rec["args_str"].strip()
                                    if s.endswith(","):
                                        s = s[:-1]
                                    parsed = json.loads(s)
                                    if isinstance(parsed, dict):
                                        args = parsed
                                except Exception:
                                    args = {}
                        if name:
                            finalized_calls.append({"name": name, "args": args})

                    for call in finalized_calls:
                        name = call.get("name")
                        args = _coerce_args(call.get("args"))
                        if not name:
                            continue
                        with st.expander(f"🔧 Tool: {name}", expanded=True):
                            st.caption("Arguments")
                            st.json(_sanitize_args_for_display(args or {}))
                            # Debug: show raw JSON string if args empty
                            try:
                                # find buffer entry
                                buf_id = next((tid for tid in tc_order if tc_buffer.get(tid, {}).get("name") == name), None)
                                if buf_id:
                                    raw = tc_buffer.get(buf_id, {}).get("args_str", "")
                                    if raw and not args:
                                        st.code(raw, language="json")
                            except Exception:
                                pass
                        try:
                            with st.spinner(f"Executing {name}..."):
                                if name == "register_strategy":
                                    # If args missing code/class_name, try extracting from last assistant text or user input
                                    a = dict(args or {})
                                    if not a.get("code") or not a.get("class_name"):
                                        fallback = _extract_code_and_class(text) or _extract_code_and_class(user_input)
                                        if fallback:
                                            a.setdefault("code", fallback.get("code"))
                                            a.setdefault("class_name", fallback.get("class_name"))
                                    result = register_strategy.invoke(a)
                                    st.success(str(result))
                                elif name == "backtest_strategy":
                                    result = backtest_strategy.invoke(args)
                                    st.info("✅ Backtest completed")
                                else:
                                    st.warning(f"⚠️ Unknown tool: {name}")
                        except Exception as e:
                            st.error(f"❌ Tool '{name}' failed: {e}")

                    # If there were no tool calls but the model produced JSON that looks like a tool
                    if (not tc_order) and text.strip().startswith("{"):
                        try:
                            blob = json.loads(text)
                            tname = blob.get("tool")
                            targs = _coerce_args(blob)
                            if tname == "register_strategy":
                                st.info("Executing inferred tool: register_strategy")
                                st.success(str(register_strategy.invoke({k: v for k, v in targs.items() if k in {"class_name","code","strategy_name"}})))
                            elif tname == "backtest_strategy":
                                st.info("Executing inferred tool: backtest_strategy")
                                keys = {"code","symbols","years","start_date","end_date","initial_capital","commission","slippage","rebalance","benchmark"}
                                st.info("✅ Backtest completed")
                                backtest_strategy.invoke({k: v for k, v in targs.items() if k in keys})
                        except Exception:
                            pass

        # Persist/restore chat history
        c1, c2 = st.columns(2)
        with c1:
            if st.session_state.chat:
                st.download_button(
                    "Download Chat JSON",
                    data=json.dumps(st.session_state.chat, indent=2),
                    file_name="strategy_workbench_chat.json",
                    mime="application/json",
                )
        with c2:
            uploaded = st.file_uploader(
                "Upload Chat JSON", type=["json"], accept_multiple_files=False
            )
            if uploaded is not None:
                try:
                    st.session_state.chat = json.loads(uploaded.read().decode("utf-8"))
                    st.success("Chat loaded")
                except Exception as e:
                    st.error(f"Failed to load chat: {e}")

    with tab_backtest:
        st.subheader("Validate / Load & Backtest")
        # Strategy picker
        names = list_available_strategies()
        colp1, colp2 = st.columns([3, 1])
        with colp1:
            module_cls = st.selectbox(
                "Strategy",
                options=names,
                index=(
                    names.index(
                        next(
                            (n for n in names if n.endswith(":MomentumStrategy")),
                            names[0],
                        )
                    )
                    if names
                    else 0
                ),
            )
        with colp2:
            if st.button("Refresh List"):
                names = list_available_strategies()
                st.experimental_rerun()
        if st.button("Validate"):
            v = validate_strategy(module_cls)
            if v.ok:
                st.success(f"OK: {v.module}:{v.class_name}")
                st.code(read_strategy_source(v.module or module_cls.split(":")[0]))
            else:
                st.error(v.message)

        if st.button("Run Backtest"):
            try:
                strat = instantiate_strategy(module_cls)
            except Exception as e:
                st.error(f"Instantiate failed: {e}")
            else:
                # Backtest
                data = YFinanceDataService()
                backtester = BacktestingService(data)
                end = datetime.today().date()
                start = end - timedelta(days=365 * years)
                bt_cfg = BacktestConfig(
                    start_date=datetime.combine(start, datetime.min.time()),
                    end_date=datetime.combine(end, datetime.min.time()),
                    initial_capital=initial_capital,
                    commission=commission,
                    slippage=slippage,
                    benchmark=benchmark,
                )
                # initial holdings: equal capital at first price available
                fetch_syms = symbols[:] if isinstance(symbols, list) else list(symbols)
                if benchmark and benchmark not in fetch_syms:
                    fetch_syms.append(benchmark)
                price_history = data.fetch_price_history(
                    fetch_syms,
                    bt_cfg.start_date.strftime("%Y-%m-%d"),
                    bt_cfg.end_date.strftime("%Y-%m-%d"),
                )
                valid_syms = [
                    s
                    for s in symbols
                    if s in price_history and not price_history[s].empty
                ]
                if benchmark and benchmark not in price_history:
                    st.warning(f"No price data for benchmark {benchmark}; benchmark line will be hidden.")
                if len(valid_syms) < 2:
                    st.error("Not enough symbols with data.")
                else:
                    start_prices = {
                        s: float(price_history[s]["close"].iloc[0]) for s in valid_syms
                    }
                    cap_per = initial_capital / len(valid_syms)
                    initial_holdings = {
                        s: cap_per / start_prices[s] for s in valid_syms
                    }

                    strat_cfg = StrategyConfig(
                        name=strat.name, rebalance_frequency=rebalance
                    )
                    res = backtester.run_backtest(
                        strat, strat_cfg, bt_cfg, initial_holdings
                    )

                    # Plots
                    c1, c2 = st.columns(2)
                    with c1:
                        st.plotly_chart(
                            _plot_growth_with_benchmark(
                                res, price_history, benchmark, initial_holdings
                            )
                            or _plot_equity_curve(res),
                            use_container_width=True,
                        )
                    with c2:
                        st.plotly_chart(
                            _plot_allocations(res, price_history)
                            or _plot_trades(res, price_history),
                            use_container_width=True,
                        )

                    st.markdown("### Metrics")
                    st.json(
                        {
                            "total_return": round(res.total_return, 4),
                            "annualized_return": round(res.annualized_return, 4),
                            "volatility": round(res.volatility, 4),
                            "sharpe_ratio": round(res.sharpe_ratio, 4),
                            "max_drawdown": round(res.max_drawdown, 4),
                            "benchmark_return": round(res.benchmark_return, 4),
                            "total_trades": int(res.total_trades),
                        }
                    )

                    # Trades table with scores
                    if getattr(res, "executed_trades", None):
                        st.markdown("### Executed Trades")
                        df_tr = pd.DataFrame(res.executed_trades)
                        # tidy columns
                        if "timestamp" in df_tr.columns:
                            df_tr["timestamp"] = pd.to_datetime(df_tr["timestamp"])
                        show_cols = [
                            c
                            for c in [
                                "timestamp",
                                "symbol",
                                "action",
                                "price",
                                "quantity_shares",
                                "weight_fraction",
                                "gross_value",
                                "commission",
                                "slippage",
                                "total_cost",
                                "net_cash_delta",
                                "score",
                                "reason",
                            ]
                            if c in df_tr.columns
                        ]
                        st.dataframe(
                            df_tr[show_cols].sort_values("timestamp"),
                            use_container_width=True,
                            hide_index=True,
                        )

                    # Rebalance diagnostics
                    if getattr(res, "rebalance_details", None):
                        with st.expander(
                            "Rebalance diagnostics (weights / target / scores)"
                        ):
                            try:
                                st.json(res.rebalance_details)
                            except Exception:
                                st.write(res.rebalance_details)

    with tab_store:
        st.subheader("Browse & Load Custom Strategies")
        names = list_available_strategies()
        st.write("Found:")
        for name in names:
            st.write("- ", name)

        st.markdown("### View / Edit Source")
        sel = st.selectbox("Select Strategy", options=[""] + names)
        code_area = None
        if sel:
            try:
                src = read_strategy_source(sel)
            except Exception as e:
                st.error(str(e))
                src = ""
            code_area = st.text_area("Source", value=src, height=400)
        class_copy = st.text_input(
            "Save as Class Name (in custom)", value="EditedStrategy"
        )
        if st.button("Save Copy to Custom"):
            if not code_area:
                st.error("No source to save.")
            else:
                try:
                    modp, cls = write_new_strategy(
                        class_copy, class_copy, source=code_area
                    )
                    st.success(f"Saved {modp}:{cls}")
                except Exception as e:
                    st.error(str(e))


if __name__ == "__main__":
    main()
