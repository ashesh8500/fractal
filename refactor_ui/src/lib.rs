use wasm_bindgen::prelude::*;

mod strategy_workbench;
pub mod charts;

#[wasm_bindgen(start)]
pub fn run() {
    console_error_panic_hook::set_once();
    yew::Renderer::<strategy_workbench::StrategyWorkbenchApp>::new().render();
}
