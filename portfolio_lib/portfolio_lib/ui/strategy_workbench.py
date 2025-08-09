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

import textwrap
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple, Type
from pydantic import BaseModel

import numpy as np
import pandas as pd

from portfolio_lib.models.strategy import BacktestConfig, StrategyConfig
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.strategy.base import BaseStrategy  # noqa: F401
try:
    # Prefer relative import when run as a module
    from .agent_tools import (
        ensure_custom_pkg,
        list_available_strategies,
        read_strategy_source,
        validate_strategy,
        write_new_strategy,
        instantiate_strategy,
    )
except Exception:
    # Fallback: add package root to sys.path and import absolute
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    import importlib
    _agt = importlib.import_module("portfolio_lib.ui.agent_tools")
    ensure_custom_pkg = getattr(_agt, "ensure_custom_pkg")
    list_available_strategies = getattr(_agt, "list_available_strategies")
    read_strategy_source = getattr(_agt, "read_strategy_source")
    validate_strategy = getattr(_agt, "validate_strategy")
    write_new_strategy = getattr(_agt, "write_new_strategy")
    instantiate_strategy = getattr(_agt, "instantiate_strategy")

# LangChain imports will be done inside main() when needed to avoid optional dep errors


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
    go = importlib.import_module('plotly.graph_objects')
    # local import ensures optional dependency
    s = pd.Series(res.portfolio_values, index=pd.to_datetime(res.timestamps)).sort_index()
    s = s / float(s.iloc[0]) if len(s) else s
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=res.strategy_name))
    fig.update_layout(title="Growth of $1", xaxis_title="Date", yaxis_title="Growth")
    return fig


def _build_close_frame(price_history: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    series = []
    for sym, df in price_history.items():
        if df is None or df.empty:
            continue
        col = "close" if "close" in df.columns else ("Close" if "Close" in df.columns else None)
        if not col:
            continue
        s = pd.Series(df[col].values, index=pd.to_datetime(df.index), name=sym)
        series.append(s)
    if not series:
        return pd.DataFrame()
    closes = pd.concat(series, axis=1).sort_index().ffill()
    return closes


def _plot_growth_with_benchmark(res, price_history: Dict[str, pd.DataFrame], benchmark: str, initial_holdings: Dict[str, float]) -> Optional[Any]:
    import importlib
    go = importlib.import_module('plotly.graph_objects')
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
        bench = closes[benchmark]
        bench_g = bench / float(bench.iloc[0])
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
        fig.add_trace(go.Scatter(x=idx, y=bench_g.values, mode="lines", name="Benchmark"))
    if len(base_g) and base_g.notna().any():
        fig.add_trace(go.Scatter(x=idx, y=base_g.values, mode="lines", name="Baseline (B&H initial)"))
    fig.update_layout(title="Growth of $1 (Strategy vs Benchmark vs Baseline)", xaxis_title="Date", yaxis_title="Growth")
    return fig


def _plot_allocations(res, price_history: Dict[str, pd.DataFrame]) -> Optional[Any]:
    import importlib
    go = importlib.import_module('plotly.graph_objects')
    idx = pd.to_datetime(res.timestamps)
    if not getattr(res, "holdings_history", None) or len(idx) == 0:
        return None
    closes = _build_close_frame(price_history).reindex(idx).ffill()
    if closes.empty:
        return None
    # Build weights over time
    weights = []
    for i, ts in enumerate(idx):
        hh = res.holdings_history[i] if i < len(res.holdings_history) else {}
        if not hh:
            weights.append(pd.Series(0.0, index=closes.columns))
            continue
        prices = closes.loc[ts].reindex(closes.columns).astype(float)
        pos_val = pd.Series({k: float(hh.get(k, 0.0)) for k in closes.columns}) * prices
        tot = float(pos_val.sum())
        w = (pos_val / tot) if tot > 0 else pos_val
        weights.append(w)
    wdf = pd.concat(weights, axis=1).T
    wdf.index = idx
    # Order symbols by mean weight and include all for fidelity
    means = wdf.mean().sort_values(ascending=False)
    ordered_cols = list(means.index)
    wdf_top = wdf[ordered_cols].fillna(0.0)
    # Ensure non-negative and bounded weights
    wdf_top = wdf_top.clip(lower=0.0, upper=1.0)
    # Compute remainder as Others (should be near zero if all symbols included)
    others = (1.0 - wdf_top.sum(axis=1)).clip(lower=0.0)
    fig = go.Figure()
    for col in ordered_cols:
        fig.add_trace(
            go.Scatter(
                x=wdf_top.index,
                y=wdf_top[col].values,
                mode="lines",
                name=col,
                stackgroup="one",
                groupnorm="fraction",
            )
        )
    if others.notna().any() and (others > 1e-6).any():
        fig.add_trace(
            go.Scatter(
                x=wdf_top.index,
                y=others.values,
                mode="lines",
                name="Others",
                stackgroup="one",
                groupnorm="fraction",
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
    fig.update_layout(title="Portfolio Allocation", xaxis_title="Date", yaxis_title="Weight", yaxis=dict(range=[0, 1]))
    return fig


def _plot_trades(res, price_history: Dict[str, pd.DataFrame]) -> Optional[Any]:
    import importlib
    go = importlib.import_module('plotly.graph_objects')
    trades = getattr(res, "executed_trades", [])
    if not trades:
        return None
    # pick the most-traded symbol that has price data
    df_tr = pd.DataFrame(trades)
    if "symbol" not in df_tr.columns:
        return None
    counts = (
        df_tr["symbol"].value_counts() if not df_tr.empty else pd.Series(dtype=int)
    )
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
        fig.add_trace(go.Scatter(x=buys_x, y=buys_y, mode="markers", name="BUY", marker=dict(color="green", symbol="triangle-up")))
    if sells_x:
        fig.add_trace(go.Scatter(x=sells_x, y=sells_y, mode="markers", name="SELL", marker=dict(color="red", symbol="triangle-down")))
    fig.update_layout(title="Executed Trades", xaxis_title="Date", yaxis_title="Price")
    return fig


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
    """Parse a JSON tool call from model output.
    Supports:
      - register_strategy: {tool, class_name, code, strategy_name?}
      - backtest_strategy: {tool, code, symbols, years? or start_date/end_date, initial_capital, commission, slippage, rebalance, benchmark}
    Returns (tool_name, payload_dict) or None.
    """
    def _as_obj(t: str) -> Optional[Dict[str, Any]]:
        try:
            o = json.loads(t)
            return o if isinstance(o, dict) else None
        except Exception:
            return None

    obj = _as_obj(text)
    if not obj:
        # fallback: find first JSON object
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = _as_obj(text[start : end + 1])
        except Exception:
            obj = None
    if not obj:
        return None
    tool = obj.get("tool")
    if tool in {"register_strategy", "backtest_strategy"}:
        return tool, obj
    return None


def _instantiate_strategy_from_source(code: str, class_name: Optional[str] = None) -> BaseStrategy:
    """Exec code and return an instance of the single subclass of BaseStrategy.
    If class_name is provided, use it; else auto-detect unique subclass.
    """
    ns: Dict[str, Any] = {}
    exec(code, ns, ns)
    # find subclasses
    cls_candidates: List[Type[BaseStrategy]] = []
    for v in ns.values():
        try:
            if isinstance(v, type) and issubclass(v, BaseStrategy) and v is not BaseStrategy:
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
        raise ValueError(f"Expected exactly one BaseStrategy subclass, found {len(cls_candidates)}")
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
    price_history = data.fetch_price_history(symbols, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    valid = [s for s in symbols if s in price_history and not price_history[s].empty]
    if len(valid) < 2:
        raise ValueError("Not enough symbols with data to backtest")
    start_prices = {s: float(price_history[s]["close"].iloc[0]) for s in valid}
    cap_per = initial_capital / len(valid)
    initial_holdings = {s: cap_per / start_prices[s] for s in valid}
    cfg = StrategyConfig(name=strat.name, rebalance_frequency=rebalance)
    res = svc.run_backtest(strat, cfg, bt_cfg, initial_holdings)

    growth = _plot_growth_with_benchmark(res, price_history, benchmark, initial_holdings) or _plot_equity_curve(res)
    alloc_or_trades = _plot_allocations(res, price_history) or _plot_trades(res, price_history)
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
        initial_capital = st.number_input("Initial Capital", value=100000.0, step=1000.0)
        commission = st.number_input("Commission", value=0.0005, step=0.0001, format="%f")
        slippage = st.number_input("Slippage", value=0.0002, step=0.0001, format="%f")
        rebalance = st.selectbox("Rebalance", ["daily", "weekly", "monthly", "quarterly"], index=2)
        benchmark = st.text_input("Benchmark", value="QQQ")

        st.header("LLM Settings")
        provider = st.selectbox("Provider", ["None", "OpenAI-compatible", "LiteLLM (LM Studio)"])
        # Default to LM Studio OpenAI-compatible endpoint
        default_base = "http://localhost:1234/v1"
        api_base = st.text_input("API Base (OpenAI-compatible)", value=default_base)
        api_key = st.text_input("API Key", type="password")
        # Models: use session state to keep list between reruns
        st.session_state.setdefault("model_options", [])
        if st.button("Refresh Models"):
            st.session_state.model_options = _fetch_models(api_base, api_key)
        model_options: List[str] = st.session_state.get("model_options", [])
        model = st.selectbox("Model", options=(model_options or ["gpt-4o-mini"]))

    # Chat session state
    if "chat" not in st.session_state:
        st.session_state.chat = []  # list of dicts {role, content}

    # Strategy Management Tabs
    tab_chat, tab_backtest, tab_store = st.tabs(["Chat", "Backtest", "Store/Load"])

    with tab_chat:
        st.subheader("Constrained Strategy Builder")
        chat_mode = st.radio("Chat Mode", ["Discuss", "Implement"], horizontal=True, key="chat_mode")
        st.markdown(
            "Flow: 1) Acknowledge understanding of the requested strategy, 2) Preview a brief plan, 3) Emit a single JSON tool call to register the strategy."
        )

        # Show available strategies
        st.markdown("### Available Strategies")
        st.code("\n".join(list_available_strategies()) or "<none>")

        # Chat history
        for msg in st.session_state.chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Describe the strategy to create or modify…")
        if user_input and provider != "None":
            st.session_state.chat.append({"role": "user", "content": user_input})

            # Build a system prompt to constrain output
            if chat_mode == "Discuss":
                sys_prompt = textwrap.dedent(
                    """
                    You are an expert quant Python assistant focused on strategy exploration.
                    Flow:
                    1) Briefly clarify and discuss the strategy idea.
                    2) When ready to test, OUTPUT A SINGLE JSON OBJECT (last line only) to call a backtest tool.

                    Backtest Tool JSON (emit exactly once when ready):
                    {
                        "tool": "backtest_strategy",
                        "code": "<FULL PYTHON SOURCE CODE>",
                        "symbols": ["AAPL", "MSFT", "NVDA"],
                        "years": 3,
                        "initial_capital": 100000,
                        "commission": 0.0005,
                        "slippage": 0.0002,
                        "rebalance": "monthly",
                        "benchmark": "QQQ"
                    }

                    Code Requirements:
                    - Define exactly one class that subclasses portfolio_lib.services.strategy.base.BaseStrategy.
                    - Constructor: super().__init__("<short_name>")
                    - Implement execute(self, portfolio_weights, price_history, current_prices, config) -> StrategyResult.
                    - Use portfolio_lib.models.strategy.Trade and TradeAction; Trade.quantity is a weight fraction delta (0..1).
                    - Keep it simple and fast. No I/O or network.
                    """
                ).strip()
            else:
                sys_prompt = textwrap.dedent(
                    """
                    You are an expert quant Python assistant.
                    Workflow for each user request:
                    1) Respond briefly confirming your understanding of the strategy request.
                    2) Preview the approach at a high level (signals, weighting, constraints).
                    3) Then output a SINGLE JSON object to call a tool to register the strategy file. The JSON must be the last line only.

                    Tool spec (emit exactly this JSON shape when ready to register):
                    {
                        "tool": "register_strategy",
                        "class_name": "<ClassName>",
                        "strategy_name": "<short_name>",
                        "code": "<FULL PYTHON SOURCE CODE>"
                    }

                    Code Requirements:
                    - Define exactly one class that subclasses portfolio_lib.services.strategy.base.BaseStrategy.
                    - Constructor: super().__init__("<short_name>")
                    - Implement execute(self, portfolio_weights, price_history, current_prices, config) -> StrategyResult.
                    - Use portfolio_lib.models.strategy.Trade and TradeAction; Trade.quantity is a weight fraction delta (0..1).
                    - No external I/O, no network calls.
                    - Compute must be simple and fast.
                    """
                ).strip()

            # Choose model and set up tools + streaming
            llm = None
            tools = []
            try:
                from langchain_core.tools import tool as lc_tool  # type: ignore
                from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore
                # Streaming callback to Streamlit
                class StreamHandler:
                    def __init__(self, container):
                        self.container = container
                        self.text = ""
                    def on_llm_new_token(self, token: str, **kwargs):
                        self.text += token
                        self.container.markdown(self.text)
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
                def register_strategy(class_name: str, code: str, strategy_name: Optional[str] = None) -> str:
                    """Save a strategy file to custom folder. Returns module path and class."""
                    if chat_mode != "Implement":
                        return "Switch to Implement mode to register strategies."
                    mod_path, cls = write_new_strategy(class_name, strategy_name or class_name, source=code)
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
                    if not syms:
                        return json.dumps({"error": "No symbols"})
                    yrs_val = int(years) if years is not None else int(defaults_local.get("years", 3))
                    if start_date and end_date:
                        start_dt = pd.to_datetime(start_date).to_pydatetime()
                        end_dt = pd.to_datetime(end_date).to_pydatetime()
                    else:
                        end_dt = datetime.today()
                        start_dt = end_dt - timedelta(days=365 * max(1, yrs_val))
                    init_cap = float(initial_capital) if initial_capital is not None else float(defaults_local.get("initial_capital", 100000.0))
                    comm = float(commission) if commission is not None else float(defaults_local.get("commission", 0.0005))
                    slip = float(slippage) if slippage is not None else float(defaults_local.get("slippage", 0.0002))
                    reb = str(rebalance) if rebalance is not None else str(defaults_local.get("rebalance", "monthly"))
                    bench = str(benchmark) if benchmark is not None else str(defaults_local.get("benchmark", "QQQ"))
                    fig1, fig2, metrics = _run_backtest_on_code(code, [str(s).upper() for s in syms], start_dt, end_dt, init_cap, comm, slip, reb, bench)
                    # Render charts in UI while returning JSON summary for the tool output
                    st.plotly_chart(fig1, use_container_width=True)
                    if fig2 is not None:
                        st.plotly_chart(fig2, use_container_width=True)
                    st.json(metrics)
                    result_json = json.dumps({
                        "tool": "backtest_result",
                        "symbols": syms,
                        "start": pd.to_datetime(start_dt).isoformat(),
                        "end": pd.to_datetime(end_dt).isoformat(),
                        "metrics": metrics,
                    })
                    # Append concise summary to chat history, too
                    st.session_state.chat.append({"role": "assistant", "content": result_json})
                    return result_json

                tools = [register_strategy, backtest_strategy]
                # Provider selection
                if provider == "OpenAI-compatible":
                    from langchain_openai import ChatOpenAI  # type: ignore
                    llm = ChatOpenAI(model=model, openai_api_key=api_key or "", openai_api_base=api_base or None, streaming=True)
                elif provider == "LiteLLM (LM Studio)":
                    try:
                        from langchain_litellm import ChatLiteLLM  # type: ignore
                        llm = ChatLiteLLM(model=model, api_key=api_key or "sk-ignored", base_url=api_base or "http://localhost:1234/v1", streaming=True)
                    except Exception:
                        from langchain_community.chat_models import ChatLiteLLM  # type: ignore
                        llm = ChatLiteLLM(model=model, api_key=api_key or "sk-ignored", base_url=api_base or "http://localhost:1234/v1", streaming=True)
            except Exception:
                llm = None

            if llm is None:
                st.warning("LangChain back-end not available. Install langchain and a provider.")
            else:
                with st.spinner("Asking model…"):
                    # Streaming container for assistant text
                    stream_box = st.empty()
                    handler = None
                    try:
                        # Some providers need callbacks via callbacks parameter
                        handler = StreamHandler(stream_box)
                    except Exception:
                        handler = None
                    # Bind tools
                    try:
                        llm_with_tools = llm.bind_tools(tools) if hasattr(llm, "bind_tools") else llm
                    except Exception:
                        llm_with_tools = llm
                    # Build messages
                    msgs = [SystemMessage(content=sys_prompt), HumanMessage(content=user_input)]
                    try:
                        resp = llm_with_tools.invoke(msgs, config={"callbacks": [handler]} if handler else None)  # type: ignore
                    except Exception:
                        # Fall back to non-streaming
                        resp = llm_with_tools.invoke(msgs)  # type: ignore
                    # Display assistant text content (if any)
                    try:
                        content_text = getattr(resp, "content", None)
                        if content_text:
                            # Ensure full text is shown (in case streaming missed final delta)
                            stream_box.markdown(str(content_text))
                            st.session_state.chat.append({"role": "assistant", "content": str(content_text)})
                    except Exception:
                        pass
                    # Execute any tool calls
                    try:
                        tool_calls = getattr(resp, "tool_calls", []) or []
                    except Exception:
                        tool_calls = []
                # Process tool calls after showing assistant text
                for tc in tool_calls:
                    name = getattr(tc, "name", None) or tc.get("name") if isinstance(tc, dict) else None
                    args = getattr(tc, "args", None) or tc.get("args") if isinstance(tc, dict) else None
                    if not name:
                        continue
                    try:
                        if name == "register_strategy":
                            result = tools[0].invoke(args)
                            st.success(str(result))
                        elif name == "backtest_strategy":
                            result = tools[1].invoke(args)
                            # backtest tool already renders; still show brief status
                            st.info("Backtest complete")
                        else:
                            st.warning(f"Unknown tool: {name}")
                    except Exception as e:
                        st.error(f"Tool '{name}' failed: {e}")

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
            uploaded = st.file_uploader("Upload Chat JSON", type=["json"], accept_multiple_files=False)
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
            module_cls = st.selectbox("Strategy", options=names, index=(names.index(next((n for n in names if n.endswith(":MomentumStrategy")), names[0])) if names else 0))
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
                price_history = data.fetch_price_history(symbols, bt_cfg.start_date.strftime("%Y-%m-%d"), bt_cfg.end_date.strftime("%Y-%m-%d"))
                valid_syms = [s for s in symbols if s in price_history and not price_history[s].empty]
                if len(valid_syms) < 2:
                    st.error("Not enough symbols with data.")
                else:
                    start_prices = {s: float(price_history[s]["close"].iloc[0]) for s in valid_syms}
                    cap_per = initial_capital / len(valid_syms)
                    initial_holdings = {s: cap_per / start_prices[s] for s in valid_syms}

                    strat_cfg = StrategyConfig(name=strat.name, rebalance_frequency=rebalance)
                    res = backtester.run_backtest(strat, strat_cfg, bt_cfg, initial_holdings)

                    # Plots
                    c1, c2 = st.columns(2)
                    with c1:
                        st.plotly_chart(_plot_growth_with_benchmark(res, price_history, benchmark, initial_holdings) or _plot_equity_curve(res), use_container_width=True)
                    with c2:
                        st.plotly_chart(_plot_allocations(res, price_history) or _plot_trades(res, price_history), use_container_width=True)

                    st.markdown("### Metrics")
                    st.json({
                        "total_return": round(res.total_return, 4),
                        "annualized_return": round(res.annualized_return, 4),
                        "volatility": round(res.volatility, 4),
                        "sharpe_ratio": round(res.sharpe_ratio, 4),
                        "max_drawdown": round(res.max_drawdown, 4),
                        "benchmark_return": round(res.benchmark_return, 4),
                        "total_trades": int(res.total_trades),
                    })

                    # Trades table with scores
                    if getattr(res, "executed_trades", None):
                        st.markdown("### Executed Trades")
                        df_tr = pd.DataFrame(res.executed_trades)
                        # tidy columns
                        if "timestamp" in df_tr.columns:
                            df_tr["timestamp"] = pd.to_datetime(df_tr["timestamp"])
                        show_cols = [c for c in ["timestamp","symbol","action","price","quantity_shares","weight_fraction","gross_value","commission","slippage","total_cost","net_cash_delta","score","reason"] if c in df_tr.columns]
                        st.dataframe(df_tr[show_cols].sort_values("timestamp"), use_container_width=True, hide_index=True)

                    # Rebalance diagnostics
                    if getattr(res, "rebalance_details", None):
                        with st.expander("Rebalance diagnostics (weights / target / scores)"):
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
        class_copy = st.text_input("Save as Class Name (in custom)", value="EditedStrategy")
        if st.button("Save Copy to Custom"):
            if not code_area:
                st.error("No source to save.")
            else:
                try:
                    modp, cls = write_new_strategy(class_copy, class_copy, source=code_area)
                    st.success(f"Saved {modp}:{cls}")
                except Exception as e:
                    st.error(str(e))


if __name__ == "__main__":
    main()
