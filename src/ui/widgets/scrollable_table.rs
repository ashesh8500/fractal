use egui::{Response, Ui, Widget};
use std::collections::HashSet;

pub struct ScrollableTable<'a> {
    id: egui::Id,
    headers: Vec<&'a str>,
    rows: Vec<Vec<String>>,
    striped: bool,
    max_height: f32,
    selected_rows: HashSet<usize>,
    clickable: bool,
    on_select: Option<Box<dyn FnMut(usize, bool) + 'a>>,
}

impl<'a> ScrollableTable<'a> {
    pub fn new(id: impl Into<egui::Id>, headers: Vec<&'a str>) -> Self {
        Self {
            id: id.into(),
            headers,
            rows: Vec::new(),
            striped: true,
            max_height: 300.0,
            selected_rows: HashSet::new(),
            clickable: true,
            on_select: None,
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

    pub fn clickable(mut self, clickable: bool) -> Self {
        self.clickable = clickable;
        self
    }

    pub fn on_select(mut self, f: impl FnMut(usize, bool) + 'a) -> Self {
        self.on_select = Some(Box::new(f));
        self
    }

    fn header_ui(&self, ui: &mut Ui) {
        egui::Grid::new(self.id.with("header"))
            .num_columns(self.headers.len())
            .striped(false)
            .show(ui, |ui| {
                for h in &self.headers {
                    ui.strong(*h);
                }
                ui.end_row();
            });
        ui.separator();
    }

    fn body_ui(&mut self, ui: &mut Ui) {
        let row_height = ui.text_style_height(&egui::TextStyle::Body) + 8.0;

        egui::ScrollArea::vertical()
            .id_salt(self.id)
            .max_height(self.max_height)
            .show(ui, |ui| {
                for (row_index, row) in self.rows.iter().enumerate() {
                    let is_selected = self.selected_rows.contains(&row_index);

                    let rect = ui.allocate_rect(
                        egui::Rect::from_min_size(
                            ui.cursor().min,
                            egui::vec2(ui.available_width(), row_height),
                        ),
                        egui::Sense::click(),
                    ).rect;

                    // Backgrounds
                    if self.striped && row_index % 2 == 0 {
                        ui.painter().rect_filled(rect, egui::CornerRadius::ZERO, ui.visuals().faint_bg_color);
                    }
                    if is_selected {
                        ui.painter().rect_filled(rect, egui::CornerRadius::ZERO, ui.visuals().selection.bg_fill);
                    }

                    // Row content
                    ui.allocate_ui_at_rect(rect, |ui| {
                        ui.horizontal(|ui| {
                            for (i, cell) in row.iter().enumerate() {
                                let _cell_resp = ui.label(cell);
                                if i < row.len() - 1 {
                                    ui.add_space(16.0);
                                }
                            }
                        });
                    });

                    // Interact and toggle
                    let resp = ui.interact(rect, self.id.with(("row", row_index)), egui::Sense::click());
                    if self.clickable && resp.clicked() {
                        let now_selected = if is_selected {
                            self.selected_rows.remove(&row_index);
                            false
                        } else {
                            self.selected_rows.insert(row_index);
                            true
                        };
                        if let Some(on_select) = &mut self.on_select {
                            on_select(row_index, now_selected);
                        }
                    }

                    // Ensure spacing between rows
                    ui.add_space(2.0);
                }
            });
    }

    pub fn show(&mut self, ui: &mut Ui) -> Response {
        let (rect, response) = ui.allocate_exact_size(
            egui::vec2(ui.available_width(), self.max_height + 48.0),
            egui::Sense::hover(),
        );

        if ui.is_rect_visible(rect) {
            ui.allocate_ui_at_rect(rect, |ui| {
                self.header_ui(ui);
                self.body_ui(ui);
            });
        }

        response
    }
}

impl<'a> Widget for ScrollableTable<'a> {
    fn ui(mut self, ui: &mut Ui) -> Response {
        self.show(ui)
    }
}
