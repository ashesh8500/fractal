//! Strategy Workbench Component (Rust UI mirror of Streamlit workbench core features)
//! - List available strategies (from backend dynamic endpoint)
//! - View/edit code (client-side only)
//! - Validate & Register strategy via backend
//! - Run inline backtest via backend and display key metrics

use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::Portfolio;
use crate::state::Config;
use crate::api::ApiClient;
use egui::Color32;
use egui_plot::{Plot, Line, PlotPoints};
use chrono;

#[derive(Default)]
pub struct StrategyWorkbenchComponent {
    is_open: bool,
    // Backend fetched list
    strategies: Vec<String>,
    last_refresh: Option<std::time::Instant>,
    // Selected strategy module
    selected: Option<String>,
    source_code: String,
    edited_code: String,
    // Form state for new class name
    new_class_name: String,
    rebalance: String,
    symbols_csv: String,
    start_date: String,
    end_date: String,
    benchmark: String,
    // Results
    last_message: Option<String>,
    last_inline_result: Option<serde_json::Value>,
    // Timeseries data
    equity_points: Vec<[f64; 2]>,
    drawdown_points: Vec<[f64; 2]>,
    benchmark_points: Vec<[f64; 2]>,
    daily_return_points: Vec<[f64; 2]>,
    equity_min: f64,
    equity_max: f64,
    dd_min: f64,
    dd_max: f64,
    allocation_series: Vec<(String, Vec<[f64;2]>)>,
    // Async flags
    loading: bool,
    // UI toggles & extra state
    show_diff: bool,
    show_equity: bool,
    last_validation: Option<(bool, Option<String>, String)>,
    template_selected: usize,
    last_draft_save: Option<std::time::Instant>,
}

impl StrategyWorkbenchComponent {
    pub fn new() -> Self {
        #[cfg(not(target_arch = "wasm32"))]
        let draft = std::fs::read_to_string("strategy_workbench_draft.py").unwrap_or_default();
        #[cfg(target_arch = "wasm32")]
        let draft = String::new();
        let mut s = Self { is_open: false, rebalance: "monthly".into(), symbols_csv: "AAPL,MSFT,NVDA,AMZN".into(), start_date: "2024-01-01".into(), end_date: "2024-12-31".into(), benchmark: "SPY".into(), new_class_name: "NewLLMStrategy".into(), ..Default::default() };
        s.source_code = draft.clone();
        s.edited_code = draft;
        s.show_equity = true;
    s.equity_min = f64::INFINITY;
    s.equity_max = f64::NEG_INFINITY;
    s.dd_min = 0.0;
    s.dd_max = 0.0;
    s.allocation_series = Vec::new();
        s
    }

    fn refresh_if_stale(&mut self, ui: &egui::Ui, api: &ApiClient) {
        if self.loading { return; }
        let stale = self.last_refresh.map(|t| t.elapsed().as_secs() > 30).unwrap_or(true);
        if stale {
            self.loading = true;
            let api_cl = api.clone();
            let ctx = ui.ctx().clone();
            ctx.request_repaint();
            tokio_spawn(async move {
                let res = api_cl.list_strategies().await;
                ctx.memory_mut(|mem| { mem.data.insert_temp(egui::Id::new("swb_list"), res.map_err(|e| e.to_string())); });
                ctx.request_repaint();
            });
        }
    }
}

impl PortfolioComponent for StrategyWorkbenchComponent {
    fn render(&mut self, ui: &mut egui::Ui, _portfolio: &Portfolio, config: &Config) {
    ui.heading("Strategy Workbench (LLM-assisted)");
    ui.colored_label(Color32::YELLOW, "Warning: Executing custom strategy code is UNSANDBOXED. Review code before running.");
    ui.label("Author or paste code implementing BaseStrategy. Use templates, diff, and inline backtest to iterate.");
        let api = ApiClient::new(&config.api_base_url);
        self.refresh_if_stale(ui, &api);

        // Consume async list
        ui.ctx().memory_mut(|mem| {
            if let Some(res) = mem.data.get_temp::<Result<Vec<String>, String>>(egui::Id::new("swb_list")) {
                match res { Ok(list) => { self.strategies = list; self.last_refresh = Some(std::time::Instant::now()); }, Err(e) => { self.last_message = Some(format!("List failed: {}", e)); } }
                self.loading = false;
            }
        });

        ui.horizontal(|ui| {
            if ui.button("🔄 Refresh").clicked() { self.last_refresh = None; }
            if let Some(msg) = &self.last_message { ui.weak(msg); }
        });
        ui.separator();
        ui.collapsing("Available Strategies", |ui| {
            if self.strategies.is_empty() { ui.weak("<none>"); }
            for s in &self.strategies {
                let sel = self.selected.as_ref() == Some(s);
                if ui.selectable_label(sel, s).clicked() { self.selected = Some(s.clone()); }
            }
        });

        // Load source button
        if ui.button("Load Source").clicked() {
            if let Some(module) = self.selected.clone() { let api_cl = api.clone(); let ctx = ui.ctx().clone(); self.loading = true; tokio_spawn(async move { let res = api_cl.get_strategy_source(&module).await; ctx.memory_mut(|mem| { mem.data.insert_temp(egui::Id::new("swb_src"), (module.clone(), res.map_err(|e| e.to_string()))); }); ctx.request_repaint(); }); }
        }
        // Receive source
        ui.ctx().memory_mut(|mem| {
            if let Some((module, res)) = mem.data.get_temp::<(String, Result<String, String>)>(egui::Id::new("swb_src")) { match res { Ok(src) => { self.source_code = src.clone(); self.edited_code = src; self.last_message = Some(format!("Loaded {}", module)); }, Err(e) => { self.last_message = Some(format!("Load failed: {}", e)); } } self.loading = false; }
        });

        if !self.edited_code.is_empty() {
            ui.horizontal(|ui| {
                ui.checkbox(&mut self.show_diff, "Diff");
                egui::ComboBox::from_label("Templates")
                    .selected_text(strategy_templates().get(self.template_selected).map(|t| t.0).unwrap_or("None"))
                    .show_ui(ui, |ui| {
                        for (idx, (name, _code)) in strategy_templates().iter().enumerate() {
                            ui.selectable_value(&mut self.template_selected, idx, *name);
                        }
                    });
                if ui.button("Insert Overwrite").clicked() {
                    if let Some((_n, code)) = strategy_templates().get(self.template_selected) {
                        self.source_code = code.to_string();
                        self.edited_code = self.source_code.clone();
                    }
                }
                if ui.button("Append").clicked() {
                    if let Some((_n, code)) = strategy_templates().get(self.template_selected) {
                        self.edited_code.push_str("\n\n# --- Template Append ---\n");
                        self.edited_code.push_str(code);
                    }
                }
            });
            if self.show_diff {
                ui.collapsing("Diff (Original vs Edited)", |ui| {
                    for dl in compute_diff(&self.source_code, &self.edited_code) {
                        match dl.kind.as_str() {
                            "+" => { ui.colored_label(Color32::LIGHT_GREEN, format!("+ {}", dl.line)); },
                            "-" => { ui.colored_label(Color32::LIGHT_RED, format!("- {}", dl.line)); },
                            _ => { ui.label(format!("  {}", dl.line)); }
                        }
                    }
                });
            }
            ui.collapsing("Source (editable)", |ui| {
                let resp = egui::TextEdit::multiline(&mut self.edited_code)
                    .code_editor()
                    .desired_rows(22)
                    .lock_focus(true)
                    .show(ui);
                if resp.response.changed() {
                    let now = std::time::Instant::now();
                    let write_ok = self.last_draft_save.map(|t| t.elapsed().as_secs_f32() > 2.0).unwrap_or(true);
                    if write_ok {
                        #[cfg(not(target_arch = "wasm32"))]
                        { let _ = std::fs::write("strategy_workbench_draft.py", &self.edited_code); }
                        self.last_draft_save = Some(now);
                    }
                }
            });
        }

        ui.separator();
        ui.horizontal(|ui| {
            ui.label("New Class:"); ui.text_edit_singleline(&mut self.new_class_name);
            if ui.button("Validate").clicked() { let code = self.edited_code.clone(); let class_name = self.new_class_name.clone(); let api_cl = api.clone(); let ctx = ui.ctx().clone(); self.loading = true; tokio_spawn(async move { let res = api_cl.validate_strategy_code(&code, Some(&class_name)).await; ctx.memory_mut(|mem| { mem.data.insert_temp(egui::Id::new("swb_val"), res.map_err(|e| e.to_string())); }); ctx.request_repaint(); }); }
            if ui.button("Register").clicked() { let code = self.edited_code.clone(); let class_name = self.new_class_name.clone(); let api_cl = api.clone(); let ctx = ui.ctx().clone(); self.loading = true; tokio_spawn(async move { let res = api_cl.register_strategy(&class_name, &code, None).await; ctx.memory_mut(|mem| { mem.data.insert_temp(egui::Id::new("swb_reg"), res.map_err(|e| e.to_string())); }); ctx.request_repaint(); }); }
        });
        ui.ctx().memory_mut(|mem| {
            if let Some(res) = mem.data.get_temp::<Result<(bool, Option<String>, String), String>>(egui::Id::new("swb_val")) {
                match res { Ok((ok, cls, msg)) => { self.last_message = Some(format!("Validate {}: {} {}", if ok {"OK"} else {"FAIL"}, cls.clone().unwrap_or_default(), msg)); self.last_validation = Some((ok, cls, msg)); }, Err(e) => { self.last_message = Some(format!("Validate error: {}", e)); } }
                self.loading = false;
            }
            if let Some(res) = mem.data.get_temp::<Result<(bool, Option<String>, String), String>>(egui::Id::new("swb_reg")) {
                match res { Ok((ok, module, msg)) => { self.last_message = Some(format!("Register {}: {}", if ok {"OK"} else {"FAIL"}, msg)); if ok { if let Some(m) = module { self.strategies.push(m); } } }, Err(e) => { self.last_message = Some(format!("Register error: {}", e)); } }
                self.loading = false;
            }
        });

        if let Some((ok, _cls, msg)) = &self.last_validation { ui.collapsing("Validation Output", |ui| { let color = if *ok { Color32::LIGHT_GREEN } else { Color32::LIGHT_RED }; for line in msg.lines() { ui.colored_label(color, line); } }); }

        ui.separator();
        ui.heading("Inline Backtest");
        ui.horizontal(|ui| { ui.label("Symbols"); ui.text_edit_singleline(&mut self.symbols_csv); ui.label("Rebalance"); ui.text_edit_singleline(&mut self.rebalance); });
        ui.horizontal(|ui| { ui.label("Start"); ui.text_edit_singleline(&mut self.start_date); ui.label("End"); ui.text_edit_singleline(&mut self.end_date); ui.label("Benchmark"); ui.text_edit_singleline(&mut self.benchmark); });
        if ui.button("▶ Run Inline Backtest").clicked() { let code = self.edited_code.clone(); let symbols: Vec<String> = self.symbols_csv.split(',').map(|s| s.trim().to_uppercase()).filter(|s| !s.is_empty()).collect(); let sd = self.start_date.clone(); let ed = self.end_date.clone(); let reb = self.rebalance.clone(); let bench = self.benchmark.clone(); let api_cl = api.clone(); let ctx = ui.ctx().clone(); self.loading = true; tokio_spawn(async move { let res = api_cl.inline_backtest(&code, &symbols, &sd, &ed, 100000.0, 0.0005, 0.0002, &reb, &bench).await; ctx.memory_mut(|mem| { mem.data.insert_temp(egui::Id::new("swb_bt"), res.map_err(|e| e.to_string())); }); ctx.request_repaint(); }); }
        ui.ctx().memory_mut(|mem| { if let Some(res) = mem.data.get_temp::<Result<serde_json::Value, String>>(egui::Id::new("swb_bt")) { match res { Ok(v) => { self.last_inline_result = Some(v.clone()); self.last_message = Some("Backtest OK".into()); // build series
                        self.equity_points.clear(); self.benchmark_points.clear(); self.drawdown_points.clear(); self.daily_return_points.clear(); self.allocation_series.clear();
                        self.equity_min = f64::INFINITY; self.equity_max = f64::NEG_INFINITY; self.dd_min = 0.0; self.dd_max = 0.0;
                        if let Some(vals) = v.get("portfolio_values").and_then(|x| x.as_array()) { if let Some(ts) = v.get("timestamps").and_then(|x| x.as_array()) { let mut paired: Vec<(f64,f64)> = Vec::new(); for (i,(pv, tsv)) in vals.iter().zip(ts.iter()).enumerate() { if let (Some(p), Some(ts_str)) = (pv.as_f64(), tsv.as_str()) { let x = parse_timestamp_epoch(ts_str).unwrap_or(i as f64); paired.push((x,p)); if p < self.equity_min { self.equity_min = p; } if p > self.equity_max { self.equity_max = p; } } } paired.sort_by(|a,b| a.0.partial_cmp(&b.0).unwrap()); self.equity_points = paired.into_iter().map(|(x,y)| [x,y]).collect(); } }
                        if let (Some(ts), Some(bv)) = (v.get("timestamps").and_then(|x| x.as_array()), v.get("benchmark_values").and_then(|x| x.as_array())) { let mut bm: Vec<[f64;2]> = Vec::new(); for (i,(t,b)) in ts.iter().zip(bv.iter()).enumerate() { if let (Some(ts_str), Some(b_f)) = (t.as_str(), b.as_f64()) { let x = parse_timestamp_epoch(ts_str).unwrap_or(i as f64); bm.push([x,b_f]); } } self.benchmark_points = bm; }
                        if let (Some(ts), Some(dds)) = (v.get("timestamps").and_then(|x| x.as_array()), v.get("drawdowns").and_then(|x| x.as_array())) { for (i,(t,ddv)) in ts.iter().zip(dds.iter()).enumerate() { if let (Some(ts_str), Some(dd_f)) = (t.as_str(), ddv.as_f64()) { let x = parse_timestamp_epoch(ts_str).unwrap_or(i as f64); self.drawdown_points.push([x, dd_f]); if dd_f < self.dd_min { self.dd_min = dd_f; } if dd_f > self.dd_max { self.dd_max = dd_f; } } } }
                        if let Some(rets) = v.get("daily_returns").and_then(|x| x.as_array()) { for (i,r) in rets.iter().enumerate() { if let Some(rv) = r.as_f64() { self.daily_return_points.push([i as f64, rv]); } } }
                        // Allocation weights -> per symbol time series
                        if let Some(weights_arr) = v.get("allocation_weights").and_then(|x| x.as_array()) { if let Some(ts) = v.get("timestamps").and_then(|x| x.as_array()) {
                            use std::collections::BTreeMap;
                            let mut per_symbol: BTreeMap<String, Vec<[f64;2]>> = BTreeMap::new();
                            for (idx,(w_obj, tsv)) in weights_arr.iter().zip(ts.iter()).enumerate() { if let (Some(map), Some(ts_str)) = (w_obj.as_object(), tsv.as_str()) { let x = parse_timestamp_epoch(ts_str).unwrap_or(idx as f64); for (sym,val) in map.iter() { if let Some(fv) = val.as_f64() { per_symbol.entry(sym.clone()).or_default().push([x, fv]); } } } }
                            self.allocation_series = per_symbol.into_iter().collect();
                        }}
                    }, Err(e) => { self.last_message = Some(format!("Backtest error: {}", e)); } } self.loading = false; } });

    if let Some(v) = &self.last_inline_result {
        ui.separator();
        ui.colored_label(Color32::LIGHT_BLUE, "Results");
        // Metrics grid
        if let Some(tr) = v.get("total_return").and_then(|x| x.as_f64()) { ui.label(format!("Total Return: {:.2}%", tr * 100.0)); }
        if let Some(ar) = v.get("annualized_return").and_then(|x| x.as_f64()) { ui.label(format!("Annualized: {:.2}%", ar * 100.0)); }
        if let Some(vol) = v.get("volatility").and_then(|x| x.as_f64()) { ui.label(format!("Volatility: {:.2}%", vol * 100.0)); }
        if let Some(sh) = v.get("sharpe_ratio").and_then(|x| x.as_f64()) { ui.label(format!("Sharpe: {:.2}", sh)); }
        if let Some(dd) = v.get("max_drawdown").and_then(|x| x.as_f64()) { ui.label(format!("Max DD: {:.2}%", dd * 100.0)); }
        if let Some(br) = v.get("benchmark_return").and_then(|x| x.as_f64()) { ui.label(format!("Benchmark: {:.2}%", br * 100.0)); }
        if let Some(alpha) = v.get("alpha").and_then(|x| x.as_f64()) { if alpha.is_finite() { ui.label(format!("Alpha: {:.2}", alpha)); } }
        if let Some(beta) = v.get("beta").and_then(|x| x.as_f64()) { if beta.is_finite() { ui.label(format!("Beta: {:.2}", beta)); } }
        if let Some(tt) = v.get("total_trades").and_then(|x| x.as_i64()) { ui.label(format!("Trades: {}", tt)); }
        if ui.button(if self.show_equity {"Hide Plots"} else {"Show Plots"}).clicked() { self.show_equity = !self.show_equity; }
        if self.show_equity {
            // Build supplementary series if not already populated for this result
            if self.drawdown_points.is_empty() && self.last_inline_result.is_some() {
                self.drawdown_points.clear();
                self.benchmark_points.clear();
                self.daily_return_points.clear();
                if let (Some(ts), Some(dds)) = (v.get("timestamps").and_then(|x| x.as_array()), v.get("drawdowns").and_then(|x| x.as_array())) {
                    for (i,(t,ddv)) in ts.iter().zip(dds.iter()).enumerate() {
                        if let (Some(ts_str), Some(dd_f)) = (t.as_str(), ddv.as_f64()) {
                            if let Some(x) = parse_timestamp_epoch(ts_str) { self.drawdown_points.push([x, dd_f]); if dd_f < self.dd_min { self.dd_min = dd_f; } if dd_f > self.dd_max { self.dd_max = dd_f; } }
                            else { self.drawdown_points.push([i as f64, dd_f]); }
                        }
                    }
                }
                if let (Some(ts), Some(bv)) = (v.get("timestamps").and_then(|x| x.as_array()), v.get("benchmark_values").and_then(|x| x.as_array())) {
                    for (i,(t,bv_v)) in ts.iter().zip(bv.iter()).enumerate() {
                        if let (Some(ts_str), Some(bv_f)) = (t.as_str(), bv_v.as_f64()) {
                            if let Some(x) = parse_timestamp_epoch(ts_str) { self.benchmark_points.push([x, bv_f]); }
                            else { self.benchmark_points.push([i as f64, bv_f]); }
                        }
                    }
                }
                if let Some(rets) = v.get("daily_returns").and_then(|x| x.as_array()) {
                    for (i,r) in rets.iter().enumerate() { if let Some(rv) = r.as_f64() { self.daily_return_points.push([i as f64, rv]); } }
                }
            }
            // Equity & Benchmark
            if !self.equity_points.is_empty() { Plot::new("equity_plot").height(220.0).legend(egui_plot::Legend::default()).show(ui, |plot_ui| { let eq = Line::new(PlotPoints::from(self.equity_points.clone())).name("Equity"); plot_ui.line(eq); if !self.benchmark_points.is_empty() { let bm = Line::new(PlotPoints::from(self.benchmark_points.clone())).name("Benchmark").color(Color32::LIGHT_RED); plot_ui.line(bm); } }); }
            // Drawdown
            if !self.drawdown_points.is_empty() { Plot::new("drawdown_plot").height(140.0).legend(egui_plot::Legend::default()).show(ui, |plot_ui| { let dd_line = Line::new(PlotPoints::from(self.drawdown_points.clone())).name("Drawdown").color(Color32::LIGHT_RED); plot_ui.line(dd_line); }); }
            // Daily returns
            if !self.daily_return_points.is_empty() { Plot::new("daily_returns").height(140.0).legend(egui_plot::Legend::default()).show(ui, |plot_ui| { let dr = Line::new(PlotPoints::from(self.daily_return_points.clone())).name("Daily Returns").color(Color32::LIGHT_GREEN); plot_ui.line(dr); }); }
            // Allocation plot (stacked approximation via lines)
            if !self.allocation_series.is_empty() { ui.collapsing("Allocations (Weights)", |ui| { Plot::new("allocations_plot").height(200.0).legend(egui_plot::Legend::default()).show(ui, |plot_ui| { for (sym, pts) in &self.allocation_series { let line = Line::new(PlotPoints::from(pts.clone())).name(sym.clone()); plot_ui.line(line); } }); }); }
            // Trades table (top 25)
            if let Some(trades) = v.get("executed_trades").and_then(|x| x.as_array()) { ui.collapsing(format!("Executed Trades (showing up to {})", trades.len().min(25)), |ui| { let mut shown = 0; for tr in trades { if shown >= 25 { break; } if let Some(obj) = tr.as_object() { let sym = obj.get("symbol").and_then(|x| x.as_str()).unwrap_or("?"); let act = obj.get("action").and_then(|x| x.as_str()).unwrap_or(""); let qty = obj.get("quantity").and_then(|x| x.as_f64()).unwrap_or(0.0); let price = obj.get("price").and_then(|x| x.as_f64()).unwrap_or(f64::NAN); let ts = obj.get("timestamp").and_then(|x| x.as_str()).unwrap_or(""); ui.label(format!("{ts} {sym} {act} qty={:.4} @ {:.2}", qty, price)); } shown +=1; } }); }
        }
    }

        if self.loading { ui.horizontal(|ui| { ui.spinner(); ui.label("Working..."); }); }
    }

    fn name(&self) -> &str { "Strategy Workbench" }
    fn is_open(&self) -> bool { self.is_open }
    fn set_open(&mut self, open: bool) { self.is_open = open; }
    fn category(&self) -> ComponentCategory { ComponentCategory::Analytics }
}

// Helper to spawn tasks (native + wasm)
fn tokio_spawn<F>(fut: F)
where F: std::future::Future<Output = ()> + 'static + Send {
    #[cfg(not(target_arch = "wasm32"))]
    { tokio::spawn(fut); }
    #[cfg(target_arch = "wasm32")]
    { wasm_bindgen_futures::spawn_local(fut); }
}

// ---- Templates & Diff helpers ----

struct DiffLine { kind: String, line: String }

fn compute_diff(original: &str, edited: &str) -> Vec<DiffLine> {
    let orig: Vec<&str> = original.lines().collect();
    let edit: Vec<&str> = edited.lines().collect();
    let m = orig.len();
    let n = edit.len();
    let mut dp = vec![vec![0u16; n+1]; m+1];
    for i in (0..m).rev() {
        for j in (0..n).rev() {
            dp[i][j] = if orig[i] == edit[j] { dp[i+1][j+1] + 1 } else { dp[i+1][j].max(dp[i][j+1]) };
        }
    }
    let mut i=0; let mut j=0; let mut out = Vec::new();
    while i < m && j < n {
        if orig[i] == edit[j] { out.push(DiffLine { kind: " ".into(), line: orig[i].into() }); i+=1; j+=1; }
        else if dp[i+1][j] >= dp[i][j+1] { out.push(DiffLine { kind: "-".into(), line: orig[i].into() }); i+=1; }
        else { out.push(DiffLine { kind: "+".into(), line: edit[j].into() }); j+=1; }
    }
    while i < m { out.push(DiffLine { kind: "-".into(), line: orig[i].into() }); i+=1; }
    while j < n { out.push(DiffLine { kind: "+".into(), line: edit[j].into() }); j+=1; }
    out
}

fn strategy_templates() -> Vec<(&'static str, &'static str)> {
    vec![
        ("Momentum Skeleton", r#"from portfolio_lib.services.strategy.base import BaseStrategy\n\nclass MomentumTemplate(BaseStrategy):\n    def initialize(self):\n        self.lookback = 20\n\n    def generate_signals(self, data):\n        signals = {}\n        for symbol, df in data.items():\n            if len(df) > self.lookback:\n                recent = df['close'].iloc[-self.lookback:]\n                signals[symbol] = 1.0 if recent.iloc[-1] > recent.mean() else 0.0\n            else:\n                signals[symbol] = 0.0\n        return signals\n"#),
        ("Mean Reversion Skeleton", r#"from portfolio_lib.services.strategy.base import BaseStrategy\n\nclass MeanReversionTemplate(BaseStrategy):\n    def initialize(self):\n        self.window = 10\n\n    def generate_signals(self, data):\n        signals = {}\n        for symbol, df in data.items():\n            if len(df) > self.window:\n                window_slice = df['close'].iloc[-self.window:]\n                price = window_slice.iloc[-1]\n                avg = window_slice.mean()\n                signals[symbol] = -1.0 if price > avg * 1.02 else (1.0 if price < avg * 0.98 else 0.0)\n            else:\n                signals[symbol] = 0.0\n        return signals\n"#),
        ("Pair Trading Skeleton", r#"from portfolio_lib.services.strategy.base import BaseStrategy\nimport numpy as np\n\nclass PairTradingTemplate(BaseStrategy):\n    def initialize(self):\n        self.spread_window = 30\n\n    def generate_signals(self, data):\n        if len(data) < 2:\n            return {s:0.0 for s in data}\n        symbols = list(data.keys())[:2]\n        a, b = symbols\n        da, db = data[a], data[b]\n        min_len = min(len(da), len(db))\n        if min_len < self.spread_window:\n            return {a:0.0, b:0.0}\n        spread_a = da['close'].iloc[-self.spread_window:]\n        spread_b = db['close'].iloc[-self.spread_window:]\n        ratio = spread_a.values / np.where(spread_b.values==0, 1, spread_b.values)\n        z = (ratio - ratio.mean()) / (ratio.std() + 1e-9)\n        last_z = z[-1]\n        if last_z > 1.5:\n            return {a: -1.0, b: 1.0}\n        elif last_z < -1.5:\n            return {a: 1.0, b: -1.0}\n        return {a:0.0, b:0.0}\n"#),
    ]
}

fn parse_timestamp_epoch(ts: &str) -> Option<f64> {
    if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(ts) { return Some(dt.timestamp() as f64); }
    if let Ok(date) = chrono::NaiveDate::parse_from_str(ts, "%Y-%m-%d") { return Some(date.and_hms_opt(0,0,0)?.and_utc().timestamp() as f64); }
    None
}

fn format_epoch_date(ts: f64) -> String {
    if ts.is_finite() {
        let secs = ts as i64;
        if let Some(dt) = chrono::NaiveDateTime::from_timestamp_opt(secs, 0) { return dt.date().format("%Y-%m-%d").to_string(); }
    }
    String::new()
}
