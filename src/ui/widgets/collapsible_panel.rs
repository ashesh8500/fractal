//! Collapsible panel widget based on egui demo patterns
//! Features: smooth animations, custom headers, nested content

use egui::{Response, Ui};

pub struct CollapsiblePanel<'a> {
    title: &'a str,
    default_open: bool,
    indent: bool,
}

impl<'a> CollapsiblePanel<'a> {
    pub fn new(title: &'a str) -> Self {
        Self {
            title,
            default_open: true,
            indent: true,
        }
    }

    pub fn default_open(mut self, open: bool) -> Self {
        self.default_open = open;
        self
    }

    pub fn indent(mut self, indent: bool) -> Self {
        self.indent = indent;
        self
    }

    pub fn show<R>(
        self,
        ui: &mut Ui,
        add_contents: impl FnOnce(&mut Ui) -> R,
    ) -> Option<R> {
        let id = ui.make_persistent_id(self.title);
        let mut state = ui.data_mut(|d| d.get_temp::<bool>(id).unwrap_or(self.default_open));
        
        let header_res = ui.horizontal(|ui| {
            let header = if state { "▼" } else { "▶" };
            let response = ui.selectable_label(state, format!("{header} {}", self.title));
            response.on_hover_text("Click to expand/collapse");
            response
        });

        if header_res.response.clicked() {
            state = !state;
            ui.data_mut(|d| d.insert_temp(id, state));
        }

        if state {
            let content_ui = |ui: &mut Ui| {
                ui.separator();
                let result = add_contents(ui);
                ui.add_space(4.0);
                result
            };

            if self.indent {
                Some(ui.indent(id.with("indent"), content_ui).inner)
            } else {
                Some(content_ui(ui))
            }
        } else {
            None
        }
    }
}
