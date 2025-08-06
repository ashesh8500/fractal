//! Entry point for the Fractal portfolio application.
//! This binary launches the eframe UI using the `TemplateApp` defined in `src/app.rs`.

mod app;

fn main() -> eframe::Result<()> {
    // Configure native window options (can be customized as needed)
    let native_options = eframe::NativeOptions::default();

    // Run the eframe application, constructing our `TemplateApp`.
    eframe::run_native(
        "Fractal Portfolio Tracker",
        native_options,
        Box::new(|cc| Box::new(app::TemplateApp::new(cc))),
    )
}
