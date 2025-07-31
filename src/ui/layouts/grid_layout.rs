//! Responsive grid layout based on egui demo patterns
//! Automatically adjusts columns based on available width

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
        items: impl IntoIterator<Item = impl FnOnce(&mut Ui) -> R>,
    ) {
        let available_width = ui.available_width();
        let num_columns = ((available_width / self.min_col_width) as usize)
            .max(1)
            .min(self.max_columns);
        
        let col_width =
            (available_width - self.spacing.x * (num_columns.saturating_sub(1)) as f32) / num_columns as f32;

        let items_vec: Vec<_> = items.into_iter().collect();
        let total = items_vec.len();
        if total == 0 {
            return;
        }
        let num_rows = (total + num_columns - 1) / num_columns;

        for row in 0..num_rows {
            ui.horizontal(|ui| {
                ui.spacing_mut().item_spacing = self.spacing;
                
                for col in 0..num_columns {
                    let index = row * num_columns + col;
                    if index < total {
                        let item = &items_vec[index];
                        ui.allocate_ui(Vec2::new(col_width, 0.0), |ui| {
                            item(ui);
                        });
                    } else {
                        ui.allocate_space(Vec2::new(col_width, 0.0));
                    }
                }
            });

            if row < num_rows - 1 {
                ui.add_space(self.spacing.y);
            }
        }
    }
}

impl Default for ResponsiveGrid {
    fn default() -> Self {
        Self::new()
    }
}
