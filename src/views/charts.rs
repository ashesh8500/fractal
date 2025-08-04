use egui::{Color32, Stroke};
use egui_plot::{Plot, PlotPoints, Series};
use rand::Rng;

pub fn show_charts(ctx: &egui::Context) {
    egui::CentralPanel::default().show(ctx, |ui| {
        ui.heading("Candlestick Chart Example");
        
        let mut plot = Plot::new("candle_chart")
            .width(600.0)
            .height(400.0)
            .x_axis_formatter(|value, _range| format!("{:.0}", value))
            .y_axis_formatter(|value, _range| format!("{:.2}", value));
            
        // Generate some sample data
        let mut points: Vec<[f64; 2]> = Vec::new();
        let mut rng = rand::thread_rng();
        
        for i in 0..100 {
            let x = i as f64;
            let y = 50.0 + (i as f64 * 0.1).sin() * 10.0 + rng.gen_range(-5.0..5.0);
            points.push([x, y]);
        }
        
        plot = plot.data_series(Series::new(PlotPoints::from(points))
            .name("Data Series")
            .color(Color32::from_rgb(
                (rng.gen::<f32>() * 255.0) as u8,
                (rng.gen::<f32>() * 255.0) as u8,
                (rng.gen::<f32>() * 255.0) as u8,
            ))
            .stroke(Stroke::new(2.0, Color32::from_rgb(
                (rng.gen::<f32>() * 255.0) as u8,
                (rng.gen::<f32>() * 255.0) as u8,
                (rng.gen::<f32>() * 255.0) as u8,
            ))));
            
        ui.add(plot);
    });
}
