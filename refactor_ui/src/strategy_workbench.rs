use yew::prelude::*;
use crate::charts;
use serde::{Deserialize, Serialize};
use wasm_bindgen_futures::spawn_local;
use reqwest::Client;

#[derive(Clone, PartialEq, Deserialize, Debug)]
struct StrategyListResponse { strategies: Vec<String> }

#[derive(Clone, PartialEq, Deserialize, Debug)]
struct StrategySourceResponse { module: String, source: String }

#[derive(Clone, PartialEq, Deserialize, Debug)]
struct StrategyValidationResponse { ok: bool, message: String, class_name: Option<String> }

#[derive(Clone, PartialEq, Deserialize, Debug)]
struct StrategyRegisterResponse { ok: bool, class_name: Option<String>, message: Option<String> }

#[derive(Clone, Serialize)]
struct StrategyCodeRequest { code: String, class_name: Option<String> }

#[derive(Clone, Serialize)]
struct StrategyRegisterRequest { class_name: String, code: String, strategy_name: Option<String> }

#[derive(Clone, Serialize)]
struct InlineBacktestRequest {
    code: String,
    symbols: Vec<String>,
    start_date: String,
    end_date: String,
    initial_capital: f64,
    commission: f64,
    slippage: f64,
    rebalance: String,
    benchmark: String,
}

#[derive(Clone, Deserialize, Debug, PartialEq)]
struct InlineBacktestResponse {
    ok: bool,
    message: Option<String>,
    strategy_name: Option<String>,
    total_return: Option<f64>,
    annualized_return: Option<f64>,
    volatility: Option<f64>,
    sharpe_ratio: Option<f64>,
    max_drawdown: Option<f64>,
    benchmark_return: Option<f64>,
    alpha: Option<f64>,
    beta: Option<f64>,
    portfolio_values: Option<Vec<f64>>,
    timestamps: Option<Vec<String>>,
    drawdowns: Option<Vec<f64>>,
    daily_returns: Option<Vec<f64>>,
    benchmark_values: Option<Vec<f64>>,
}

#[derive(Default, Clone, PartialEq)]
struct WorkbenchState {
    strategies: Vec<String>,
    selected: Option<String>,
    source: String,
    edited: String,
    class_name: String,
    symbols: String,
    start_date: String,
    end_date: String,
    rebalance: String,
    benchmark: String,
    status: String,
    last_validation: Option<StrategyValidationResponse>,
    backtest: Option<InlineBacktestResponse>,
}

impl WorkbenchState {
    fn new() -> Self { Self { class_name: "NewStrategy".into(), symbols: "AAPL,MSFT,NVDA".into(), start_date: "2024-01-01".into(), end_date: "2024-12-31".into(), rebalance: "monthly".into(), benchmark: "SPY".into(), ..Default::default() } }
}

#[function_component(StrategyWorkbenchApp)]
pub fn strategy_workbench_app() -> Html {
    let api_base = std::env::var("FRONTEND_API_BASE").unwrap_or_else(|_| "http://127.0.0.1:8000/api/v1".into());
    let client = Client::new();
    let state = use_state(WorkbenchState::new);

    // Fetch strategies
    {
        let state = state.clone();
        let client = client.clone();
        let api = api_base.clone();
        use_effect_with((), move |_| {
            spawn_local(async move {
                if let Ok(resp) = client.get(format!("{}/strategies", api)).send().await {
                    if let Ok(parsed) = resp.json::<StrategyListResponse>().await {
                        let mut s = (*state).clone();
                        s.strategies = parsed.strategies;
                        s.status = "Fetched strategies".into();
                        state.set(s);
                    }
                }
            });
            || ()
        });
    }

    // Handlers
    let on_load_source = {
        let state = state.clone();
        let client = client.clone();
        let api = api_base.clone();
        Callback::from(move |_| {
            if let Some(sel) = &state.selected {
                let sel = sel.clone();
                let state2 = state.clone();
                let client2 = client.clone();
                let api2 = api.clone();
                spawn_local(async move {
                    let url = format!("{}/strategies/source?module={}", api2, sel);
                    match client2.get(url).send().await {
                        Ok(r) => match r.json::<StrategySourceResponse>().await {
                            Ok(resp) => {
                            let mut s = (*state2).clone();
                            s.source = resp.source.clone();
                            s.edited = resp.source;
                            s.status = format!("Loaded {}", sel);
                            state2.set(s);
                            },
                            Err(e) => { let mut s = (*state2).clone(); s.status = format!("Parse failed: {}", e); state2.set(s); }
                        },
                        Err(e) => { let mut s = (*state2).clone(); s.status = format!("Load failed: {}", e); state2.set(s); }
                    }
                });
            }
        })
    };

    let on_validate = {
        let state = state.clone();
        let client = client.clone();
        let api = api_base.clone();
        Callback::from(move |_| {
            let payload = StrategyCodeRequest { code: state.edited.clone(), class_name: Some(state.class_name.clone()) };
            let state2 = state.clone(); let client2 = client.clone(); let api2 = api.clone();
            spawn_local(async move {
                match client2.post(format!("{}/strategies/validate", api2)).json(&payload).send().await {
                    Ok(r) => match r.json::<StrategyValidationResponse>().await {
                        Ok(resp) => { let mut s = (*state2).clone(); s.last_validation = Some(resp.clone()); s.status = format!("Validation: {}", resp.message); state2.set(s); },
                        Err(e) => { let mut s = (*state2).clone(); s.status = format!("Validation parse error: {}", e); state2.set(s); }
                    },
                    Err(e) => { let mut s = (*state2).clone(); s.status = format!("Validation error: {}", e); state2.set(s); }
                }                
            });
        })
    };

    let on_register = {
        let state = state.clone(); let client = client.clone(); let api = api_base.clone();
        Callback::from(move |_| {
            let payload = StrategyRegisterRequest { class_name: state.class_name.clone(), code: state.edited.clone(), strategy_name: None };
            let state2 = state.clone(); let client2 = client.clone(); let api2 = api.clone();
            spawn_local(async move {
                match client2.post(format!("{}/strategies/register", api2)).json(&payload).send().await {
                    Ok(r) => match r.json::<StrategyRegisterResponse>().await {
                        Ok(resp) => { let mut s = (*state2).clone(); if resp.ok { s.strategies.push(resp.class_name.clone().unwrap_or_default()); } s.status = format!("Register: {:?}", resp.message); state2.set(s); },
                        Err(e) => { let mut s = (*state2).clone(); s.status = format!("Register parse error: {}", e); state2.set(s); }
                    },
                    Err(e) => { let mut s = (*state2).clone(); s.status = format!("Register error: {}", e); state2.set(s); }
                }                
            });
        })
    };

    let on_backtest = {
        let state = state.clone(); let client = client.clone(); let api = api_base.clone();
        Callback::from(move |_| {
            let symbols: Vec<String> = state.symbols.split(',').map(|s| s.trim().to_uppercase()).filter(|s| !s.is_empty()).collect();
            let payload = InlineBacktestRequest { code: state.edited.clone(), symbols, start_date: state.start_date.clone(), end_date: state.end_date.clone(), initial_capital: 100000.0, commission: 0.0005, slippage: 0.0002, rebalance: state.rebalance.clone(), benchmark: state.benchmark.clone() };
            let state2 = state.clone(); let client2 = client.clone(); let api2 = api.clone();
            spawn_local(async move {
                match client2.post(format!("{}/strategies/backtest-inline", api2)).json(&payload).send().await {
                    Ok(r) => match r.json::<InlineBacktestResponse>().await {
                        Ok(resp) => { let mut s = (*state2).clone(); s.backtest = Some(resp.clone()); s.status = format!("Backtest: {}", resp.message.clone().unwrap_or_default()); state2.set(s); },
                        Err(e) => { let mut s = (*state2).clone(); s.status = format!("Backtest parse error: {}", e); state2.set(s); }
                    },
                    Err(e) => { let mut s = (*state2).clone(); s.status = format!("Backtest error: {}", e); state2.set(s); }
                }                
            });
        })
    };

    let state_view = (*state).clone();

    // Chart rendering effect
    {
        let bt_dep = state_view.backtest.clone();
        use_effect_with(bt_dep, move |bto| {
            if let Some(bt) = bto.as_ref() {
                wasm_bindgen_futures::spawn_local({
                    let bt_clone = bt.clone(); async move {
                        gloo_timers::future::TimeoutFuture::new(15).await;
                        if let (Some(pv), Some(bv)) = (&bt_clone.portfolio_values, &bt_clone.benchmark_values) {
                            charts::draw_line_chart("equity_chart", &[charts::LineSeries{label:"Portfolio", data: pv, color:"#4aa3ff"}, charts::LineSeries{label:"Benchmark", data: bv, color:"#a384ff"}], 180);
                        }
                        if let Some(dd) = &bt_clone.drawdowns { charts::draw_area_chart("drawdown_chart", dd, 120, "#e05252"); }
                        if let Some(dr) = &bt_clone.daily_returns { charts::draw_bar_chart("returns_chart", dr, 120, "#46c07a", "#d36a6a"); }
                    }
                });
            }
            || ()
        });
    }

    html! {
        <div class="app-shell" style="font-family: 'JetBrains Mono', monospace; background:#0f1115; color:#e0e6ef; min-height:100vh; padding:12px;">
            <h1 style="font-weight:500; letter-spacing:1px;">{"Strategy Workbench (Refactor Prototype)"}</h1>
            <p style="color:#8892b0; font-size:0.85rem;">{"Securely iterate strategy code, validate & backtest. This prototype focuses on core workflow with a lean high-performance aesthetic."}</p>
            <div class="grid" style="display:grid; grid-template-columns:220px 1fr; gap:12px;">
                <div class="side" style="border:1px solid #1f242d; padding:8px; border-radius:6px; background:#14181f;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:0.8rem; opacity:0.7;">{"Strategies"}</span>
                        <button onclick={on_load_source.clone()} style="background:#1d2430; color:#b0c4ff; border:0; padding:2px 6px; font-size:0.65rem; border-radius:4px; cursor:pointer;">{"Load"}</button>
                    </div>
                    <div style="max-height:240px; overflow:auto; font-size:0.7rem;">
                    { for state_view.strategies.iter().map(|m| {
                        let sel = state_view.selected.clone();
                        let m2 = m.clone();
                        let state_click = state.clone();
                        html! { <div onclick={Callback::from(move |_| { let mut s = (*state_click).clone(); s.selected = Some(m2.clone()); s.status = format!("Selected {}", m2); state_click.set(s); })}
                            style={format!("padding:4px 6px; margin:2px 0; border-radius:4px; cursor:pointer; background:{};", if sel.as_ref()==Some(m){"#243040"} else {"transparent"})}>{ m }</div> }
                    }) }
                    </div>
                    <div style="margin-top:8px;">
                        <label style="display:block; font-size:0.65rem; opacity:0.7;">{"Class Name"}</label>
                        <input value={state_view.class_name.clone()} oninput={
                            let state = state.clone(); Callback::from(move |e: InputEvent| { let input: web_sys::HtmlInputElement = e.target_unchecked_into(); let mut s = (*state).clone(); s.class_name = input.value(); state.set(s); })
                        } style="width:100%; background:#0f1319; border:1px solid #1d2530; color:#c9d4e2; font-size:0.7rem; padding:4px; border-radius:4px;" />
                        <div style="display:flex; gap:4px; margin-top:6px;">
                            <button onclick={on_validate} style="flex:1; background:#22324a; border:0; color:#d0e0ff; padding:4px; font-size:0.65rem; border-radius:4px; cursor:pointer;">{"Validate"}</button>
                            <button onclick={on_register} style="flex:1; background:#1f3d2d; border:0; color:#cfe9d2; padding:4px; font-size:0.65rem; border-radius:4px; cursor:pointer;">{"Register"}</button>
                        </div>
                    </div>
                    <div style="margin-top:12px; font-size:0.6rem; color:#6a7688; white-space:pre-line;">{ state_view.status.clone() }</div>
                </div>
                <div class="main" style="display:flex; flex-direction:column; gap:12px;">
                    <div style="display:grid; grid-template-columns:1fr 320px; gap:12px;">
                        <div style="border:1px solid #1f242d; background:#14181f; padding:8px; border-radius:6px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:0.75rem; opacity:0.7;">{"Source (editable)"}</span>
                                <button onclick={on_backtest.clone()} style="background:#2c3852; border:0; color:#c3d4f5; padding:4px 10px; font-size:0.65rem; border-radius:4px; cursor:pointer;">{"Run Inline Backtest"}</button>
                            </div>
                            <textarea value={state_view.edited.clone()} oninput={
                                let state = state.clone(); Callback::from(move |e: InputEvent| { let input: web_sys::HtmlTextAreaElement = e.target_unchecked_into(); let mut s = (*state).clone(); s.edited = input.value(); state.set(s); })
                            } style="width:100%; height:380px; margin-top:6px; background:#0e1217; color:#d5e2f2; border:1px solid #1d2530; font-size:0.65rem; font-family:'JetBrains Mono',monospace; line-height:1.35; padding:8px; border-radius:4px; resize:vertical;" />
                            { if let Some(val) = &state_view.last_validation { let color = if val.ok {"#8fd19e"} else {"#e08f8f"}; html!{ <div style={format!("margin-top:6px; font-size:0.6rem; color:{}", color)}>{ format!("Validation: {}", val.message) }</div> } } else { html!{} } }
                        </div>
                        <div style="display:flex; flex-direction:column; gap:12px;">
                            <div style="border:1px solid #1f242d; background:#14181f; padding:8px; border-radius:6px;">
                                <span style="font-size:0.75rem; opacity:0.7;">{"Backtest Parameters"}</span>
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:6px;">
                                    { param_input("Symbols", state.clone(), |s,val| s.symbols = val) }
                                    { param_input("Rebalance", state.clone(), |s,val| s.rebalance = val) }
                                    { param_input("Start", state.clone(), |s,val| s.start_date = val) }
                                    { param_input("End", state.clone(), |s,val| s.end_date = val) }
                                    { param_input("Benchmark", state.clone(), |s,val| s.benchmark = val) }
                                </div>
                            </div>
                            <div style="border:1px solid #1f242d; background:#14181f; padding:8px; border-radius:6px; min-height:420px; display:flex; flex-direction:column; gap:8px;">
                                <span style="font-size:0.75rem; opacity:0.7;">{"Results"}</span>
                                <div style="display:grid; grid-template-columns:1fr; gap:8px;">
                                    <div style="background:#0f1319; border:1px solid #1d2530; border-radius:4px; padding:4px;">
                                        <div style="font-size:0.55rem; opacity:0.6;">{"Equity vs Benchmark"}</div>
                                        <canvas id="equity_chart" style="width:100%; height:180px; display:block;"></canvas>
                                    </div>
                                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                                        <div style="background:#0f1319; border:1px solid #1d2530; border-radius:4px; padding:4px;">
                                            <div style="font-size:0.55rem; opacity:0.6;">{"Drawdown"}</div>
                                            <canvas id="drawdown_chart" style="width:100%; height:120px; display:block;"></canvas>
                                        </div>
                                        <div style="background:#0f1319; border:1px solid #1d2530; border-radius:4px; padding:4px;">
                                            <div style="font-size:0.55rem; opacity:0.6;">{"Daily Returns"}</div>
                                            <canvas id="returns_chart" style="width:100%; height:120px; display:block;"></canvas>
                                        </div>
                                    </div>
                                </div>
                                { render_results(&state_view) }
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <footer style="margin-top:24px; font-size:0.55rem; opacity:0.4;">{"Prototype UI • Fast iterative strategy dev • WASM Yew minimal shell"}</footer>
        </div>
    }
}

fn param_input<F: 'static + Fn(&mut WorkbenchState, String)>(label: &str, state: UseStateHandle<WorkbenchState>, apply: F) -> Html {
    let value = match label {
        "Symbols" => state.symbols.clone(),
        "Rebalance" => state.rebalance.clone(),
        "Start" => state.start_date.clone(),
        "End" => state.end_date.clone(),
        "Benchmark" => state.benchmark.clone(),
        _ => String::new(),
    };
    html! {
        <div style="display:flex; flex-direction:column; gap:2px;">
            <label style="font-size:0.55rem; opacity:0.65;">{label}</label>
            <input value={value} oninput={Callback::from(move |e: InputEvent| {
                let input: web_sys::HtmlInputElement = e.target_unchecked_into();
                let mut s = (*state).clone();
                apply(&mut s, input.value());
                state.set(s);
            })} style="background:#0f1319; border:1px solid #1d2530; color:#c9d4e2; font-size:0.6rem; padding:4px; border-radius:4px;" />
        </div>
    }
}

fn render_results(state: &WorkbenchState) -> Html {
    if let Some(bt) = &state.backtest {
        if !bt.ok { return html!{ <div style="font-size:0.6rem; color:#e09898;">{ bt.message.clone().unwrap_or("Backtest failed".into()) }</div> }; }
        let mut lines = vec![];
        if let Some(tr) = bt.total_return { lines.push(format!("Total Return: {:.2}%", tr*100.0)); }
        if let Some(ar) = bt.annualized_return { lines.push(format!("Annualized: {:.2}%", ar*100.0)); }
        if let Some(vol) = bt.volatility { lines.push(format!("Volatility: {:.2}%", vol*100.0)); }
        if let Some(sh) = bt.sharpe_ratio { lines.push(format!("Sharpe: {:.2}", sh)); }
        if let Some(dd) = bt.max_drawdown { lines.push(format!("Max DD: {:.2}%", dd*100.0)); }
        if let Some(br) = bt.benchmark_return { lines.push(format!("Benchmark: {:.2}%", br*100.0)); }
        if let Some(a) = bt.alpha { lines.push(format!("Alpha: {:.2}", a)); }
        if let Some(b) = bt.beta { lines.push(format!("Beta: {:.2}", b)); }
        html!{ <div style="font-size:0.6rem; line-height:1.3; white-space:pre-line;">{ lines.join("\n") }</div> }
    } else { html!{ <div style="font-size:0.6rem; opacity:0.5;">{"No results yet."}</div> } }
}
