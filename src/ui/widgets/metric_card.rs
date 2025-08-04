use egui::{Color32, Response, Ui, Widget, Vec2, Frame, CornerRadius};

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
            // Take only the values we need from style/visuals to avoid holding an immutable borrow of `ui` across a mutable call.
            let style = ui.style().clone();
            let interact_visuals = style.interact(&response);
            let base_fill = self
                .color
                .unwrap_or(style.visuals.widgets.noninteractive.bg_fill);
            let bg_color = if response.hovered() {
                base_fill.gamma_multiply(0.9)
            } else {
                base_fill
            };
            let frame_stroke = interact_visuals.bg_stroke; // Copy; Stroke is Copy

            // Background frame using modern API (now safe: we don't hold `&ui` immutably)
            Frame::new()
                .fill(bg_color)
                .stroke(frame_stroke)
                .corner_radius(CornerRadius::same(8)) // u8 radius
                .show(ui, |_inner_ui| {});

            // Text colors
            let text_color = if self.color.is_some() {
                Color32::WHITE
            } else {
                ui.visuals().text_color()
            };

            let left_padding = 16.0;
            let top_padding = 12.0;
            let spacing = 6.0;

            let mut cursor_y = rect.top() + top_padding;

            // Icon (if any)
            if let Some(icon) = self.icon {
                let icon_pos = egui::pos2(rect.left() + left_padding, cursor_y);
                ui.painter().text(
                    icon_pos,
                    egui::Align2::LEFT_TOP,
                    icon,
                    egui::FontId::proportional(20.0),
                    text_color,
                );
                cursor_y += 22.0 + spacing;
            }

            // Label (use plain &str with font/color)
            {
                let pos = egui::pos2(rect.left() + left_padding, cursor_y);
                ui.painter().text(
                    pos,
                    egui::Align2::LEFT_TOP,
                    &self.label,
                    egui::FontId::proportional(14.0),
                    text_color.gamma_multiply(0.8),
                );
                cursor_y += 18.0 + spacing;
            }

            // Value (use plain &str with larger font/color)
            {
                let pos = egui::pos2(rect.left() + left_padding, cursor_y);
                ui.painter().text(
                    pos,
                    egui::Align2::LEFT_TOP,
                    &self.value,
                    egui::FontId::proportional(22.0),
                    text_color,
                );
            }

            // Border stroke with modern signature
            // Acquire a color without borrowing `ui` immutably across the call:
            let stroke_color = ui
                .visuals()
                .widgets
                .noninteractive
                .bg_stroke
                .color
                .gamma_multiply(0.2);
            ui.painter().rect_stroke(
                rect,
                CornerRadius::same(8),
                egui::Stroke::new(1.0, stroke_color),
                egui::StrokeKind::Outside,
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
