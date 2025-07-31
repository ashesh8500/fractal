//! Enhanced scrollable table widget based on egui demo patterns
//! Features: striped rows, selection, proper scrolling, tooltips

use egui::{Response, Ui, Widget};
use std::collections::HashSet;

pub struct ScrollableTable<'a> {
    id: egui::Id,
    headers: Vec<&'a str>,
    rows: Vec<Vec<String>>,
    striped: bool,
    max_height: f32,
    selected_rows: &'a mut HashSet<usize>,
    clickable: bool,
}

impl<'a> ScrollableTable<'a> {
    pub fn new(id: impl Into<egui::Id>, headers: Vec<&'a str>) -> Self {
        Self {
            id: id.into(),
            headers,
            rows: Vec::new(),
            striped: true,
            max_height: 300.0,
            selected_rows: &mut HashSet::new(),
            clickable: true,
        }
    }

    pub fn rows(mut self, rows: Vec<Vec<String>>) -> Self {
        self.rows = rows;
        self
    }

    pub fn striped(mut self, striped: bool) -> Self {
        self.striped = striped;
        self
    }

    pub fn max_height(mut self, height: f32) -> Self {
        self.max_height = height;
        self
    }

    pub fn selected_rows(mut self, selected: &'a mut HashSet<usize>) -> Self {
        self.selected_rows = selected;
        self
    }

    pub fn clickable(mut self, clickable: bool) -> Self {
        self.clickable = clickable;
        self
    }
}

impl<'a> Widget for ScrollableTable<'a> {
    fn ui(self, ui: &mut Ui) -> Response {
        let Self {
            id,
            headers,
            rows,
            striped,
            max_height,
            mut selected_rows,
            clickable,
        } = self;

        egui::ScrollArea::vertical()
            .id_source(id)
            .max_height(max_height)
            .show(ui, |ui| {
                let grid = egui::Grid::new(id.with("grid"))
                    .striped(striped)
                    .num_columns(headers.len())
                    .min_col_width(50.0);

                grid.show(ui, |ui| {
                    // Headers
                    for header in &headers {
                        ui.strong(*header);
                    }
                    ui.end_row();

                    // Data rows
                    let text_height = egui::TextStyle::Body
                        .resolve(ui.style())
                        .size
                        .max(ui.spacing().interact_size.y);

                    for (row_idx, row_data) in rows.iter().enumerate() {
                        // Start row layout: allocate a rect per row using a dummy full-width area.
                        let row_start = ui.cursor();
                        // Render cells, gathering widest height automatically:
                        for (col_idx, cell) in row_data.iter().enumerate() {
                            let cell_response = ui.label(cell);
                            if cell_response.truncated {
                                cell_response.on_hover_text(cell);
                            }
                            // After last column in row, end row:
                            if col_idx == row_data.len() - 1 {
                                ui.end_row();
                            }
                        }
                        // Now retrieve the row rect by combining from row_start to current:
                        let row_rect = egui::Rect::from_min_max(row_start.min, ui.cursor().min);

                        // Interaction overlay for the row:
                        let row_id = id.with(("row", row_idx));
                        let sense = if clickable {
                            egui::Sense::click()
                        } else {
                            egui::Sense::hover()
                        };
                        let response = ui.interact(row_rect, row_id, sense);

                        // Selection toggle
                        if clickable && response.clicked() {
                            if selected_rows.contains(&row_idx) {
                                selected_rows.remove(&row_idx);
                            } else {
                                selected_rows.insert(row_idx);
                            }
                        }

                        // Hover and selection paints
                        if selected_rows.contains(&row_idx) {
                            ui.painter().rect_filled(
                                row_rect,
                                0.0,
                                ui.visuals().selection.bg_fill,
                            );
                        } else if response.hovered() {
                            ui.painter().rect_filled(
                                row_rect,
                                0.0,
                                ui.visuals().widgets.hovered.bg_fill,
                            );
                        }

                        // Ensure a minimum row height:
                        let current_height = row_rect.height();
                        if current_height < text_height {
                            ui.add_space(text_height - current_height);
                        }
                    }
                });
            })
            .response
    }
}
