//! Entry point for the Fractal portfolio application.
//! This binary launches the eframe UI using the `TemplateApp` defined in `src/app.rs`.

use fractal::TemplateApp;

#[cfg(not(target_arch = "wasm32"))]
#[tokio::main]
async fn main() -> eframe::Result<()> {
    // Initialize logging (native)
    env_logger::init();

    // Configure native window options (can be customized as needed)
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1200.0, 800.0])
            .with_min_inner_size([800.0, 600.0]),
        ..Default::default()
    };

    // Run the eframe application, constructing our `TemplateApp`.
    eframe::run_native(
        "Fractal Portfolio Tracker",
        native_options,
        Box::new(|cc| Ok(Box::new(TemplateApp::new(cc)))),
    )
}

#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen(start)]
pub async fn start() -> Result<(), JsValue> {
    let web_options = eframe::WebOptions::default();

    // Get the canvas element by id
    let window = web_sys::window().ok_or_else(|| JsValue::from_str("no window"))?;
    let document = window.document().ok_or_else(|| JsValue::from_str("no document"))?;
    let el = document
        .get_element_by_id("the_canvas_id")
        .ok_or_else(|| JsValue::from_str("canvas with id 'the_canvas_id' not found"))?;
    let canvas: web_sys::HtmlCanvasElement = el
        .dyn_into::<web_sys::HtmlCanvasElement>()
        .map_err(|_| JsValue::from_str("element is not a canvas"))?;

    eframe::WebRunner::new()
        .start(
            canvas,
            web_options,
            Box::new(|cc| Ok(Box::new(TemplateApp::new(cc)))),
        )
        .await
        .map_err(|e| JsValue::from_str(&format!("eframe web start error: {:?}", e)))
}

#[cfg(target_arch = "wasm32")]
fn main() {
    wasm_bindgen_futures::spawn_local(async {
        let _ = start().await;
    });
}
