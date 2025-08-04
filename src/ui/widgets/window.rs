use egui::{self, Ui};

/// A small helper wrapper to standardize windows across the app, inspired by egui demo patterns.
/// - Resizable by default
/// - Optional vertical/horizontal scroll (off by default to avoid double scrollbars)
/// - Default size/width controls
pub struct WindowPanel<'a> {
    id: egui::Id,
    title: &'a str,
    default_size: Option<egui::Vec2>,
    default_width: Option<f32>,
    resizable: bool,
    scroll: egui::Vec2b,
    open: &'a mut bool,
}

impl<'a> WindowPanel<'a> {
    pub fn new(id: impl Into<egui::Id>, title: &'a str, open: &'a mut bool) -> Self {
        Self {
            id: id.into(),
            title,
            default_size: None,
            default_width: None,
            resizable: true,
            scroll: egui::Vec2b::FALSE, // keep window itself non-scrolling; content controls scrolling
            open,
        }
    }

    pub fn default_size(mut self, size: [f32; 2]) -> Self {
        self.default_size = Some(egui::Vec2::new(size[0], size[1]));
        self
    }

    pub fn default_width(mut self, width: f32) -> Self {
        self.default_width = Some(width);
        self
    }

    pub fn resizable(mut self, resizable: bool) -> Self {
        self.resizable = resizable;
        self
    }

    /// Enable scroll on the window itself (not commonly recommended if inner content manages scroll).
    pub fn scroll(mut self, horizontal: bool, vertical: bool) -> Self {
        self.scroll = egui::Vec2b::new(horizontal, vertical);
        self
    }

    pub fn show<R>(self, ctx: &egui::Context, add_contents: impl FnOnce(&mut Ui) -> R) -> Option<R> {
        if !*self.open {
            return None;
        }

        let mut window = egui::Window::new(self.title)
            .id(self.id)
            .resizable(self.resizable)
            .scroll(self.scroll);

        if let Some(size) = self.default_size {
            window = window.default_size(size);
        }
        if let Some(w) = self.default_width {
            window = window.default_width(w);
        }

        let mut out = None;
        window.open(self.open).show(ctx, |ui| {
            out = Some(add_contents(ui));
        });
        out
    }
}
