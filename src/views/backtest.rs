use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::{BacktestResult, Portfolio};
use crate::state::Config;
use std::io::Write;

#[derive(Default)]
pub struct BacktestComponent {
    is_open: bool,
    // Form state
    strategy_name: String,
    start_date: String,
    end_date: String,
    initial_capital: f64,
    commission: f64,
    slippage: f64,
    benchmark: String,

    // Local error/info
    last_msg: Option<String>,

    // Trades filters
    filter_start: String,
    filter_end: String,
    filter_symbol: String,
}

impl BacktestComponent {
    pub fn new() -> Self {
        Self {
            is_open: true,
            strategy_name: "momentum".to_string(),
            start_date: "2024-01-01".to_string(),
            end_date: "2024-12-31".to_string(),
            initial_capital: 100_000.0,
            commission: 0.001,
            slippage: 0.0005,
            benchmark: "SPY".to_string(),
            last_msg: None,
            filter_start: "".to_string(),
            filter_end: "".to_string(),
            filter_symbol: "".to_string(),
        }
    }
}

impl PortfolioComponent for BacktestComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        ui.heading("Backtesting");
        ui.label(format!("Portfolio: {}", portfolio.name));

        ui.separator();
        egui::Grid::new(ui.id().with("bt_form"))
            .num_columns(2)
            .spacing([8.0, 6.0])
            .show(ui, |ui| {
                ui.label("Strategy");
                ui.text_edit_singleline(&mut self.strategy_name);
                ui.end_row();

                ui.label("Start Date");
                ui.text_edit_singleline(&mut self.start_date);
                ui.end_row();

                ui.label("End Date");
                ui.text_edit_singleline(&mut self.end_date);
                ui.end_row();

                ui.label("Initial Capital");
                ui.add(egui::DragValue::new(&mut self.initial_capital).speed(1000.0));
                ui.end_row();

                ui.label("Commission");
                ui.add(egui::DragValue::new(&mut self.commission).speed(0.0001).range(0.0..=0.1));
                ui.end_row();

                ui.label("Slippage");
                ui.add(egui::DragValue::new(&mut self.slippage).speed(0.0001).range(0.0..=0.1));
                ui.end_row();

                ui.label("Benchmark");
                ui.text_edit_singleline(&mut self.benchmark);
                ui.end_row();
            });

        ui.add_space(6.0);

        // Fire-and-forget event; the app loop will pick this up and call backend.
        if ui.button("▶ Run Backtest").clicked() {
            let payload = BacktestEventPayload {
                portfolio_name: portfolio.name.clone(),
                strategy_name: self.strategy_name.clone(),
                start_date: self.start_date.clone(),
                end_date: self.end_date.clone(),
                initial_capital: self.initial_capital,
                commission: self.commission,
                slippage: self.slippage,
                benchmark: self.benchmark.clone(),
            };
            emit_backtest_request(ui, payload);
            self.last_msg = Some("Backtest requested…".to_string());
        }

        if let Some(msg) = &self.last_msg {
            ui.weak(msg);
        }

        ui.separator();
        ui.heading("Results");
        if let Some(result) = &portfolio.backtest_results {
            render_backtest_result(ui, result);
            // Executed trades table (if available)
            if let Some(trades) = &portfolio.backtest_trades {
                ui.add_space(8.0);
                ui.heading("Executed Trades");
                ui.horizontal(|ui| {
                    ui.label("Filter Start (YYYY-MM-DD):");
                    ui.text_edit_singleline(&mut self.filter_start);
                    ui.label("End:");
                    ui.text_edit_singleline(&mut self.filter_end);
                    ui.label("Symbol:");
                    ui.text_edit_singleline(&mut self.filter_symbol);
                    if ui.button("Export CSV").clicked() {
                        export_trades_csv(trades);
                    }
                });
                egui::ScrollArea::vertical().max_height(220.0).show(ui, |ui| {
                    egui::Grid::new(ui.id().with("trades_grid")).striped(true).num_columns(7).show(ui, |ui| {
                        ui.strong("Time"); ui.strong("Symbol"); ui.strong("Action"); ui.strong("Shares"); ui.strong("Price"); ui.strong("$ Gross"); ui.strong("$ NetΔ");
                        ui.end_row();
                        for t in trades.iter().filter(|t| trade_passes_filter(t, &self.filter_start, &self.filter_end, &self.filter_symbol)) {
                            ui.label(t.timestamp.format("%Y-%m-%d").to_string());
                            ui.label(&t.symbol);
                            let color = if t.action == "buy" { egui::Color32::LIGHT_GREEN } else { egui::Color32::LIGHT_RED };
                            ui.colored_label(color, &t.action);
                            ui.label(format!("{:.2}", t.quantity_shares));
                            ui.label(format!("{:.2}", t.price));
                            ui.label(format!("{:.0}", t.gross_value));
                            ui.label(format!("{:.0}", t.net_cash_delta));
                            ui.end_row();
                        }
                    });
                });
            }

            // Allocation chart per rebalance date (if available)
            ui.add_space(8.0);
            ui.heading("Equity & Benchmark");
            render_equity_and_benchmark(ui, result);

            ui.add_space(8.0);
            ui.heading("Drawdown");
            render_drawdown_plot(ui, result);

            if let Some(_w) = &result.weights_over_time {
                ui.add_space(8.0);
                ui.heading("Allocations over time");
                render_allocations_plot(ui, result);
            }
        } else {
            ui.weak("No backtest results yet.");
        }
    }

    fn name(&self) -> &str { "Backtesting" }
    fn is_open(&self) -> bool { self.is_open }
    fn set_open(&mut self, open: bool) { self.is_open = open; }
    fn category(&self) -> ComponentCategory { ComponentCategory::Analytics }
}

fn render_backtest_result(ui: &mut egui::Ui, r: &BacktestResult) {
    ui.horizontal(|ui| {
        ui.label("Strategy:");
        ui.monospace(&r.strategy_name);
    });

    ui.add_space(4.0);
    egui::Grid::new(ui.id().with("bt_metrics"))
        .num_columns(2)
        .spacing([8.0, 2.0])
        .show(ui, |ui| {
            ui.label("Total Return");
            ui.label(format!("{:.2}%", r.performance.total_return * 100.0));
            ui.end_row();

            ui.label("Annualized Return");
            ui.label(format!("{:.2}%", r.performance.annualized_return * 100.0));
            ui.end_row();

            ui.label("Alpha");
            ui.label(format!("{:.2}", r.performance.alpha));
            ui.end_row();

            ui.label("Beta");
            ui.label(format!("{:.2}", r.performance.beta));
            ui.end_row();

            ui.label("Trades Executed");
            ui.label(format!("{}", r.trades_executed));
            ui.end_row();

            ui.label("Final Value");
            ui.label(format!("${:.0}", r.final_portfolio_value));
            ui.end_row();
        });

    // Optional: small equity curve preview using egui_plot
    use egui_plot::{Line, Plot};
    let points: Vec<[f64; 2]> = r
        .equity_curve
        .iter()
        .enumerate()
        .map(|(i, p)| [i as f64, p.value])
        .collect();
    Plot::new(ui.id().with("equity_curve"))
        .height(180.0)
        .allow_zoom(true)
        .allow_scroll(false)
        .show(ui, |plot_ui| {
            plot_ui.line(Line::new(points).name("Equity"));
        });
}

fn render_equity_and_benchmark(ui: &mut egui::Ui, r: &BacktestResult) {
    use egui_plot::{Legend, Line, Plot};
    let eq: Vec<[f64; 2]> = r.equity_curve.iter().enumerate().map(|(i, p)| [i as f64, p.value]).collect();
    let bm: Option<Vec<[f64; 2]>> = r.benchmark_curve.as_ref().map(|v| v.iter().enumerate().map(|(i, p)| [i as f64, p.value]).collect());
    Plot::new(ui.id().with("equity_benchmark"))
        .height(220.0)
        .legend(Legend::default())
        .allow_zoom(true)
        .allow_scroll(false)
        .show(ui, |plot_ui| {
            plot_ui.line(Line::new(eq).name("Equity"));
            if let Some(bm) = bm { plot_ui.line(Line::new(bm).name("Benchmark")); }
        });
}

fn render_drawdown_plot(ui: &mut egui::Ui, r: &BacktestResult) {
    use egui_plot::{Line, Plot};
    if r.equity_curve.is_empty() { ui.weak("No equity curve"); return; }
    let mut peak = r.equity_curve[0].value;
    let mut dd: Vec<[f64; 2]> = Vec::with_capacity(r.equity_curve.len());
    for (i, p) in r.equity_curve.iter().enumerate() {
        if p.value > peak { peak = p.value; }
        let drawdown = if peak > 0.0 { (p.value / peak) - 1.0 } else { 0.0 };
        dd.push([i as f64, drawdown]);
    }
    Plot::new(ui.id().with("drawdown_plot"))
        .height(160.0)
        .allow_zoom(true)
        .allow_scroll(false)
        .show(ui, |plot_ui| {
            plot_ui.line(Line::new(dd).name("Drawdown"));
        });
}

fn render_allocations_plot(ui: &mut egui::Ui, r: &BacktestResult) {
    use egui_plot::{Legend, Plot, Polygon};
    if let Some(wot) = &r.weights_over_time {
        // Collect a stable list of symbols across snapshots
        let mut sym_set: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        for snap in wot { for k in snap.weights.keys() { sym_set.insert(k.clone()); } }
        let symbols: Vec<String> = sym_set.into_iter().collect();
        let n = wot.len();
        if symbols.is_empty() || n == 0 { ui.weak("No allocation snapshots"); return; }

        // Initialize cumulative bottoms at 0 for stacked areas
        let mut cum_bottom: Vec<f64> = vec![0.0; n];

        Plot::new(ui.id().with("allocations_plot"))
            .height(240.0)
            .legend(Legend::default())
            .allow_zoom(true)
            .allow_scroll(false)
            .show(ui, |plot_ui| {
                for (si, sym) in symbols.iter().enumerate() {
                    // Compute top as bottom + weight for this symbol at each snapshot
                    let mut top: Vec<f64> = Vec::with_capacity(n);
                    for (i, snap) in wot.iter().enumerate() {
                        let w = snap.weights.get(sym).copied().unwrap_or(0.0).max(0.0);
                        top.push(cum_bottom[i] + w);
                    }

                    // Build polygon: along top (increasing x), back along bottom (reverse x)
                    let mut verts: Vec<[f64; 2]> = Vec::with_capacity(n * 2);
                    for i in 0..n { verts.push([i as f64, top[i]]); }
                    for i in (0..n).rev() { verts.push([i as f64, cum_bottom[i]]); }

                    // Color per symbol using HSV hue ramp
                    let h = if symbols.len() > 1 { si as f32 / (symbols.len() as f32) } else { 0.0 };
                    let fill: egui::Color32 = egui::Color32::from(egui::ecolor::Hsva::new(h, 0.65, 0.9, 0.85));

                    let poly = Polygon::new(verts).fill_color(fill).name(sym);
                    plot_ui.polygon(poly);

                    // Advance bottom to top for next layer
                    cum_bottom = top;
                }
            });
    } else {
        ui.weak("No allocation snapshots");
    }
}

fn trade_passes_filter(t: &crate::portfolio::TradeExecution, start: &str, end: &str, sym: &str) -> bool {
    let mut ok = true;
    if !sym.trim().is_empty() { ok &= t.symbol.to_uppercase().contains(&sym.trim().to_uppercase()); }
    if !start.trim().is_empty() {
        if let Ok(sd) = chrono::NaiveDate::parse_from_str(start.trim(), "%Y-%m-%d") { ok &= t.timestamp.date_naive() >= sd; }
    }
    if !end.trim().is_empty() {
        if let Ok(ed) = chrono::NaiveDate::parse_from_str(end.trim(), "%Y-%m-%d") { ok &= t.timestamp.date_naive() <= ed; }
    }
    ok
}

fn export_trades_csv(trades: &Vec<crate::portfolio::TradeExecution>) {
    // Write to current working directory
    let mut path = match std::env::current_dir() { Ok(p) => p, Err(_) => return };
    path.push("trades_export.csv");
    let mut w = match std::fs::File::create(&path) { Ok(f) => f, Err(_) => return };
    let _ = writeln!(w, "timestamp,symbol,action,shares,weight,price,gross,commission,slippage,total_cost,net_cash_delta,reason");
    for t in trades {
        let ts = t.timestamp.to_rfc3339();
        let reason = t.reason.clone().unwrap_or_default().replace(",", " ");
        let _ = writeln!(w, "{},{},{},{:.4},{:.6},{:.4},{:.2},{:.2},{:.2},{:.2},{:.2},{}",
            ts, t.symbol, t.action, t.quantity_shares, t.weight_fraction, t.price, t.gross_value, t.commission, t.slippage, t.total_cost, t.net_cash_delta, reason);
    }
}

// ---------------- Event plumbing ----------------

#[derive(Clone, Debug)]
pub struct BacktestEventPayload {
    pub portfolio_name: String,
    pub strategy_name: String,
    pub start_date: String,
    pub end_date: String,
    pub initial_capital: f64,
    pub commission: f64,
    pub slippage: f64,
    pub benchmark: String,
}

// Use egui memory as a lightweight event bus so we don't introduce global statics.
pub fn emit_backtest_request(ui: &egui::Ui, payload: BacktestEventPayload) {
    ui.memory_mut(|mem| {
        let id = egui::Id::new("backtest_events");
        let mut list: Vec<BacktestEventPayload> = mem.data.get_temp(id).unwrap_or_default();
        list.push(payload);
        mem.data.insert_temp(id, list);
    });
}

pub fn drain_backtest_requests(ctx: &egui::Context) -> Vec<BacktestEventPayload> {
    let mut out = Vec::new();
    ctx.memory_mut(|mem| {
        let id = egui::Id::new("backtest_events");
        if let Some(mut list) = mem.data.get_temp::<Vec<BacktestEventPayload>>(id) {
            out.append(&mut list);
            mem.data.remove::<Vec<BacktestEventPayload>>(id);
        }
    });
    out
}
