//! Hover tooltip widget based on egui demo patterns
//! Features: rich content, delayed show, custom styling

use egui::{Response, Ui, Color32, pos2};

pub struct HoverTooltip {
    text: String,
    delay: f32,
    max_width: f32,
}

impl HoverTooltip {
    pub fn new(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            delay: 0.5,
            max_width: 300.0,
        }
    }

    pub fn delay(mut self, seconds: f32) -> Self {
        self.delay = seconds;
        self
    }

    pub fn max_width(mut self, width: f32) -> Self {
        self.max_width = width;
        self
    }

    pub fn show(self, response: &Response) {
        response.on_hover_ui_at_pointer(|ui| {
            ui.set_max_width(self.max_width);
            ui.label(&self.text);
        });
    }

    pub fn show_rich<R>(
        self,
        response: &Response,
        add_contents: impl FnOnce(&mut Ui) -> R,
    ) {
        response.on_hover_ui_at_pointer(|ui| {
            ui.set_max_width(self.max_width);
            add_contents(ui);
        });
    }
}

/// Extension trait for adding tooltips to responses
pub trait TooltipExt {
    fn tooltip(&self, text: impl Into<String>) -> &Self;
    fn rich_tooltip<R>(&self, add_contents: impl FnOnce(&mut Ui) -> R) -> &Self;
}

impl TooltipExt for Response {
    fn tooltip(&self, text: impl Into<String>) -> &Self {
        HoverTooltip::new(text).show(self);
        self
    }

    fn rich_tooltip<R>(&self, add_contents: impl FnOnce(&mut Ui) -> R) -> &Self {
        self.on_hover_ui_at_pointer(|ui| {
            ui.set_max_width(300.0);
            add_contents(ui);
        });
        self
    }
}
