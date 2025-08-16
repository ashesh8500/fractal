"""
Dear PyGui frontend for the Strategy Workbench.

Minimal Python UI to replace the Rust/egui app for local use.
- Select a strategy from portfolio_lib
- Configure symbols/time window and backtest parameters
- Run backtests using existing BacktestingService/YFinanceDataService
- View metrics and executed trades

Run:
  python -m portfolio_lib.ui.pygui_workbench

Prereqs:
  pip install dearpygui pandas numpy plotly yfinance

Notes:
- Charts are not rendered in v1 to keep MVP simple. Metrics and tables are shown.
- You can extend this to render charts by generating images and displaying as textures.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

import pandas as pd

from portfolio_lib.models.strategy import BacktestConfig, StrategyConfig
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.services.data.yfinance import YFinanceDataService

from .agent_tools import (
    ensure_custom_pkg,
    instantiate_strategy,
    list_available_strategies,
    read_strategy_source,
    validate_strategy,
)

try:
    from dearpygui import dearpygui as dpg  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("Dear PyGui is required: pip install dearpygui") from e


class PyguiWorkbench:
    def __init__(self) -> None:
        ensure_custom_pkg()
        self.state = {
            "symbols": "AAPL,MSFT,NVDA,AMZN,GOOGL,QQQ",
            "years": 3,
            "initial_capital": 100000.0,
            "commission": 0.0005,
            "slippage": 0.0002,
            "rebalance": "monthly",
            "benchmark": "QQQ",
            "strategies": list_available_strategies(),
            "selected_strategy": None,
        }
        if self.state["strategies"]:
            self.state["selected_strategy"] = self.state["strategies"][0]

        # Dear PyGui context
        dpg.create_context()
        dpg.create_viewport(
            title="Fractal - Workbench (Dear PyGui)", width=1200, height=800
        )
        self._build_ui()
        dpg.setup_dearpygui()

    # -------------- UI builders --------------
    def _build_ui(self) -> None:
        with dpg.font_registry():
            pass

        with dpg.texture_registry(show=False) as self.tex_registry:
            pass

        with dpg.window(
            label="Strategy Workbench", width=-1, height=-1
        ) as self.main_window:
            dpg.add_text("Python Dear PyGui Workbench")
            dpg.add_separator()

            with dpg.collapsing_header(label="Backtest Settings", default_open=True):
                dpg.add_input_text(
                    label="Symbols (CSV)",
                    default_value=self.state["symbols"],
                    callback=lambda s, a, u: self._on_change("symbols", a),
                )
                dpg.add_slider_int(
                    label="Years",
                    min_value=1,
                    max_value=10,
                    default_value=self.state["years"],
                    callback=lambda s, a, u: self._on_change("years", a),
                )
                dpg.add_input_float(
                    label="Initial Capital",
                    default_value=self.state["initial_capital"],
                    step=1000.0,
                    callback=lambda s, a, u: self._on_change("initial_capital", a),
                )
                dpg.add_input_float(
                    label="Commission",
                    default_value=self.state["commission"],
                    format="%.6f",
                    step=0.0001,
                    callback=lambda s, a, u: self._on_change("commission", a),
                )
                dpg.add_input_float(
                    label="Slippage",
                    default_value=self.state["slippage"],
                    format="%.6f",
                    step=0.0001,
                    callback=lambda s, a, u: self._on_change("slippage", a),
                )
                dpg.add_combo(
                    label="Rebalance",
                    items=["daily", "weekly", "monthly", "quarterly"],
                    default_value=self.state["rebalance"],
                    callback=lambda s, a, u: self._on_change("rebalance", a),
                )
                dpg.add_input_text(
                    label="Benchmark",
                    default_value=self.state["benchmark"],
                    callback=lambda s, a, u: self._on_change("benchmark", a),
                )

            dpg.add_separator()
            with dpg.collapsing_header(label="Strategy", default_open=True):
                dpg.add_combo(
                    label="Select Strategy",
                    items=self.state["strategies"],
                    default_value=self.state["selected_strategy"] or "",
                    callback=lambda s, a, u: self._on_change("selected_strategy", a),
                )
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Refresh List",
                        callback=lambda: self._refresh_strategies(),
                    )
                    dpg.add_button(
                        label="Validate", callback=lambda: self._validate_selected()
                    )
                    dpg.add_button(
                        label="Run Backtest", callback=lambda: self._run_backtest()
                    )

            dpg.add_separator()
            dpg.add_text("Output:")
            self.output_window = dpg.add_child_window(width=-1, height=300)

            dpg.add_separator()
            dpg.add_text("Charts:")
            with dpg.group(horizontal=True):
                self.chart_growth_container = dpg.add_child_window(
                    width=560, height=360
                )
                self.chart_alloc_container = dpg.add_child_window(width=560, height=360)

        dpg.set_primary_window(self.main_window, True)

    # -------------- State helpers --------------
    def _on_change(self, key: str, value):
        self.state[key] = value

    def _append_output(self, text: str) -> None:
        dpg.add_text(text, parent=self.output_window)

    def _refresh_strategies(self) -> None:
        self.state["strategies"] = list_available_strategies()
        if (
            self.state["strategies"]
            and self.state["selected_strategy"] not in self.state["strategies"]
        ):
            self.state["selected_strategy"] = self.state["strategies"][0]
        dpg.configure_item(self.main_window, label="Strategy Workbench (refreshed)")
        self._append_output("Refreshed strategies.")

    def _validate_selected(self) -> None:
        sel = self.state.get("selected_strategy")
        if not sel:
            self._append_output("No strategy selected.")
            return
        v = validate_strategy(sel)
        if v.ok:
            self._append_output(f"OK: {v.module}:{v.class_name}")
            try:
                src = read_strategy_source(v.module or sel.split(":")[0])
                self._append_output(f"Source preview (first 40 lines) for {sel}:")
                preview = "\n".join(src.splitlines()[:40])
                dpg.add_input_text(
                    multiline=True,
                    readonly=True,
                    default_value=preview,
                    width=-1,
                    height=200,
                    parent=self.output_window,
                )
            except Exception as e:
                self._append_output(f"Failed to read source: {e}")
        else:
            self._append_output(f"Invalid: {v.message}")

    # -------------- Backtest --------------
    def _run_backtest_async(self) -> None:
        # Deprecated: Dear PyGui is not thread-safe for UI updates; run synchronously.
        self._run_backtest()

    def _run_backtest(self) -> None:
        try:
            sel = self.state.get("selected_strategy")
            if not sel:
                self._append_output("No strategy selected.")
                return
            # Instantiate
            try:
                strat = instantiate_strategy(sel)
            except Exception as e:
                self._append_output(f"Instantiate failed: {e}")
                return

            # Build config
            syms = [
                s.strip().upper()
                for s in str(self.state["symbols"]).split(",")
                if s.strip()
            ]
            years = int(self.state["years"]) if self.state["years"] else 3
            end = datetime.today().date()
            start = end - timedelta(days=365 * years)
            bt_cfg = BacktestConfig(
                start_date=datetime.combine(start, datetime.min.time()),
                end_date=datetime.combine(end, datetime.min.time()),
                initial_capital=float(self.state["initial_capital"]),
                commission=float(self.state["commission"]),
                slippage=float(self.state["slippage"]),
                benchmark=str(self.state["benchmark"]),
            )

            data = YFinanceDataService()
            backtester = BacktestingService(data)
            price_history = data.fetch_price_history(
                syms,
                bt_cfg.start_date.strftime("%Y-%m-%d"),
                bt_cfg.end_date.strftime("%Y-%m-%d"),
            )
            valid_syms = [
                s for s in syms if s in price_history and not price_history[s].empty
            ]
            if len(valid_syms) < 2:
                self._append_output("Not enough symbols with data.")
                return

            start_prices = {
                s: float(price_history[s]["close"].iloc[0]) for s in valid_syms
            }
            cap_per = bt_cfg.initial_capital / len(valid_syms)
            initial_holdings = {s: cap_per / start_prices[s] for s in valid_syms}

            strat_cfg = StrategyConfig(
                name=strat.name, rebalance_frequency=str(self.state["rebalance"])
            )
            res = backtester.run_backtest(strat, strat_cfg, bt_cfg, initial_holdings)

            # Charts
            try:
                growth_fig = self._plot_growth(
                    res, price_history, str(self.state["benchmark"]), initial_holdings
                )
                alloc_fig = self._plot_allocations(res, price_history)
                self._render_plot_to_container(
                    growth_fig, self.chart_growth_container, title_hint="Equity Curve"
                )
                if alloc_fig is not None:
                    self._render_plot_to_container(
                        alloc_fig, self.chart_alloc_container, title_hint="Allocations"
                    )
                else:
                    self._append_output("No allocation data to chart.")
            except Exception as e:
                self._append_output(f"Chart rendering unavailable: {e}")

            # Output metrics
            metrics = {
                "total_return": round(res.total_return, 4),
                "annualized_return": round(res.annualized_return, 4),
                "volatility": round(res.volatility, 4),
                "sharpe_ratio": round(res.sharpe_ratio, 4),
                "max_drawdown": round(res.max_drawdown, 4),
                "benchmark_return": round(res.benchmark_return, 4),
                "total_trades": int(res.total_trades),
            }
            self._append_output(
                f"Backtest complete for {sel} on {', '.join(valid_syms)}"
            )
            for k, v in metrics.items():
                self._append_output(f"  {k}: {v}")

            # Trades table preview
            if getattr(res, "executed_trades", None):
                df_tr = pd.DataFrame(res.executed_trades)
                cols = [
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
                head = df_tr[cols].head(25)
                dpg.add_text("Executed Trades (head)", parent=self.output_window)
                dpg.add_input_text(
                    multiline=True,
                    readonly=True,
                    width=-1,
                    height=200,
                    default_value=head.to_string(index=False),
                    parent=self.output_window,
                )
        except Exception as e:  # pragma: no cover
            self._append_output(f"Backtest error: {e}")

    # -------------- Plot helpers --------------
    def _build_close_frame(
        self, price_history: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
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
            s = pd.Series(df[col].values, index=pd.to_datetime(df.index), name=sym)
            series.append(s)
        if not series:
            return pd.DataFrame()
        return pd.concat(series, axis=1).sort_index().ffill()

    def _plot_growth(
        self,
        res,
        price_history: Dict[str, pd.DataFrame],
        benchmark: str,
        initial_holdings: Dict[str, float],
    ):
        import importlib

        go = importlib.import_module("plotly.graph_objects")
        idx = pd.to_datetime(res.timestamps)
        closes = self._build_close_frame(price_history).reindex(idx).ffill()
        strat = pd.Series(res.portfolio_values, index=idx)
        fig = go.Figure()
        if len(strat):
            g = strat / float(strat.iloc[0])
            fig.add_trace(go.Scatter(x=idx, y=g.values, mode="lines", name="Strategy"))
        if not closes.empty and benchmark in closes.columns:
            b = closes[benchmark]
            b = b / float(b.iloc[0])
            fig.add_trace(go.Scatter(x=idx, y=b.values, mode="lines", name="Benchmark"))
        inter = [s for s in initial_holdings.keys() if s in closes.columns]
        if inter:
            px = closes[inter]
            shares = pd.Series({s: float(initial_holdings.get(s, 0.0)) for s in inter})
            base_val = (px * shares).sum(axis=1)
            base_g = base_val / float(base_val.iloc[0])
            fig.add_trace(
                go.Scatter(x=idx, y=base_g.values, mode="lines", name="Baseline")
            )
        fig.update_layout(
            title="Growth of $1", xaxis_title="Date", yaxis_title="Growth"
        )
        return fig

    def _plot_allocations(self, res, price_history: Dict[str, pd.DataFrame]):
        import importlib

        go = importlib.import_module("plotly.graph_objects")
        idx = pd.to_datetime(res.timestamps)
        if not getattr(res, "holdings_history", None) or len(idx) == 0:
            return None
        closes = self._build_close_frame(price_history).reindex(idx).ffill()
        if closes.empty:
            return None
        weights = []
        for i, ts in enumerate(idx):
            hh = res.holdings_history[i] if i < len(res.holdings_history) else {}
            if not hh:
                weights.append(pd.Series(0.0, index=closes.columns))
                continue
            prices = closes.loc[ts].reindex(closes.columns).astype(float)
            pos_val = (
                pd.Series({k: float(hh.get(k, 0.0)) for k in closes.columns}) * prices
            )
            tot = float(pos_val.sum())
            w = (pos_val / tot) if tot > 0 else pos_val
            weights.append(w)
        wdf = pd.concat(weights, axis=1).T
        wdf.index = idx
        means = wdf.mean().sort_values(ascending=False)
        ordered = list(means.index)
        wdf = wdf[ordered].fillna(0.0).clip(lower=0.0, upper=1.0)
        fig = go.Figure()
        for col in ordered:
            fig.add_trace(
                go.Scatter(
                    x=wdf.index,
                    y=wdf[col].values,
                    mode="lines",
                    name=col,
                    stackgroup="one",
                    groupnorm="fraction",
                )
            )
        fig.update_layout(
            title="Portfolio Allocation",
            xaxis_title="Date",
            yaxis_title="Weight",
            yaxis=dict(range=[0, 1]),
        )
        return fig

    def _render_plot_to_container(
        self, fig, container_id, title_hint: str = ""
    ) -> None:
        if fig is None:
            return
        # Convert to PNG using plotly/kaleido
        try:
            png_bytes = fig.to_image(format="png", engine="kaleido", scale=2)
        except Exception as e:
            self._append_output(
                f"Plotly image conversion failed (install kaleido): {e}"
            )
            return
        # Write to temp file and load into Dear PyGui texture
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(png_bytes)
            tmp_path = tmp.name
        try:
            w, h, c, data = dpg.load_image(tmp_path)
            # clear previous children in container
            try:
                dpg.delete_item(container_id, children_only=True)
            except Exception:
                pass
            # register texture in the existing registry
            tex_id = dpg.add_static_texture(w, h, data, parent=self.tex_registry)
            if title_hint:
                dpg.add_text(title_hint, parent=container_id)
            dpg.add_image(tex_id, parent=container_id)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def run(self) -> None:
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()


def main() -> None:
    app = PyguiWorkbench()
    app.run()


if __name__ == "__main__":
    main()
