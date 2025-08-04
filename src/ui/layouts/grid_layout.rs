use egui::{Ui, Vec2};

pub struct ResponsiveGrid {
    min_col_width: f32,
    spacing: Vec2,
    max_columns: usize,
}

impl ResponsiveGrid {
    pub fn new() -> Self {
        Self {
            min_col_width: 200.0,
            spacing: Vec2::new(8.0, 8.0),
            max_columns: 4,
        }
    }

    pub fn min_col_width(mut self, width: f32) -> Self {
        self.min_col_width = width;
        self
    }

    pub fn spacing(mut self, spacing: Vec2) -> Self {
        self.spacing = spacing;
        self
    }

    pub fn max_columns(mut self, max: usize) -> Self {
        self.max_columns = max;
        self
    }

    pub fn show<R>(
        self,
        ui: &mut Ui,
        items: impl IntoIterator<Item = impl FnMut(&mut Ui) -> R>,
    ) {
        let available_width = ui.available_width();
        let columns = (available_width / self.min_col_width).floor().max(1.0) as usize;
        let columns = columns.min(self.max_columns).max(1);

        let mut items_iter = items.into_iter();

        loop {
            let mut filled_any = false;
            ui.horizontal_wrapped(|ui| {
                ui.spacing_mut().item_spacing = self.spacing;
                for _ in 0..columns {
                    if let Some(mut item) = items_iter.next() {
                        filled_any = true;
                        ui.allocate_ui(Vec2::new(self.min_col_width, 0.0), |ui| {
                            item(ui);
                        });
                    }
                }
            });
            if !filled_any {
                break;
            }
            ui.add_space(self.spacing.y);
        }
    }
}

impl Default for ResponsiveGrid {
    fn default() -> Self {
        Self::new()
    }
}
