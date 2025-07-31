//! Enhanced scrollable table widget based on egui demo patterns
//! Features: striped rows, selection, proper scrolling, tooltips

use egui::{Color32, Response, Ui, Widget};
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
            selected_rows,
            clickable,
        } = self;

        egui::ScrollArea::vertical()
            .id_source(id)
            .max_height(max_height)
            .show(ui, |ui| {
                egui::Grid::new(id.with("grid"))
                    .striped(striped)
                    .num_columns(headers.len())
                    .min_col_width(50.0)
                    .show(ui, |ui| {
                        // Headers
                        for header in &headers {
                            ui.strong(*header);
                        }
                        ui.end_row();

                        // Data rows
                        for (row_idx, row_data) in rows.iter().enumerate() {
                            let is_selected = selected_rows.contains(&row_idx);
                            
                            // Create a sense for the entire row if clickable
                            let row_rect = ui.max_rect();
                            let row_id = id.with(("row", row_idx));
                            let row_response = if clickable {
                                ui.interact(row_rect, row_id, egui::Sense::click())
                            } else {
                                ui.interact(row_rect, row_id, egui::Sense::hover())
                            };

                            // Highlight selected rows
                            if is_selected {
                                ui.painter().rect_filled(
                                    row_rect,
                                    0.0,
                                    ui.visuals().selection.bg_fill,
                                );
                            }

                            // Hover effect
                            if row_response.hovered() && !is_selected {
                                ui.painter().rect_filled(
                                    row_rect,
                                    0.0,
                                    ui.visuals().widgets.hovered.bg_fill,
                                );
                            }

                            // Handle row click
                            if clickable && row_response.clicked() {
                                if selected_rows.contains(&row_idx) {
                                    selected_rows.remove(&row_idx);
                                } else {
                                    selected_rows.insert(row_idx);
                                }
                            }

                            // Render cells
                            for (col_idx, cell) in row_data.iter().enumerate() {
                                let cell_response = ui.label(cell);
                                
                                // Add tooltip for truncated text
                                if cell_response.truncated {
                                    cell_response.on_hover_text(cell);
                                }
                            }
                            ui.end_row();
                        }
                    })
            })
            .response
    }
}
