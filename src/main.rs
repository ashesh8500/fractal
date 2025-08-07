//! Entry point for the Fractal portfolio application.
//! This binary launches the eframe UI using the `TemplateApp` defined in `src/app.rs`.

use fractal::TemplateApp;

#[tokio::main]
async fn main() -> eframe::Result<()> {
    // Initialize logging
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
