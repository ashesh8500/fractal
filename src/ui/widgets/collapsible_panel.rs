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
    ) -> (Response, Option<R>) {
        let id = ui.id().with(self.title);
        let mut state = ui.data_mut(|d| d.get_persisted::<bool>(id)).unwrap_or(self.default_open);

        let header_text = if state { "▼" } else { "▶" };
        let label = format!("{header_text} {}", self.title);
        let response = ui.selectable_label(state, label);
        response.clone().on_hover_text("Click to expand/collapse");

        if response.clicked() {
            state = !state;
            ui.data_mut(|d| d.insert_persisted(id, state));
        }

        let mut out = None;
        if state {
            if self.indent {
                ui.indent(id.with("indent"), |ui| {
                    ui.separator();
                    out = Some(add_contents(ui));
                    ui.add_space(4.0);
                });
            } else {
                ui.separator();
                out = Some(add_contents(ui));
                ui.add_space(4.0);
            }
        }

        (response, out)
    }
}
