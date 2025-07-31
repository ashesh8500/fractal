//! Elegant metric card widget based on egui demo patterns
//! Features: colored backgrounds, icons, hover effects

use egui::{Color32, Response, Ui, Widget, Vec2, Rounding, Frame};

pub struct MetricCard {
    label: String,
    value: String,
    icon: Option<&'static str>,
    color: Option<Color32>,
}

impl MetricCard {
    pub fn new(label: impl Into<String>, value: impl Into<String>) -> Self {
        Self {
            label: label.into(),
            value: value.into(),
            icon: None,
            color: None,
        }
    }

    pub fn icon(mut self, icon: &'static str) -> Self {
        self.icon = Some(icon);
        self
    }

    pub fn color(mut self, color: Color32) -> Self {
        self.color = Some(color);
        self
    }

    pub fn show(self, ui: &mut Ui) -> Response {
        let desired_size = Vec2::new(ui.available_width(), 72.0);
        let (rect, response) = ui.allocate_exact_size(desired_size, egui::Sense::hover());

        if ui.is_rect_visible(rect) {
            let visuals = ui.style().interact(&response);
            let base = self.color.unwrap_or(ui.visuals().widgets.noninteractive.bg_fill);
            let bg_color = if response.hovered() {
                base.gamma_multiply(0.9)
            } else {
                base.gamma_multiply(0.8)
            };

            // Background frame similar to demo style
            Frame::none()
                .fill(bg_color)
                .stroke(visuals.bg_stroke)
                .rounding(egui::style::CornerRadius::same(8.0))
                .show(ui, |_| {});

            // Use painter to draw within rect
            let text_color = if self.color.is_some() {
                Color32::WHITE
            } else {
                ui.visuals().text_color()
            };

            let margin = 12.0;
            let content_rect = rect.shrink(margin);

            // Draw icon if present
            let mut text_pos = content_rect.left_top();
            if let Some(icon) = self.icon {
                ui.painter().text(
                    text_pos,
                    egui::Align2::LEFT_TOP,
                    icon,
                    egui::FontId::proportional(22.0),
                    text_color,
                );
                text_pos.x += 30.0;
            }

            // Draw label
            ui.painter().text(
                text_pos,
                egui::Align2::LEFT_TOP,
                &self.label,
                egui::FontId::proportional(14.0),
                text_color.gamma_multiply(0.8),
            );

            // Draw value
            ui.painter().text(
                content_rect.left_bottom() + Vec2::new(0.0, -6.0),
                egui::Align2::LEFT_BOTTOM,
                &self.value,
                egui::FontId::proportional(22.0).strong(),
                text_color,
            );

            // Subtle outline
            ui.painter().rect_stroke(
                rect,
                Rounding::same(8.0),
                egui::Stroke::new(1.0, visuals.bg_stroke.color.gamma_multiply(0.2)),
            );
        }

        response
    }
}

impl Widget for MetricCard {
    fn ui(self, ui: &mut Ui) -> Response {
        self.show(ui)
    }
}
