

└── crates
    └── egui_demo_lib
        └── src
            └── demo
                ├── about.rs
                ├── code_editor.rs
                ├── code_example.rs
                ├── dancing_strings.rs
                ├── demo_app_windows.rs
                ├── drag_and_drop.rs
                ├── extra_viewport.rs
                ├── font_book.rs
                ├── frame_demo.rs
                ├── highlighting.rs
                ├── interactive_container.rs
                ├── misc_demo_window.rs
                ├── mod.rs
                ├── modals.rs
                ├── multi_touch.rs
                ├── paint_bezier.rs
                ├── painting.rs
                ├── panels.rs
                ├── password.rs
                ├── popups.rs
                ├── scene.rs
                ├── screenshot.rs
                ├── scrolling.rs
                ├── sliders.rs
                ├── strip_demo.rs
                ├── table_demo.rs
                ├── tests
                    ├── clipboard_test.rs
                    ├── cursor_test.rs
                    ├── grid_test.rs
                    ├── id_test.rs
                    ├── input_event_history.rs
                    ├── input_test.rs
                    ├── layout_test.rs
                    ├── manual_layout_test.rs
                    ├── mod.rs
                    ├── svg_test.rs
                    ├── tessellation_test.rs
                    └── window_resize_test.rs
                ├── text_edit.rs
                ├── text_layout.rs
                ├── toggle_switch.rs
                ├── tooltips.rs
                ├── undo_redo.rs
                ├── widget_gallery.rs
                └── window_options.rs


/crates/egui_demo_lib/src/demo/about.rs:
--------------------------------------------------------------------------------
  1 | #[derive(Default)]
  2 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  3 | #[cfg_attr(feature = "serde", serde(default))]
  4 | pub struct About {}
  5 | 
  6 | impl crate::Demo for About {
  7 |     fn name(&self) -> &'static str {
  8 |         "About egui"
  9 |     }
 10 | 
 11 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 12 |         egui::Window::new(self.name())
 13 |             .default_width(320.0)
 14 |             .default_height(480.0)
 15 |             .open(open)
 16 |             .resizable([true, false])
 17 |             .scroll(false)
 18 |             .show(ctx, |ui| {
 19 |                 use crate::View as _;
 20 |                 self.ui(ui);
 21 |             });
 22 |     }
 23 | }
 24 | 
 25 | impl crate::View for About {
 26 |     fn ui(&mut self, ui: &mut egui::Ui) {
 27 |         use egui::special_emojis::{OS_APPLE, OS_LINUX, OS_WINDOWS};
 28 | 
 29 |         ui.heading("egui");
 30 |         ui.label(format!(
 31 |             "egui is an immediate mode GUI library written in Rust. egui runs both on the web and natively on {}{}{}. \
 32 |             On the web it is compiled to WebAssembly and rendered with WebGL.{}",
 33 |             OS_APPLE, OS_LINUX, OS_WINDOWS,
 34 |             if cfg!(target_arch = "wasm32") {
 35 |                 " Everything you see is rendered as textured triangles. There is no DOM, HTML, JS or CSS. Just Rust."
 36 |             } else {""}
 37 |         ));
 38 |         ui.label("egui is designed to be easy to use, portable, and fast.");
 39 | 
 40 |         ui.add_space(12.0);
 41 | 
 42 |         ui.heading("Immediate mode");
 43 |         about_immediate_mode(ui);
 44 | 
 45 |         ui.add_space(12.0);
 46 | 
 47 |         ui.heading("Links");
 48 |         links(ui);
 49 | 
 50 |         ui.add_space(12.0);
 51 | 
 52 |         ui.horizontal_wrapped(|ui| {
 53 |             ui.spacing_mut().item_spacing.x = 0.0;
 54 |             ui.label("egui development is sponsored by ");
 55 |             ui.hyperlink_to("Rerun.io", "https://www.rerun.io/");
 56 |             ui.label(", a startup building an SDK for visualizing streams of multimodal data. ");
 57 |             ui.label("For an example of a real-world egui app, see ");
 58 |             ui.hyperlink_to("rerun.io/viewer", "https://www.rerun.io/viewer");
 59 |             ui.label(" (runs in your browser).");
 60 |         });
 61 | 
 62 |         ui.add_space(12.0);
 63 | 
 64 |         ui.vertical_centered(|ui| {
 65 |             ui.add(crate::egui_github_link_file!());
 66 |         });
 67 |     }
 68 | }
 69 | 
 70 | fn about_immediate_mode(ui: &mut egui::Ui) {
 71 |     ui.style_mut().spacing.interact_size.y = 0.0; // hack to make `horizontal_wrapped` work better with text.
 72 | 
 73 |     ui.horizontal_wrapped(|ui| {
 74 |             ui.spacing_mut().item_spacing.x = 0.0;
 75 |             ui.label("Immediate mode is a GUI paradigm that lets you create a GUI with less code and simpler control flow. For example, this is how you create a ");
 76 |             let _ = ui.small_button("button");
 77 |             ui.label(" in egui:");
 78 |         });
 79 | 
 80 |     ui.add_space(8.0);
 81 |     crate::rust_view_ui(
 82 |         ui,
 83 |         r#"
 84 |   if ui.button("Save").clicked() {
 85 |       my_state.save();
 86 |   }"#
 87 |         .trim_start_matches('\n'),
 88 |     );
 89 |     ui.add_space(8.0);
 90 | 
 91 |     ui.horizontal_wrapped(|ui| {
 92 |         ui.spacing_mut().item_spacing.x = 0.0;
 93 |         ui.label("There are no callbacks or messages, and no button state to store. ");
 94 |         ui.label("Read more about immediate mode ");
 95 |         ui.hyperlink_to("here", "https://github.com/emilk/egui#why-immediate-mode");
 96 |         ui.label(".");
 97 |     });
 98 | }
 99 | 
100 | fn links(ui: &mut egui::Ui) {
101 |     use egui::special_emojis::GITHUB;
102 |     ui.hyperlink_to(
103 |         format!("{GITHUB} github.com/emilk/egui"),
104 |         "https://github.com/emilk/egui",
105 |     );
106 |     ui.hyperlink_to(
107 |         "@ernerfeldt.bsky.social",
108 |         "https://bsky.app/profile/ernerfeldt.bsky.social",
109 |     );
110 |     ui.hyperlink_to("📓 egui documentation", "https://docs.rs/egui/");
111 | }
112 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/code_editor.rs:
--------------------------------------------------------------------------------
  1 | // ----------------------------------------------------------------------------
  2 | 
  3 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  4 | #[cfg_attr(feature = "serde", serde(default))]
  5 | pub struct CodeEditor {
  6 |     language: String,
  7 |     code: String,
  8 | }
  9 | 
 10 | impl Default for CodeEditor {
 11 |     fn default() -> Self {
 12 |         Self {
 13 |             language: "rs".into(),
 14 |             code: "// A very simple example\n\
 15 | fn main() {\n\
 16 | \tprintln!(\"Hello world!\");\n\
 17 | }\n\
 18 | "
 19 |             .into(),
 20 |         }
 21 |     }
 22 | }
 23 | 
 24 | impl crate::Demo for CodeEditor {
 25 |     fn name(&self) -> &'static str {
 26 |         "🖮 Code Editor"
 27 |     }
 28 | 
 29 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 30 |         use crate::View as _;
 31 |         egui::Window::new(self.name())
 32 |             .open(open)
 33 |             .default_height(500.0)
 34 |             .show(ctx, |ui| self.ui(ui));
 35 |     }
 36 | }
 37 | 
 38 | impl crate::View for CodeEditor {
 39 |     fn ui(&mut self, ui: &mut egui::Ui) {
 40 |         let Self { language, code } = self;
 41 | 
 42 |         ui.horizontal(|ui| {
 43 |             ui.set_height(0.0);
 44 |             ui.label("An example of syntax highlighting in a TextEdit.");
 45 |             ui.add(crate::egui_github_link_file!());
 46 |         });
 47 | 
 48 |         if cfg!(feature = "syntect") {
 49 |             ui.horizontal(|ui| {
 50 |                 ui.label("Language:");
 51 |                 ui.text_edit_singleline(language);
 52 |             });
 53 |             ui.horizontal_wrapped(|ui| {
 54 |                 ui.spacing_mut().item_spacing.x = 0.0;
 55 |                 ui.label("Syntax highlighting powered by ");
 56 |                 ui.hyperlink_to("syntect", "https://github.com/trishume/syntect");
 57 |                 ui.label(".");
 58 |             });
 59 |         } else {
 60 |             ui.horizontal_wrapped(|ui| {
 61 |                 ui.spacing_mut().item_spacing.x = 0.0;
 62 |                 ui.label("Compile the demo with the ");
 63 |                 ui.code("syntax_highlighting");
 64 |                 ui.label(" feature to enable more accurate syntax highlighting using ");
 65 |                 ui.hyperlink_to("syntect", "https://github.com/trishume/syntect");
 66 |                 ui.label(".");
 67 |             });
 68 |         }
 69 | 
 70 |         let mut theme =
 71 |             egui_extras::syntax_highlighting::CodeTheme::from_memory(ui.ctx(), ui.style());
 72 |         ui.collapsing("Theme", |ui| {
 73 |             ui.group(|ui| {
 74 |                 theme.ui(ui);
 75 |                 theme.clone().store_in_memory(ui.ctx());
 76 |             });
 77 |         });
 78 | 
 79 |         let mut layouter = |ui: &egui::Ui, buf: &dyn egui::TextBuffer, wrap_width: f32| {
 80 |             let mut layout_job = egui_extras::syntax_highlighting::highlight(
 81 |                 ui.ctx(),
 82 |                 ui.style(),
 83 |                 &theme,
 84 |                 buf.as_str(),
 85 |                 language,
 86 |             );
 87 |             layout_job.wrap.max_width = wrap_width;
 88 |             ui.fonts(|f| f.layout_job(layout_job))
 89 |         };
 90 | 
 91 |         egui::ScrollArea::vertical().show(ui, |ui| {
 92 |             ui.add(
 93 |                 egui::TextEdit::multiline(code)
 94 |                     .font(egui::TextStyle::Monospace) // for cursor height
 95 |                     .code_editor()
 96 |                     .desired_rows(10)
 97 |                     .lock_focus(true)
 98 |                     .desired_width(f32::INFINITY)
 99 |                     .layouter(&mut layouter),
100 |             );
101 |         });
102 |     }
103 | }
104 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/code_example.rs:
--------------------------------------------------------------------------------
  1 | #[derive(Debug)]
  2 | pub struct CodeExample {
  3 |     name: String,
  4 |     age: u32,
  5 | }
  6 | 
  7 | impl Default for CodeExample {
  8 |     fn default() -> Self {
  9 |         Self {
 10 |             name: "Arthur".to_owned(),
 11 |             age: 42,
 12 |         }
 13 |     }
 14 | }
 15 | 
 16 | impl CodeExample {
 17 |     fn samples_in_grid(&mut self, ui: &mut egui::Ui) {
 18 |         // Note: we keep the code narrow so that the example fits on a mobile screen.
 19 | 
 20 |         let Self { name, age } = self; // for brevity later on
 21 | 
 22 |         show_code(ui, r#"ui.heading("Example");"#);
 23 |         ui.heading("Example");
 24 |         ui.end_row();
 25 | 
 26 |         show_code(
 27 |             ui,
 28 |             r#"
 29 |             ui.horizontal(|ui| {
 30 |                 ui.label("Name");
 31 |                 ui.text_edit_singleline(name);
 32 |             });"#,
 33 |         );
 34 |         // Putting things on the same line using ui.horizontal:
 35 |         ui.horizontal(|ui| {
 36 |             ui.label("Name");
 37 |             ui.text_edit_singleline(name);
 38 |         });
 39 |         ui.end_row();
 40 | 
 41 |         show_code(
 42 |             ui,
 43 |             r#"
 44 |             ui.add(
 45 |                 egui::DragValue::new(age)
 46 |                     .range(0..=120)
 47 |                     .suffix(" years"),
 48 |             );"#,
 49 |         );
 50 |         ui.add(egui::DragValue::new(age).range(0..=120).suffix(" years"));
 51 |         ui.end_row();
 52 | 
 53 |         show_code(
 54 |             ui,
 55 |             r#"
 56 |             if ui.button("Increment").clicked() {
 57 |                 *age += 1;
 58 |             }"#,
 59 |         );
 60 |         if ui.button("Increment").clicked() {
 61 |             *age += 1;
 62 |         }
 63 |         ui.end_row();
 64 | 
 65 |         #[expect(clippy::literal_string_with_formatting_args)]
 66 |         show_code(ui, r#"ui.label(format!("{name} is {age}"));"#);
 67 |         ui.label(format!("{name} is {age}"));
 68 |         ui.end_row();
 69 |     }
 70 | 
 71 |     fn code(&mut self, ui: &mut egui::Ui) {
 72 |         show_code(
 73 |             ui,
 74 |             r"
 75 | pub struct CodeExample {
 76 |     name: String,
 77 |     age: u32,
 78 | }
 79 | 
 80 | impl CodeExample {
 81 |     fn ui(&mut self, ui: &mut egui::Ui) {
 82 |         // Saves us from writing `&mut self.name` etc
 83 |         let Self { name, age } = self;",
 84 |         );
 85 | 
 86 |         ui.horizontal(|ui| {
 87 |             let font_id = egui::TextStyle::Monospace.resolve(ui.style());
 88 |             let indentation = 2.0 * 4.0 * ui.fonts(|f| f.glyph_width(&font_id, ' '));
 89 |             ui.add_space(indentation);
 90 | 
 91 |             egui::Grid::new("code_samples")
 92 |                 .striped(true)
 93 |                 .num_columns(2)
 94 |                 .show(ui, |ui| {
 95 |                     self.samples_in_grid(ui);
 96 |                 });
 97 |         });
 98 | 
 99 |         crate::rust_view_ui(ui, "    }\n}");
100 |     }
101 | }
102 | 
103 | impl crate::Demo for CodeExample {
104 |     fn name(&self) -> &'static str {
105 |         "🖮 Code Example"
106 |     }
107 | 
108 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
109 |         use crate::View as _;
110 |         egui::Window::new(self.name())
111 |             .open(open)
112 |             .min_width(375.0)
113 |             .default_size([390.0, 500.0])
114 |             .scroll(false)
115 |             .resizable([true, false]) // resizable so we can shrink if the text edit grows
116 |             .show(ctx, |ui| self.ui(ui));
117 |     }
118 | }
119 | 
120 | impl crate::View for CodeExample {
121 |     fn ui(&mut self, ui: &mut egui::Ui) {
122 |         ui.scope(|ui| {
123 |             ui.spacing_mut().item_spacing = egui::vec2(8.0, 6.0);
124 |             self.code(ui);
125 |         });
126 | 
127 |         ui.separator();
128 | 
129 |         crate::rust_view_ui(ui, &format!("{self:#?}"));
130 | 
131 |         ui.separator();
132 | 
133 |         let mut theme =
134 |             egui_extras::syntax_highlighting::CodeTheme::from_memory(ui.ctx(), ui.style());
135 |         ui.collapsing("Theme", |ui| {
136 |             theme.ui(ui);
137 |             theme.store_in_memory(ui.ctx());
138 |         });
139 | 
140 |         ui.separator();
141 | 
142 |         ui.vertical_centered(|ui| {
143 |             ui.add(crate::egui_github_link_file!());
144 |         });
145 |     }
146 | }
147 | 
148 | fn show_code(ui: &mut egui::Ui, code: &str) {
149 |     let code = remove_leading_indentation(code.trim_start_matches('\n'));
150 |     crate::rust_view_ui(ui, &code);
151 | }
152 | 
153 | fn remove_leading_indentation(code: &str) -> String {
154 |     fn is_indent(c: &u8) -> bool {
155 |         matches!(*c, b' ' | b'\t')
156 |     }
157 | 
158 |     let first_line_indent = code.bytes().take_while(is_indent).count();
159 | 
160 |     let mut out = String::new();
161 | 
162 |     let mut code = code;
163 |     while !code.is_empty() {
164 |         let indent = code.bytes().take_while(is_indent).count();
165 |         let start = first_line_indent.min(indent);
166 |         let end = code
167 |             .find('\n')
168 |             .map_or_else(|| code.len(), |endline| endline + 1);
169 |         out += &code[start..end];
170 |         code = &code[end..];
171 |     }
172 |     out
173 | }
174 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/dancing_strings.rs:
--------------------------------------------------------------------------------
 1 | use egui::{
 2 |     Color32, Context, Pos2, Rect, Ui,
 3 |     containers::{Frame, Window},
 4 |     emath, epaint,
 5 |     epaint::PathStroke,
 6 |     hex_color, lerp, pos2, remap, vec2,
 7 | };
 8 | 
 9 | #[derive(Default)]
10 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
11 | #[cfg_attr(feature = "serde", serde(default))]
12 | pub struct DancingStrings {
13 |     colors: bool,
14 | }
15 | 
16 | impl crate::Demo for DancingStrings {
17 |     fn name(&self) -> &'static str {
18 |         "♫ Dancing Strings"
19 |     }
20 | 
21 |     fn show(&mut self, ctx: &Context, open: &mut bool) {
22 |         use crate::View as _;
23 |         Window::new(self.name())
24 |             .open(open)
25 |             .default_size(vec2(512.0, 256.0))
26 |             .vscroll(false)
27 |             .show(ctx, |ui| self.ui(ui));
28 |     }
29 | }
30 | 
31 | impl crate::View for DancingStrings {
32 |     fn ui(&mut self, ui: &mut Ui) {
33 |         let color = if ui.visuals().dark_mode {
34 |             Color32::from_additive_luminance(196)
35 |         } else {
36 |             Color32::from_black_alpha(240)
37 |         };
38 | 
39 |         ui.checkbox(&mut self.colors, "Colored")
40 |             .on_hover_text("Demonstrates how a path can have varying color across its length.");
41 | 
42 |         Frame::canvas(ui.style()).show(ui, |ui| {
43 |             ui.ctx().request_repaint();
44 |             let time = ui.input(|i| i.time);
45 | 
46 |             let desired_size = ui.available_width() * vec2(1.0, 0.35);
47 |             let (_id, rect) = ui.allocate_space(desired_size);
48 | 
49 |             let to_screen =
50 |                 emath::RectTransform::from_to(Rect::from_x_y_ranges(0.0..=1.0, -1.0..=1.0), rect);
51 | 
52 |             let mut shapes = vec![];
53 | 
54 |             for &mode in &[2, 3, 5] {
55 |                 let mode = mode as f64;
56 |                 let n = 120;
57 |                 let speed = 1.5;
58 | 
59 |                 let points: Vec<Pos2> = (0..=n)
60 |                     .map(|i| {
61 |                         let t = i as f64 / (n as f64);
62 |                         let amp = (time * speed * mode).sin() / mode;
63 |                         let y = amp * (t * std::f64::consts::TAU / 2.0 * mode).sin();
64 |                         to_screen * pos2(t as f32, y as f32)
65 |                     })
66 |                     .collect();
67 | 
68 |                 let thickness = 10.0 / mode as f32;
69 |                 shapes.push(epaint::Shape::line(
70 |                     points,
71 |                     if self.colors {
72 |                         PathStroke::new_uv(thickness, move |rect, p| {
73 |                             let t = remap(p.x, rect.x_range(), -1.0..=1.0).abs();
74 |                             let center_color = hex_color!("#5BCEFA");
75 |                             let outer_color = hex_color!("#F5A9B8");
76 | 
77 |                             Color32::from_rgb(
78 |                                 lerp(center_color.r() as f32..=outer_color.r() as f32, t) as u8,
79 |                                 lerp(center_color.g() as f32..=outer_color.g() as f32, t) as u8,
80 |                                 lerp(center_color.b() as f32..=outer_color.b() as f32, t) as u8,
81 |                             )
82 |                         })
83 |                     } else {
84 |                         PathStroke::new(thickness, color)
85 |                     },
86 |                 ));
87 |             }
88 | 
89 |             ui.painter().extend(shapes);
90 |         });
91 |         ui.vertical_centered(|ui| {
92 |             ui.add(crate::egui_github_link_file!());
93 |         });
94 |     }
95 | }
96 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/drag_and_drop.rs:
--------------------------------------------------------------------------------
  1 | use egui::{Color32, Context, Frame, Id, Ui, Window, vec2};
  2 | 
  3 | #[derive(Clone, PartialEq, Eq)]
  4 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  5 | pub struct DragAndDropDemo {
  6 |     /// columns with items
  7 |     columns: Vec<Vec<String>>,
  8 | }
  9 | 
 10 | impl Default for DragAndDropDemo {
 11 |     fn default() -> Self {
 12 |         Self {
 13 |             columns: vec![
 14 |                 vec!["Item A", "Item B", "Item C", "Item D"],
 15 |                 vec!["Item E", "Item F", "Item G"],
 16 |                 vec!["Item H", "Item I", "Item J", "Item K"],
 17 |             ]
 18 |             .into_iter()
 19 |             .map(|v| v.into_iter().map(ToString::to_string).collect())
 20 |             .collect(),
 21 |         }
 22 |     }
 23 | }
 24 | 
 25 | impl crate::Demo for DragAndDropDemo {
 26 |     fn name(&self) -> &'static str {
 27 |         "✋ Drag and Drop"
 28 |     }
 29 | 
 30 |     fn show(&mut self, ctx: &Context, open: &mut bool) {
 31 |         use crate::View as _;
 32 |         Window::new(self.name())
 33 |             .open(open)
 34 |             .default_size(vec2(256.0, 256.0))
 35 |             .vscroll(false)
 36 |             .resizable(false)
 37 |             .show(ctx, |ui| self.ui(ui));
 38 |     }
 39 | }
 40 | 
 41 | /// What is being dragged.
 42 | #[derive(Clone, Copy, Debug, PartialEq, Eq)]
 43 | struct Location {
 44 |     col: usize,
 45 |     row: usize,
 46 | }
 47 | 
 48 | impl crate::View for DragAndDropDemo {
 49 |     fn ui(&mut self, ui: &mut Ui) {
 50 |         ui.label("This is a simple example of drag-and-drop in egui.");
 51 |         ui.label("Drag items between columns.");
 52 | 
 53 |         // If there is a drop, store the location of the item being dragged, and the destination for the drop.
 54 |         let mut from = None;
 55 |         let mut to = None;
 56 | 
 57 |         ui.columns(self.columns.len(), |uis| {
 58 |             for (col_idx, column) in self.columns.clone().into_iter().enumerate() {
 59 |                 let ui = &mut uis[col_idx];
 60 | 
 61 |                 let frame = Frame::default().inner_margin(4.0);
 62 | 
 63 |                 let (_, dropped_payload) = ui.dnd_drop_zone::<Location, ()>(frame, |ui| {
 64 |                     ui.set_min_size(vec2(64.0, 100.0));
 65 |                     for (row_idx, item) in column.iter().enumerate() {
 66 |                         let item_id = Id::new(("my_drag_and_drop_demo", col_idx, row_idx));
 67 |                         let item_location = Location {
 68 |                             col: col_idx,
 69 |                             row: row_idx,
 70 |                         };
 71 |                         let response = ui
 72 |                             .dnd_drag_source(item_id, item_location, |ui| {
 73 |                                 ui.label(item);
 74 |                             })
 75 |                             .response;
 76 | 
 77 |                         // Detect drops onto this item:
 78 |                         if let (Some(pointer), Some(hovered_payload)) = (
 79 |                             ui.input(|i| i.pointer.interact_pos()),
 80 |                             response.dnd_hover_payload::<Location>(),
 81 |                         ) {
 82 |                             let rect = response.rect;
 83 | 
 84 |                             // Preview insertion:
 85 |                             let stroke = egui::Stroke::new(1.0, Color32::WHITE);
 86 |                             let insert_row_idx = if *hovered_payload == item_location {
 87 |                                 // We are dragged onto ourselves
 88 |                                 ui.painter().hline(rect.x_range(), rect.center().y, stroke);
 89 |                                 row_idx
 90 |                             } else if pointer.y < rect.center().y {
 91 |                                 // Above us
 92 |                                 ui.painter().hline(rect.x_range(), rect.top(), stroke);
 93 |                                 row_idx
 94 |                             } else {
 95 |                                 // Below us
 96 |                                 ui.painter().hline(rect.x_range(), rect.bottom(), stroke);
 97 |                                 row_idx + 1
 98 |                             };
 99 | 
100 |                             if let Some(dragged_payload) = response.dnd_release_payload() {
101 |                                 // The user dropped onto this item.
102 |                                 from = Some(dragged_payload);
103 |                                 to = Some(Location {
104 |                                     col: col_idx,
105 |                                     row: insert_row_idx,
106 |                                 });
107 |                             }
108 |                         }
109 |                     }
110 |                 });
111 | 
112 |                 if let Some(dragged_payload) = dropped_payload {
113 |                     // The user dropped onto the column, but not on any one item.
114 |                     from = Some(dragged_payload);
115 |                     to = Some(Location {
116 |                         col: col_idx,
117 |                         row: usize::MAX, // Inset last
118 |                     });
119 |                 }
120 |             }
121 |         });
122 | 
123 |         if let (Some(from), Some(mut to)) = (from, to) {
124 |             if from.col == to.col {
125 |                 // Dragging within the same column.
126 |                 // Adjust row index if we are re-ordering:
127 |                 to.row -= (from.row < to.row) as usize;
128 |             }
129 | 
130 |             let item = self.columns[from.col].remove(from.row);
131 | 
132 |             let column = &mut self.columns[to.col];
133 |             to.row = to.row.min(column.len());
134 |             column.insert(to.row, item);
135 |         }
136 | 
137 |         ui.vertical_centered(|ui| {
138 |             ui.add(crate::egui_github_link_file!());
139 |         });
140 |     }
141 | }
142 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/extra_viewport.rs:
--------------------------------------------------------------------------------
 1 | #[derive(Default)]
 2 | pub struct ExtraViewport {}
 3 | 
 4 | impl crate::Demo for ExtraViewport {
 5 |     fn is_enabled(&self, ctx: &egui::Context) -> bool {
 6 |         !ctx.embed_viewports()
 7 |     }
 8 | 
 9 |     fn name(&self) -> &'static str {
10 |         "🗖 Extra Viewport"
11 |     }
12 | 
13 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
14 |         if !*open {
15 |             return;
16 |         }
17 | 
18 |         let id = egui::Id::new(self.name());
19 | 
20 |         ctx.show_viewport_immediate(
21 |             egui::ViewportId(id),
22 |             egui::ViewportBuilder::default()
23 |                 .with_title(self.name())
24 |                 .with_inner_size([400.0, 512.0]),
25 |             |ctx, class| {
26 |                 if class == egui::ViewportClass::Embedded {
27 |                     // Not a real viewport
28 |                     egui::Window::new(self.name())
29 |                         .id(id)
30 |                         .open(open)
31 |                         .show(ctx, |ui| {
32 |                             ui.label("This egui integration does not support multiple viewports");
33 |                         });
34 |                 } else {
35 |                     egui::CentralPanel::default().show(ctx, |ui| {
36 |                         viewport_content(ui, ctx, open);
37 |                     });
38 |                 }
39 |             },
40 |         );
41 |     }
42 | }
43 | 
44 | fn viewport_content(ui: &mut egui::Ui, ctx: &egui::Context, open: &mut bool) {
45 |     ui.label("egui and eframe supports having multiple native windows like this, which egui calls 'viewports'.");
46 | 
47 |     ui.label(format!(
48 |         "This viewport has id: {:?}, child of viewport {:?}",
49 |         ctx.viewport_id(),
50 |         ctx.parent_viewport_id()
51 |     ));
52 | 
53 |     ui.label("Here you can see all the open viewports:");
54 | 
55 |     egui::ScrollArea::vertical().show(ui, |ui| {
56 |         let viewports = ui.input(|i| i.raw.viewports.clone());
57 |         for (id, viewport) in viewports {
58 |             ui.group(|ui| {
59 |                 ui.label(format!("viewport {id:?}"));
60 |                 ui.push_id(id, |ui| {
61 |                     viewport.ui(ui);
62 |                 });
63 |             });
64 |         }
65 |     });
66 | 
67 |     if ui.input(|i| i.viewport().close_requested()) {
68 |         *open = false;
69 |     }
70 | }
71 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/font_book.rs:
--------------------------------------------------------------------------------
  1 | use std::collections::BTreeMap;
  2 | 
  3 | struct GlyphInfo {
  4 |     name: String,
  5 | 
  6 |     // What fonts it is available in
  7 |     fonts: Vec<String>,
  8 | }
  9 | 
 10 | pub struct FontBook {
 11 |     filter: String,
 12 |     font_id: egui::FontId,
 13 |     available_glyphs: BTreeMap<egui::FontFamily, BTreeMap<char, GlyphInfo>>,
 14 | }
 15 | 
 16 | impl Default for FontBook {
 17 |     fn default() -> Self {
 18 |         Self {
 19 |             filter: Default::default(),
 20 |             font_id: egui::FontId::proportional(18.0),
 21 |             available_glyphs: Default::default(),
 22 |         }
 23 |     }
 24 | }
 25 | 
 26 | impl crate::Demo for FontBook {
 27 |     fn name(&self) -> &'static str {
 28 |         "🔤 Font Book"
 29 |     }
 30 | 
 31 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 32 |         egui::Window::new(self.name()).open(open).show(ctx, |ui| {
 33 |             use crate::View as _;
 34 |             self.ui(ui);
 35 |         });
 36 |     }
 37 | }
 38 | 
 39 | impl crate::View for FontBook {
 40 |     fn ui(&mut self, ui: &mut egui::Ui) {
 41 |         ui.vertical_centered(|ui| {
 42 |             ui.add(crate::egui_github_link_file!());
 43 |         });
 44 | 
 45 |         ui.label(format!(
 46 |             "The selected font supports {} characters.",
 47 |             self.available_glyphs
 48 |                 .get(&self.font_id.family)
 49 |                 .map(|map| map.len())
 50 |                 .unwrap_or_default()
 51 |         ));
 52 | 
 53 |         ui.horizontal_wrapped(|ui| {
 54 |             ui.spacing_mut().item_spacing.x = 0.0;
 55 |             ui.label("You can add more characters by installing additional fonts with ");
 56 |             ui.add(egui::Hyperlink::from_label_and_url(
 57 |                 egui::RichText::new("Context::set_fonts").text_style(egui::TextStyle::Monospace),
 58 |                 "https://docs.rs/egui/latest/egui/struct.Context.html#method.set_fonts",
 59 |             ));
 60 |             ui.label(".");
 61 |         });
 62 | 
 63 |         ui.separator();
 64 | 
 65 |         egui::introspection::font_id_ui(ui, &mut self.font_id);
 66 | 
 67 |         ui.horizontal(|ui| {
 68 |             ui.label("Filter:");
 69 |             ui.add(egui::TextEdit::singleline(&mut self.filter).desired_width(120.0));
 70 |             self.filter = self.filter.to_lowercase();
 71 |             if ui.button("ｘ").clicked() {
 72 |                 self.filter.clear();
 73 |             }
 74 |         });
 75 | 
 76 |         let filter = &self.filter;
 77 |         let available_glyphs = self
 78 |             .available_glyphs
 79 |             .entry(self.font_id.family.clone())
 80 |             .or_insert_with(|| available_characters(ui, self.font_id.family.clone()));
 81 | 
 82 |         ui.separator();
 83 | 
 84 |         egui::ScrollArea::vertical().show(ui, |ui| {
 85 |             ui.horizontal_wrapped(|ui| {
 86 |                 ui.spacing_mut().item_spacing = egui::Vec2::splat(2.0);
 87 | 
 88 |                 for (&chr, glyph_info) in available_glyphs.iter() {
 89 |                     if filter.is_empty()
 90 |                         || glyph_info.name.contains(filter)
 91 |                         || *filter == chr.to_string()
 92 |                     {
 93 |                         let button = egui::Button::new(
 94 |                             egui::RichText::new(chr.to_string()).font(self.font_id.clone()),
 95 |                         )
 96 |                         .frame(false);
 97 | 
 98 |                         let tooltip_ui = |ui: &mut egui::Ui| {
 99 |                             let font_id = self.font_id.clone();
100 | 
101 |                             char_info_ui(ui, chr, glyph_info, font_id);
102 |                         };
103 | 
104 |                         if ui.add(button).on_hover_ui(tooltip_ui).clicked() {
105 |                             ui.ctx().copy_text(chr.to_string());
106 |                         }
107 |                     }
108 |                 }
109 |             });
110 |         });
111 |     }
112 | }
113 | 
114 | fn char_info_ui(ui: &mut egui::Ui, chr: char, glyph_info: &GlyphInfo, font_id: egui::FontId) {
115 |     let resp = ui.label(egui::RichText::new(chr.to_string()).font(font_id));
116 | 
117 |     egui::Grid::new("char_info")
118 |         .num_columns(2)
119 |         .striped(true)
120 |         .show(ui, |ui| {
121 |             ui.label("Name");
122 |             ui.label(glyph_info.name.clone());
123 |             ui.end_row();
124 | 
125 |             ui.label("Hex");
126 |             ui.label(format!("{:X}", chr as u32));
127 |             ui.end_row();
128 | 
129 |             ui.label("Width");
130 |             ui.label(format!("{:.1} pts", resp.rect.width()));
131 |             ui.end_row();
132 | 
133 |             ui.label("Fonts");
134 |             ui.label(
135 |                 format!("{:?}", glyph_info.fonts)
136 |                     .trim_start_matches('[')
137 |                     .trim_end_matches(']'),
138 |             );
139 |             ui.end_row();
140 |         });
141 | }
142 | 
143 | fn available_characters(ui: &egui::Ui, family: egui::FontFamily) -> BTreeMap<char, GlyphInfo> {
144 |     ui.fonts(|f| {
145 |         f.lock()
146 |             .fonts
147 |             .font(&egui::FontId::new(10.0, family)) // size is arbitrary for getting the characters
148 |             .characters()
149 |             .iter()
150 |             .filter(|(chr, _fonts)| !chr.is_whitespace() && !chr.is_ascii_control())
151 |             .map(|(chr, fonts)| {
152 |                 (
153 |                     *chr,
154 |                     GlyphInfo {
155 |                         name: char_name(*chr),
156 |                         fonts: fonts.clone(),
157 |                     },
158 |                 )
159 |             })
160 |             .collect()
161 |     })
162 | }
163 | 
164 | fn char_name(chr: char) -> String {
165 |     special_char_name(chr)
166 |         .map(|s| s.to_owned())
167 |         .or_else(|| unicode_names2::name(chr).map(|name| name.to_string().to_lowercase()))
168 |         .unwrap_or_else(|| "unknown".to_owned())
169 | }
170 | 
171 | fn special_char_name(chr: char) -> Option<&'static str> {
172 |     #[expect(clippy::match_same_arms)] // many "flag"
173 |     match chr {
174 |         // Special private-use-area extensions found in `emoji-icon-font.ttf`:
175 |         // Private use area extensions:
176 |         '\u{FE4E5}' => Some("flag japan"),
177 |         '\u{FE4E6}' => Some("flag usa"),
178 |         '\u{FE4E7}' => Some("flag"),
179 |         '\u{FE4E8}' => Some("flag"),
180 |         '\u{FE4E9}' => Some("flag"),
181 |         '\u{FE4EA}' => Some("flag great britain"),
182 |         '\u{FE4EB}' => Some("flag"),
183 |         '\u{FE4EC}' => Some("flag"),
184 |         '\u{FE4ED}' => Some("flag"),
185 |         '\u{FE4EE}' => Some("flag south korea"),
186 |         '\u{FE82C}' => Some("number sign in square"),
187 |         '\u{FE82E}' => Some("digit one in square"),
188 |         '\u{FE82F}' => Some("digit two in square"),
189 |         '\u{FE830}' => Some("digit three in square"),
190 |         '\u{FE831}' => Some("digit four in square"),
191 |         '\u{FE832}' => Some("digit five in square"),
192 |         '\u{FE833}' => Some("digit six in square"),
193 |         '\u{FE834}' => Some("digit seven in square"),
194 |         '\u{FE835}' => Some("digit eight in square"),
195 |         '\u{FE836}' => Some("digit nine in square"),
196 |         '\u{FE837}' => Some("digit zero in square"),
197 | 
198 |         // Special private-use-area extensions found in `emoji-icon-font.ttf`:
199 |         // Web services / operating systems / browsers
200 |         '\u{E600}' => Some("web-dribbble"),
201 |         '\u{E601}' => Some("web-stackoverflow"),
202 |         '\u{E602}' => Some("web-vimeo"),
203 |         '\u{E604}' => Some("web-facebook"),
204 |         '\u{E605}' => Some("web-googleplus"),
205 |         '\u{E606}' => Some("web-pinterest"),
206 |         '\u{E607}' => Some("web-tumblr"),
207 |         '\u{E608}' => Some("web-linkedin"),
208 |         '\u{E60A}' => Some("web-stumbleupon"),
209 |         '\u{E60B}' => Some("web-lastfm"),
210 |         '\u{E60C}' => Some("web-rdio"),
211 |         '\u{E60D}' => Some("web-spotify"),
212 |         '\u{E60E}' => Some("web-qq"),
213 |         '\u{E60F}' => Some("web-instagram"),
214 |         '\u{E610}' => Some("web-dropbox"),
215 |         '\u{E611}' => Some("web-evernote"),
216 |         '\u{E612}' => Some("web-flattr"),
217 |         '\u{E613}' => Some("web-skype"),
218 |         '\u{E614}' => Some("web-renren"),
219 |         '\u{E615}' => Some("web-sina-weibo"),
220 |         '\u{E616}' => Some("web-paypal"),
221 |         '\u{E617}' => Some("web-picasa"),
222 |         '\u{E618}' => Some("os-android"),
223 |         '\u{E619}' => Some("web-mixi"),
224 |         '\u{E61A}' => Some("web-behance"),
225 |         '\u{E61B}' => Some("web-circles"),
226 |         '\u{E61C}' => Some("web-vk"),
227 |         '\u{E61D}' => Some("web-smashing"),
228 |         '\u{E61E}' => Some("web-forrst"),
229 |         '\u{E61F}' => Some("os-windows"),
230 |         '\u{E620}' => Some("web-flickr"),
231 |         '\u{E621}' => Some("web-picassa"),
232 |         '\u{E622}' => Some("web-deviantart"),
233 |         '\u{E623}' => Some("web-steam"),
234 |         '\u{E624}' => Some("web-github"),
235 |         '\u{E625}' => Some("web-git"),
236 |         '\u{E626}' => Some("web-blogger"),
237 |         '\u{E627}' => Some("web-soundcloud"),
238 |         '\u{E628}' => Some("web-reddit"),
239 |         '\u{E629}' => Some("web-delicious"),
240 |         '\u{E62A}' => Some("browser-chrome"),
241 |         '\u{E62B}' => Some("browser-firefox"),
242 |         '\u{E62C}' => Some("browser-ie"),
243 |         '\u{E62D}' => Some("browser-opera"),
244 |         '\u{E62E}' => Some("browser-safari"),
245 |         '\u{E62F}' => Some("web-google-drive"),
246 |         '\u{E630}' => Some("web-wordpress"),
247 |         '\u{E631}' => Some("web-joomla"),
248 |         '\u{E632}' => Some("lastfm"),
249 |         '\u{E633}' => Some("web-foursquare"),
250 |         '\u{E634}' => Some("web-yelp"),
251 |         '\u{E635}' => Some("web-drupal"),
252 |         '\u{E636}' => Some("youtube"),
253 |         '\u{F189}' => Some("vk"),
254 |         '\u{F1A6}' => Some("digg"),
255 |         '\u{F1CA}' => Some("web-vine"),
256 |         '\u{F8FF}' => Some("os-apple"),
257 | 
258 |         // Special private-use-area extensions found in `Ubuntu-Light.ttf`
259 |         '\u{F000}' => Some("uniF000"),
260 |         '\u{F001}' => Some("fi"),
261 |         '\u{F002}' => Some("fl"),
262 |         '\u{F506}' => Some("one seventh"),
263 |         '\u{F507}' => Some("two sevenths"),
264 |         '\u{F508}' => Some("three sevenths"),
265 |         '\u{F509}' => Some("four sevenths"),
266 |         '\u{F50A}' => Some("five sevenths"),
267 |         '\u{F50B}' => Some("six sevenths"),
268 |         '\u{F50C}' => Some("one ninth"),
269 |         '\u{F50D}' => Some("two ninths"),
270 |         '\u{F50E}' => Some("four ninths"),
271 |         '\u{F50F}' => Some("five ninths"),
272 |         '\u{F510}' => Some("seven ninths"),
273 |         '\u{F511}' => Some("eight ninths"),
274 |         '\u{F800}' => Some("zero.alt"),
275 |         '\u{F801}' => Some("one.alt"),
276 |         '\u{F802}' => Some("two.alt"),
277 |         '\u{F803}' => Some("three.alt"),
278 |         '\u{F804}' => Some("four.alt"),
279 |         '\u{F805}' => Some("five.alt"),
280 |         '\u{F806}' => Some("six.alt"),
281 |         '\u{F807}' => Some("seven.alt"),
282 |         '\u{F808}' => Some("eight.alt"),
283 |         '\u{F809}' => Some("nine.alt"),
284 |         '\u{F80A}' => Some("zero.sups"),
285 |         '\u{F80B}' => Some("one.sups"),
286 |         '\u{F80C}' => Some("two.sups"),
287 |         '\u{F80D}' => Some("three.sups"),
288 |         '\u{F80E}' => Some("four.sups"),
289 |         '\u{F80F}' => Some("five.sups"),
290 |         '\u{F810}' => Some("six.sups"),
291 |         '\u{F811}' => Some("seven.sups"),
292 |         '\u{F812}' => Some("eight.sups"),
293 |         '\u{F813}' => Some("nine.sups"),
294 |         '\u{F814}' => Some("zero.sinf"),
295 |         '\u{F815}' => Some("one.sinf"),
296 |         '\u{F816}' => Some("two.sinf"),
297 |         '\u{F817}' => Some("three.sinf"),
298 |         '\u{F818}' => Some("four.sinf"),
299 |         '\u{F819}' => Some("five.sinf"),
300 |         '\u{F81A}' => Some("six.sinf"),
301 |         '\u{F81B}' => Some("seven.sinf"),
302 |         '\u{F81C}' => Some("eight.sinf"),
303 |         '\u{F81D}' => Some("nine.sinf"),
304 | 
305 |         _ => None,
306 |     }
307 | }
308 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/frame_demo.rs:
--------------------------------------------------------------------------------
 1 | /// Shows off a table with dynamic layout
 2 | #[derive(PartialEq)]
 3 | pub struct FrameDemo {
 4 |     frame: egui::Frame,
 5 | }
 6 | 
 7 | impl Default for FrameDemo {
 8 |     fn default() -> Self {
 9 |         Self {
10 |             frame: egui::Frame::new()
11 |                 .inner_margin(12)
12 |                 .outer_margin(24)
13 |                 .corner_radius(14)
14 |                 .shadow(egui::Shadow {
15 |                     offset: [8, 12],
16 |                     blur: 16,
17 |                     spread: 0,
18 |                     color: egui::Color32::from_black_alpha(180),
19 |                 })
20 |                 .fill(egui::Color32::from_rgba_unmultiplied(97, 0, 255, 128))
21 |                 .stroke(egui::Stroke::new(1.0, egui::Color32::GRAY)),
22 |         }
23 |     }
24 | }
25 | 
26 | impl crate::Demo for FrameDemo {
27 |     fn name(&self) -> &'static str {
28 |         "▣ Frame"
29 |     }
30 | 
31 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
32 |         egui::Window::new(self.name())
33 |             .open(open)
34 |             .resizable(false)
35 |             .show(ctx, |ui| {
36 |                 use crate::View as _;
37 |                 self.ui(ui);
38 |             });
39 |     }
40 | }
41 | 
42 | impl crate::View for FrameDemo {
43 |     fn ui(&mut self, ui: &mut egui::Ui) {
44 |         ui.horizontal(|ui| {
45 |             ui.vertical(|ui| {
46 |                 ui.add(&mut self.frame);
47 | 
48 |                 ui.add_space(8.0);
49 |                 ui.set_max_width(ui.min_size().x);
50 |                 ui.vertical_centered(|ui| egui::reset_button(ui, self, "Reset"));
51 |             });
52 | 
53 |             ui.separator();
54 | 
55 |             ui.vertical(|ui| {
56 |                 // We want to paint a background around the outer margin of the demonstration frame, so we use another frame around it:
57 |                 egui::Frame::default()
58 |                     .stroke(ui.visuals().widgets.noninteractive.bg_stroke)
59 |                     .corner_radius(ui.visuals().widgets.noninteractive.corner_radius)
60 |                     .show(ui, |ui| {
61 |                         self.frame.show(ui, |ui| {
62 |                             ui.style_mut().wrap_mode = Some(egui::TextWrapMode::Extend);
63 |                             ui.label(egui::RichText::new("Content").color(egui::Color32::WHITE));
64 |                         });
65 |                     });
66 |             });
67 |         });
68 | 
69 |         ui.set_max_width(ui.min_size().x);
70 |         ui.separator();
71 |         ui.vertical_centered(|ui| ui.add(crate::egui_github_link_file!()));
72 |     }
73 | }
74 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/highlighting.rs:
--------------------------------------------------------------------------------
 1 | #[derive(Default)]
 2 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 3 | #[cfg_attr(feature = "serde", serde(default))]
 4 | pub struct Highlighting {}
 5 | 
 6 | impl crate::Demo for Highlighting {
 7 |     fn name(&self) -> &'static str {
 8 |         "✨ Highlighting"
 9 |     }
10 | 
11 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
12 |         egui::Window::new(self.name())
13 |             .default_width(320.0)
14 |             .open(open)
15 |             .show(ctx, |ui| {
16 |                 use crate::View as _;
17 |                 self.ui(ui);
18 |             });
19 |     }
20 | }
21 | 
22 | impl crate::View for Highlighting {
23 |     fn ui(&mut self, ui: &mut egui::Ui) {
24 |         ui.vertical_centered(|ui| {
25 |             ui.add(crate::egui_github_link_file!());
26 |         });
27 | 
28 |         ui.label("This demo demonstrates highlighting a widget.");
29 |         ui.add_space(4.0);
30 |         let label_response = ui.label("Hover me to highlight the button!");
31 |         ui.add_space(4.0);
32 |         let mut button_response = ui.button("Hover the button to highlight the label!");
33 | 
34 |         if label_response.hovered() {
35 |             button_response = button_response.highlight();
36 |         }
37 |         if button_response.hovered() {
38 |             label_response.highlight();
39 |         }
40 |     }
41 | }
42 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/interactive_container.rs:
--------------------------------------------------------------------------------
 1 | use egui::{Frame, Label, RichText, Sense, UiBuilder, Widget as _};
 2 | 
 3 | /// Showcase [`egui::Ui::response`].
 4 | #[derive(PartialEq, Eq, Default)]
 5 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 6 | #[cfg_attr(feature = "serde", serde(default))]
 7 | pub struct InteractiveContainerDemo {
 8 |     count: usize,
 9 | }
10 | 
11 | impl crate::Demo for InteractiveContainerDemo {
12 |     fn name(&self) -> &'static str {
13 |         "\u{20E3} Interactive Container"
14 |     }
15 | 
16 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
17 |         egui::Window::new(self.name())
18 |             .open(open)
19 |             .resizable(false)
20 |             .default_width(250.0)
21 |             .show(ctx, |ui| {
22 |                 use crate::View as _;
23 |                 self.ui(ui);
24 |             });
25 |     }
26 | }
27 | 
28 | impl crate::View for InteractiveContainerDemo {
29 |     fn ui(&mut self, ui: &mut egui::Ui) {
30 |         ui.vertical_centered(|ui| {
31 |             ui.add(crate::egui_github_link_file!());
32 |         });
33 | 
34 |         ui.horizontal_wrapped(|ui| {
35 |             ui.spacing_mut().item_spacing.x = 0.0;
36 |             ui.label("This demo showcases how to use ");
37 |             ui.code("Ui::response");
38 |             ui.label(" to create interactive container widgets that may contain other widgets.");
39 |         });
40 | 
41 |         let response = ui
42 |             .scope_builder(
43 |                 UiBuilder::new()
44 |                     .id_salt("interactive_container")
45 |                     .sense(Sense::click()),
46 |                 |ui| {
47 |                     let response = ui.response();
48 |                     let visuals = ui.style().interact(&response);
49 |                     let text_color = visuals.text_color();
50 | 
51 |                     Frame::canvas(ui.style())
52 |                         .fill(visuals.bg_fill.gamma_multiply(0.3))
53 |                         .stroke(visuals.bg_stroke)
54 |                         .inner_margin(ui.spacing().menu_margin)
55 |                         .show(ui, |ui| {
56 |                             ui.set_width(ui.available_width());
57 | 
58 |                             ui.add_space(32.0);
59 |                             ui.vertical_centered(|ui| {
60 |                                 Label::new(
61 |                                     RichText::new(format!("{}", self.count))
62 |                                         .color(text_color)
63 |                                         .size(32.0),
64 |                                 )
65 |                                 .selectable(false)
66 |                                 .ui(ui);
67 |                             });
68 |                             ui.add_space(32.0);
69 | 
70 |                             ui.horizontal(|ui| {
71 |                                 if ui.button("Reset").clicked() {
72 |                                     self.count = 0;
73 |                                 }
74 |                                 if ui.button("+ 100").clicked() {
75 |                                     self.count += 100;
76 |                                 }
77 |                             });
78 |                         });
79 |                 },
80 |             )
81 |             .response;
82 | 
83 |         if response.clicked() {
84 |             self.count += 1;
85 |         }
86 |     }
87 | }
88 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/mod.rs:
--------------------------------------------------------------------------------
 1 | //! Demo-code for showing how egui is used.
 2 | //!
 3 | //! The demo-code is also used in benchmarks and tests.
 4 | 
 5 | // ----------------------------------------------------------------------------
 6 | 
 7 | pub mod about;
 8 | pub mod code_editor;
 9 | pub mod code_example;
10 | pub mod dancing_strings;
11 | pub mod demo_app_windows;
12 | pub mod drag_and_drop;
13 | pub mod extra_viewport;
14 | pub mod font_book;
15 | pub mod frame_demo;
16 | pub mod highlighting;
17 | pub mod interactive_container;
18 | pub mod misc_demo_window;
19 | pub mod modals;
20 | pub mod multi_touch;
21 | pub mod paint_bezier;
22 | pub mod painting;
23 | pub mod panels;
24 | pub mod password;
25 | mod popups;
26 | pub mod scene;
27 | pub mod screenshot;
28 | pub mod scrolling;
29 | pub mod sliders;
30 | pub mod strip_demo;
31 | pub mod table_demo;
32 | pub mod tests;
33 | pub mod text_edit;
34 | pub mod text_layout;
35 | pub mod toggle_switch;
36 | pub mod tooltips;
37 | pub mod undo_redo;
38 | pub mod widget_gallery;
39 | pub mod window_options;
40 | 
41 | pub use {
42 |     about::About, demo_app_windows::DemoWindows, misc_demo_window::MiscDemoWindow,
43 |     widget_gallery::WidgetGallery,
44 | };
45 | 
46 | // ----------------------------------------------------------------------------
47 | 
48 | /// Something to view in the demo windows
49 | pub trait View {
50 |     fn ui(&mut self, ui: &mut egui::Ui);
51 | }
52 | 
53 | /// Something to view
54 | pub trait Demo {
55 |     /// Is the demo enabled for this integration?
56 |     fn is_enabled(&self, _ctx: &egui::Context) -> bool {
57 |         true
58 |     }
59 | 
60 |     /// `&'static` so we can also use it as a key to store open/close state.
61 |     fn name(&self) -> &'static str;
62 | 
63 |     /// Show windows, etc
64 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool);
65 | }
66 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/modals.rs:
--------------------------------------------------------------------------------
  1 | use egui::{ComboBox, Context, Id, Modal, ProgressBar, Ui, Widget as _, Window};
  2 | 
  3 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  4 | #[cfg_attr(feature = "serde", serde(default))]
  5 | pub struct Modals {
  6 |     user_modal_open: bool,
  7 |     save_modal_open: bool,
  8 |     save_progress: Option<f32>,
  9 | 
 10 |     role: &'static str,
 11 |     name: String,
 12 | }
 13 | 
 14 | impl Default for Modals {
 15 |     fn default() -> Self {
 16 |         Self {
 17 |             user_modal_open: false,
 18 |             save_modal_open: false,
 19 |             save_progress: None,
 20 |             role: Self::ROLES[0],
 21 |             name: "John Doe".to_owned(),
 22 |         }
 23 |     }
 24 | }
 25 | 
 26 | impl Modals {
 27 |     const ROLES: [&'static str; 2] = ["user", "admin"];
 28 | }
 29 | 
 30 | impl crate::Demo for Modals {
 31 |     fn name(&self) -> &'static str {
 32 |         "🗖 Modals"
 33 |     }
 34 | 
 35 |     fn show(&mut self, ctx: &Context, open: &mut bool) {
 36 |         use crate::View as _;
 37 |         Window::new(self.name())
 38 |             .open(open)
 39 |             .vscroll(false)
 40 |             .resizable(false)
 41 |             .show(ctx, |ui| self.ui(ui));
 42 |     }
 43 | }
 44 | 
 45 | impl crate::View for Modals {
 46 |     fn ui(&mut self, ui: &mut Ui) {
 47 |         let Self {
 48 |             user_modal_open,
 49 |             save_modal_open,
 50 |             save_progress,
 51 |             role,
 52 |             name,
 53 |         } = self;
 54 | 
 55 |         ui.horizontal(|ui| {
 56 |             if ui.button("Open User Modal").clicked() {
 57 |                 *user_modal_open = true;
 58 |             }
 59 | 
 60 |             if ui.button("Open Save Modal").clicked() {
 61 |                 *save_modal_open = true;
 62 |             }
 63 |         });
 64 | 
 65 |         ui.label("Click one of the buttons to open a modal.");
 66 |         ui.label("Modals have a backdrop and prevent interaction with the rest of the UI.");
 67 |         ui.label(
 68 |             "You can show modals on top of each other and close the topmost modal with \
 69 |             escape or by clicking outside the modal.",
 70 |         );
 71 | 
 72 |         if *user_modal_open {
 73 |             let modal = Modal::new(Id::new("Modal A")).show(ui.ctx(), |ui| {
 74 |                 ui.set_width(250.0);
 75 | 
 76 |                 ui.heading("Edit User");
 77 | 
 78 |                 ui.label("Name:");
 79 |                 ui.text_edit_singleline(name);
 80 | 
 81 |                 ComboBox::new("role", "Role")
 82 |                     .selected_text(*role)
 83 |                     .show_ui(ui, |ui| {
 84 |                         for r in Self::ROLES {
 85 |                             ui.selectable_value(role, r, r);
 86 |                         }
 87 |                     });
 88 | 
 89 |                 ui.separator();
 90 | 
 91 |                 egui::Sides::new().show(
 92 |                     ui,
 93 |                     |_ui| {},
 94 |                     |ui| {
 95 |                         if ui.button("Save").clicked() {
 96 |                             *save_modal_open = true;
 97 |                         }
 98 |                         if ui.button("Cancel").clicked() {
 99 |                             // You can call `ui.close()` to close the modal.
100 |                             // (This causes the current modals `should_close` to return true)
101 |                             ui.close();
102 |                         }
103 |                     },
104 |                 );
105 |             });
106 | 
107 |             if modal.should_close() {
108 |                 *user_modal_open = false;
109 |             }
110 |         }
111 | 
112 |         if *save_modal_open {
113 |             let modal = Modal::new(Id::new("Modal B")).show(ui.ctx(), |ui| {
114 |                 ui.set_width(200.0);
115 |                 ui.heading("Save? Are you sure?");
116 | 
117 |                 ui.add_space(32.0);
118 | 
119 |                 egui::Sides::new().show(
120 |                     ui,
121 |                     |_ui| {},
122 |                     |ui| {
123 |                         if ui.button("Yes Please").clicked() {
124 |                             *save_progress = Some(0.0);
125 |                         }
126 | 
127 |                         if ui.button("No Thanks").clicked() {
128 |                             ui.close();
129 |                         }
130 |                     },
131 |                 );
132 |             });
133 | 
134 |             if modal.should_close() {
135 |                 *save_modal_open = false;
136 |             }
137 |         }
138 | 
139 |         if let Some(progress) = *save_progress {
140 |             Modal::new(Id::new("Modal C")).show(ui.ctx(), |ui| {
141 |                 ui.set_width(70.0);
142 |                 ui.heading("Saving…");
143 | 
144 |                 ProgressBar::new(progress).ui(ui);
145 | 
146 |                 if progress >= 1.0 {
147 |                     *save_progress = None;
148 |                     *save_modal_open = false;
149 |                     *user_modal_open = false;
150 |                 } else {
151 |                     *save_progress = Some(progress + 0.003);
152 |                     ui.ctx().request_repaint();
153 |                 }
154 |             });
155 |         }
156 | 
157 |         ui.vertical_centered(|ui| {
158 |             ui.add(crate::egui_github_link_file!());
159 |         });
160 |     }
161 | }
162 | 
163 | #[cfg(test)]
164 | mod tests {
165 |     use crate::Demo as _;
166 |     use crate::demo::modals::Modals;
167 |     use egui::accesskit::Role;
168 |     use egui::{Key, Popup};
169 |     use egui_kittest::kittest::Queryable as _;
170 |     use egui_kittest::{Harness, SnapshotResults};
171 | 
172 |     #[test]
173 |     fn clicking_escape_when_popup_open_should_not_close_modal() {
174 |         let initial_state = Modals {
175 |             user_modal_open: true,
176 |             ..Modals::default()
177 |         };
178 | 
179 |         let mut harness = Harness::new_state(
180 |             |ctx, modals| {
181 |                 modals.show(ctx, &mut true);
182 |             },
183 |             initial_state,
184 |         );
185 | 
186 |         harness.get_by_role(Role::ComboBox).click();
187 | 
188 |         // Harness::run would fail because we keep requesting repaints to simulate progress.
189 |         harness.run_ok();
190 |         assert!(Popup::is_any_open(&harness.ctx));
191 |         assert!(harness.state().user_modal_open);
192 | 
193 |         harness.key_press(Key::Escape);
194 |         harness.run_ok();
195 |         assert!(!Popup::is_any_open(&harness.ctx));
196 |         assert!(harness.state().user_modal_open);
197 |     }
198 | 
199 |     #[test]
200 |     fn escape_should_close_top_modal() {
201 |         let initial_state = Modals {
202 |             user_modal_open: true,
203 |             save_modal_open: true,
204 |             ..Modals::default()
205 |         };
206 | 
207 |         let mut harness = Harness::new_state(
208 |             |ctx, modals| {
209 |                 modals.show(ctx, &mut true);
210 |             },
211 |             initial_state,
212 |         );
213 | 
214 |         assert!(harness.state().user_modal_open);
215 |         assert!(harness.state().save_modal_open);
216 | 
217 |         harness.key_press(Key::Escape);
218 |         harness.run();
219 | 
220 |         assert!(harness.state().user_modal_open);
221 |         assert!(!harness.state().save_modal_open);
222 |     }
223 | 
224 |     #[test]
225 |     fn should_match_snapshot() {
226 |         let initial_state = Modals {
227 |             user_modal_open: true,
228 |             ..Modals::default()
229 |         };
230 | 
231 |         let mut harness = Harness::new_state(
232 |             |ctx, modals| {
233 |                 modals.show(ctx, &mut true);
234 |             },
235 |             initial_state,
236 |         );
237 | 
238 |         let mut results = SnapshotResults::new();
239 | 
240 |         harness.run();
241 |         results.add(harness.try_snapshot("modals_1"));
242 | 
243 |         harness.get_by_label("Save").click();
244 |         harness.run_ok();
245 |         results.add(harness.try_snapshot("modals_2"));
246 | 
247 |         harness.get_by_label("Yes Please").click();
248 |         harness.run_ok();
249 |         results.add(harness.try_snapshot("modals_3"));
250 |     }
251 | 
252 |     // This tests whether the backdrop actually prevents interaction with lower layers.
253 |     #[test]
254 |     fn backdrop_should_prevent_focusing_lower_area() {
255 |         let initial_state = Modals {
256 |             save_modal_open: true,
257 |             save_progress: Some(0.0),
258 |             ..Modals::default()
259 |         };
260 | 
261 |         let mut harness = Harness::new_state(
262 |             |ctx, modals| {
263 |                 modals.show(ctx, &mut true);
264 |             },
265 |             initial_state,
266 |         );
267 | 
268 |         harness.run_ok();
269 | 
270 |         harness.get_by_label("Yes Please").click();
271 | 
272 |         harness.run_ok();
273 | 
274 |         // This snapshots should show the progress bar modal on top of the save modal.
275 |         harness.snapshot("modals_backdrop_should_prevent_focusing_lower_area");
276 |     }
277 | }
278 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/multi_touch.rs:
--------------------------------------------------------------------------------
  1 | use egui::{
  2 |     Color32, Frame, Pos2, Rect, Sense, Stroke, Vec2,
  3 |     emath::{RectTransform, Rot2},
  4 |     vec2,
  5 | };
  6 | 
  7 | pub struct MultiTouch {
  8 |     rotation: f32,
  9 |     translation: Vec2,
 10 |     zoom: f32,
 11 |     last_touch_time: f64,
 12 | }
 13 | 
 14 | impl Default for MultiTouch {
 15 |     fn default() -> Self {
 16 |         Self {
 17 |             rotation: 0.,
 18 |             translation: Vec2::ZERO,
 19 |             zoom: 1.,
 20 |             last_touch_time: 0.0,
 21 |         }
 22 |     }
 23 | }
 24 | 
 25 | impl crate::Demo for MultiTouch {
 26 |     fn name(&self) -> &'static str {
 27 |         "👌 Multi Touch"
 28 |     }
 29 | 
 30 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 31 |         egui::Window::new(self.name())
 32 |             .open(open)
 33 |             .default_size(vec2(512.0, 512.0))
 34 |             .resizable(true)
 35 |             .show(ctx, |ui| {
 36 |                 use crate::View as _;
 37 |                 self.ui(ui);
 38 |             });
 39 |     }
 40 | }
 41 | 
 42 | impl crate::View for MultiTouch {
 43 |     fn ui(&mut self, ui: &mut egui::Ui) {
 44 |         ui.vertical_centered(|ui| {
 45 |             ui.add(crate::egui_github_link_file!());
 46 |         });
 47 |         ui.strong(
 48 |             "This demo only works on devices with multitouch support (e.g. mobiles and tablets).",
 49 |         );
 50 |         ui.separator();
 51 |         ui.label("Try touch gestures Pinch/Stretch, Rotation, and Pressure with 2+ fingers.");
 52 | 
 53 |         let num_touches = ui.input(|i| i.multi_touch().map_or(0, |mt| mt.num_touches));
 54 |         ui.label(format!("Current touches: {num_touches}"));
 55 | 
 56 |         let color = if ui.visuals().dark_mode {
 57 |             Color32::WHITE
 58 |         } else {
 59 |             Color32::BLACK
 60 |         };
 61 | 
 62 |         Frame::canvas(ui.style()).show(ui, |ui| {
 63 |             // Note that we use `Sense::drag()` although we do not use any pointer events. With
 64 |             // the current implementation, the fact that a touch event of two or more fingers is
 65 |             // recognized, does not mean that the pointer events are suppressed, which are always
 66 |             // generated for the first finger. Therefore, if we do not explicitly consume pointer
 67 |             // events, the window will move around, not only when dragged with a single finger, but
 68 |             // also when a two-finger touch is active. I guess this problem can only be cleanly
 69 |             // solved when the synthetic pointer events are created by egui, and not by the
 70 |             // backend.
 71 | 
 72 |             // set up the drawing canvas with normalized coordinates:
 73 |             let (response, painter) =
 74 |                 ui.allocate_painter(ui.available_size_before_wrap(), Sense::drag());
 75 | 
 76 |             // normalize painter coordinates to ±1 units in each direction with [0,0] in the center:
 77 |             let painter_proportions = response.rect.square_proportions();
 78 |             let to_screen = RectTransform::from_to(
 79 |                 Rect::from_min_size(Pos2::ZERO - painter_proportions, 2. * painter_proportions),
 80 |                 response.rect,
 81 |             );
 82 | 
 83 |             // check for touch input (or the lack thereof) and update zoom and scale factors, plus
 84 |             // color and width:
 85 |             let mut stroke_width = 1.;
 86 |             if let Some(multi_touch) = ui.ctx().multi_touch() {
 87 |                 // This adjusts the current zoom factor and rotation angle according to the dynamic
 88 |                 // change (for the current frame) of the touch gesture:
 89 |                 self.zoom *= multi_touch.zoom_delta;
 90 |                 self.rotation += multi_touch.rotation_delta;
 91 |                 // the translation we get from `multi_touch` needs to be scaled down to the
 92 |                 // normalized coordinates we use as the basis for painting:
 93 |                 self.translation += to_screen.inverse().scale() * multi_touch.translation_delta;
 94 |                 // touch pressure will make the arrow thicker (not all touch devices support this):
 95 |                 stroke_width += 10. * multi_touch.force;
 96 | 
 97 |                 self.last_touch_time = ui.input(|i| i.time);
 98 |             } else {
 99 |                 self.slowly_reset(ui);
100 |             }
101 |             let zoom_and_rotate = self.zoom * Rot2::from_angle(self.rotation);
102 |             let arrow_start_offset = self.translation + zoom_and_rotate * vec2(-0.5, 0.5);
103 | 
104 |             // Paints an arrow pointing from bottom-left (-0.5, 0.5) to top-right (0.5, -0.5), but
105 |             // scaled, rotated, and translated according to the current touch gesture:
106 |             let arrow_start = Pos2::ZERO + arrow_start_offset;
107 |             let arrow_direction = zoom_and_rotate * vec2(1., -1.);
108 |             painter.arrow(
109 |                 to_screen * arrow_start,
110 |                 to_screen.scale() * arrow_direction,
111 |                 Stroke::new(stroke_width, color),
112 |             );
113 |         });
114 |     }
115 | }
116 | 
117 | impl MultiTouch {
118 |     fn slowly_reset(&mut self, ui: &egui::Ui) {
119 |         // This has nothing to do with the touch gesture. It just smoothly brings the
120 |         // painted arrow back into its original position, for a nice visual effect:
121 | 
122 |         let time_since_last_touch = (ui.input(|i| i.time) - self.last_touch_time) as f32;
123 | 
124 |         let delay = 0.5;
125 |         if time_since_last_touch < delay {
126 |             ui.ctx().request_repaint();
127 |         } else {
128 |             // seconds after which half the amount of zoom/rotation will be reverted:
129 |             let half_life =
130 |                 egui::remap_clamp(time_since_last_touch, delay..=1.0, 1.0..=0.0).powf(4.0);
131 | 
132 |             if half_life <= 1e-3 {
133 |                 self.zoom = 1.0;
134 |                 self.rotation = 0.0;
135 |                 self.translation = Vec2::ZERO;
136 |             } else {
137 |                 let dt = ui.input(|i| i.unstable_dt);
138 |                 let half_life_factor = (-(2_f32.ln()) / half_life * dt).exp();
139 |                 self.zoom = 1. + ((self.zoom - 1.) * half_life_factor);
140 |                 self.rotation *= half_life_factor;
141 |                 self.translation *= half_life_factor;
142 |                 ui.ctx().request_repaint();
143 |             }
144 |         }
145 |     }
146 | }
147 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/paint_bezier.rs:
--------------------------------------------------------------------------------
  1 | use egui::{
  2 |     Color32, Context, Frame, Grid, Pos2, Rect, Sense, Shape, Stroke, StrokeKind, Ui, Vec2,
  3 |     Widget as _, Window, emath,
  4 |     epaint::{self, CubicBezierShape, PathShape, QuadraticBezierShape},
  5 |     pos2,
  6 | };
  7 | 
  8 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  9 | #[cfg_attr(feature = "serde", serde(default))]
 10 | pub struct PaintBezier {
 11 |     /// Bézier curve degree, it can be 3, 4.
 12 |     degree: usize,
 13 | 
 14 |     /// The control points. The [`Self::degree`] first of them are used.
 15 |     control_points: [Pos2; 4],
 16 | 
 17 |     /// Stroke for Bézier curve.
 18 |     stroke: Stroke,
 19 | 
 20 |     /// Fill for Bézier curve.
 21 |     fill: Color32,
 22 | 
 23 |     /// Stroke for auxiliary lines.
 24 |     aux_stroke: Stroke,
 25 | 
 26 |     bounding_box_stroke: Stroke,
 27 | }
 28 | 
 29 | impl Default for PaintBezier {
 30 |     fn default() -> Self {
 31 |         Self {
 32 |             degree: 4,
 33 |             control_points: [
 34 |                 pos2(50.0, 50.0),
 35 |                 pos2(60.0, 250.0),
 36 |                 pos2(200.0, 200.0),
 37 |                 pos2(250.0, 50.0),
 38 |             ],
 39 |             stroke: Stroke::new(1.0, Color32::from_rgb(25, 200, 100)),
 40 |             fill: Color32::from_rgb(50, 100, 150).linear_multiply(0.25),
 41 |             aux_stroke: Stroke::new(1.0, Color32::RED.linear_multiply(0.25)),
 42 |             bounding_box_stroke: Stroke::new(0.0, Color32::LIGHT_GREEN.linear_multiply(0.25)),
 43 |         }
 44 |     }
 45 | }
 46 | 
 47 | impl PaintBezier {
 48 |     pub fn ui_control(&mut self, ui: &mut egui::Ui) {
 49 |         ui.collapsing("Colors", |ui| {
 50 |             Grid::new("colors")
 51 |                 .num_columns(2)
 52 |                 .spacing([12.0, 8.0])
 53 |                 .striped(true)
 54 |                 .show(ui, |ui| {
 55 |                     ui.label("Fill color");
 56 |                     ui.color_edit_button_srgba(&mut self.fill);
 57 |                     ui.end_row();
 58 | 
 59 |                     ui.label("Curve Stroke");
 60 |                     ui.add(&mut self.stroke);
 61 |                     ui.end_row();
 62 | 
 63 |                     ui.label("Auxiliary Stroke");
 64 |                     ui.add(&mut self.aux_stroke);
 65 |                     ui.end_row();
 66 | 
 67 |                     ui.label("Bounding Box Stroke");
 68 |                     ui.add(&mut self.bounding_box_stroke);
 69 |                     ui.end_row();
 70 |                 });
 71 |         });
 72 | 
 73 |         ui.collapsing("Global tessellation options", |ui| {
 74 |             let mut tessellation_options = ui.ctx().tessellation_options(|to| *to);
 75 |             tessellation_options.ui(ui);
 76 |             ui.ctx()
 77 |                 .tessellation_options_mut(|to| *to = tessellation_options);
 78 |         });
 79 | 
 80 |         ui.radio_value(&mut self.degree, 3, "Quadratic Bézier");
 81 |         ui.radio_value(&mut self.degree, 4, "Cubic Bézier");
 82 |         ui.label("Move the points by dragging them.");
 83 |         ui.small("Only convex curves can be accurately filled.");
 84 |     }
 85 | 
 86 |     pub fn ui_content(&mut self, ui: &mut Ui) -> egui::Response {
 87 |         let (response, painter) =
 88 |             ui.allocate_painter(Vec2::new(ui.available_width(), 300.0), Sense::hover());
 89 | 
 90 |         let to_screen = emath::RectTransform::from_to(
 91 |             Rect::from_min_size(Pos2::ZERO, response.rect.size()),
 92 |             response.rect,
 93 |         );
 94 | 
 95 |         let control_point_radius = 8.0;
 96 | 
 97 |         let control_point_shapes: Vec<Shape> = self
 98 |             .control_points
 99 |             .iter_mut()
100 |             .enumerate()
101 |             .take(self.degree)
102 |             .map(|(i, point)| {
103 |                 let size = Vec2::splat(2.0 * control_point_radius);
104 | 
105 |                 let point_in_screen = to_screen.transform_pos(*point);
106 |                 let point_rect = Rect::from_center_size(point_in_screen, size);
107 |                 let point_id = response.id.with(i);
108 |                 let point_response = ui.interact(point_rect, point_id, Sense::drag());
109 | 
110 |                 *point += point_response.drag_delta();
111 |                 *point = to_screen.from().clamp(*point);
112 | 
113 |                 let point_in_screen = to_screen.transform_pos(*point);
114 |                 let stroke = ui.style().interact(&point_response).fg_stroke;
115 | 
116 |                 Shape::circle_stroke(point_in_screen, control_point_radius, stroke)
117 |             })
118 |             .collect();
119 | 
120 |         let points_in_screen: Vec<Pos2> = self
121 |             .control_points
122 |             .iter()
123 |             .take(self.degree)
124 |             .map(|p| to_screen * *p)
125 |             .collect();
126 | 
127 |         match self.degree {
128 |             3 => {
129 |                 let points = points_in_screen.clone().try_into().unwrap();
130 |                 let shape =
131 |                     QuadraticBezierShape::from_points_stroke(points, true, self.fill, self.stroke);
132 |                 painter.add(epaint::RectShape::stroke(
133 |                     shape.visual_bounding_rect(),
134 |                     0.0,
135 |                     self.bounding_box_stroke,
136 |                     StrokeKind::Outside,
137 |                 ));
138 |                 painter.add(shape);
139 |             }
140 |             4 => {
141 |                 let points = points_in_screen.clone().try_into().unwrap();
142 |                 let shape =
143 |                     CubicBezierShape::from_points_stroke(points, true, self.fill, self.stroke);
144 |                 painter.add(epaint::RectShape::stroke(
145 |                     shape.visual_bounding_rect(),
146 |                     0.0,
147 |                     self.bounding_box_stroke,
148 |                     StrokeKind::Outside,
149 |                 ));
150 |                 painter.add(shape);
151 |             }
152 |             _ => {
153 |                 unreachable!();
154 |             }
155 |         };
156 | 
157 |         painter.add(PathShape::line(points_in_screen, self.aux_stroke));
158 |         painter.extend(control_point_shapes);
159 | 
160 |         response
161 |     }
162 | }
163 | 
164 | impl crate::Demo for PaintBezier {
165 |     fn name(&self) -> &'static str {
166 |         "） Bézier Curve"
167 |     }
168 | 
169 |     fn show(&mut self, ctx: &Context, open: &mut bool) {
170 |         use crate::View as _;
171 |         Window::new(self.name())
172 |             .open(open)
173 |             .vscroll(false)
174 |             .resizable(false)
175 |             .default_size([300.0, 350.0])
176 |             .show(ctx, |ui| self.ui(ui));
177 |     }
178 | }
179 | 
180 | impl crate::View for PaintBezier {
181 |     fn ui(&mut self, ui: &mut Ui) {
182 |         ui.vertical_centered(|ui| {
183 |             ui.add(crate::egui_github_link_file!());
184 |         });
185 |         self.ui_control(ui);
186 | 
187 |         Frame::canvas(ui.style()).show(ui, |ui| {
188 |             self.ui_content(ui);
189 |         });
190 |     }
191 | }
192 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/painting.rs:
--------------------------------------------------------------------------------
  1 | use egui::{Color32, Context, Frame, Pos2, Rect, Sense, Stroke, Ui, Window, emath, vec2};
  2 | 
  3 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  4 | #[cfg_attr(feature = "serde", serde(default))]
  5 | pub struct Painting {
  6 |     /// in 0-1 normalized coordinates
  7 |     lines: Vec<Vec<Pos2>>,
  8 |     stroke: Stroke,
  9 | }
 10 | 
 11 | impl Default for Painting {
 12 |     fn default() -> Self {
 13 |         Self {
 14 |             lines: Default::default(),
 15 |             stroke: Stroke::new(1.0, Color32::from_rgb(25, 200, 100)),
 16 |         }
 17 |     }
 18 | }
 19 | 
 20 | impl Painting {
 21 |     pub fn ui_control(&mut self, ui: &mut egui::Ui) -> egui::Response {
 22 |         ui.horizontal(|ui| {
 23 |             ui.label("Stroke:");
 24 |             ui.add(&mut self.stroke);
 25 |             ui.separator();
 26 |             if ui.button("Clear Painting").clicked() {
 27 |                 self.lines.clear();
 28 |             }
 29 |         })
 30 |         .response
 31 |     }
 32 | 
 33 |     pub fn ui_content(&mut self, ui: &mut Ui) -> egui::Response {
 34 |         let (mut response, painter) =
 35 |             ui.allocate_painter(ui.available_size_before_wrap(), Sense::drag());
 36 | 
 37 |         let to_screen = emath::RectTransform::from_to(
 38 |             Rect::from_min_size(Pos2::ZERO, response.rect.square_proportions()),
 39 |             response.rect,
 40 |         );
 41 |         let from_screen = to_screen.inverse();
 42 | 
 43 |         if self.lines.is_empty() {
 44 |             self.lines.push(vec![]);
 45 |         }
 46 | 
 47 |         let current_line = self.lines.last_mut().unwrap();
 48 | 
 49 |         if let Some(pointer_pos) = response.interact_pointer_pos() {
 50 |             let canvas_pos = from_screen * pointer_pos;
 51 |             if current_line.last() != Some(&canvas_pos) {
 52 |                 current_line.push(canvas_pos);
 53 |                 response.mark_changed();
 54 |             }
 55 |         } else if !current_line.is_empty() {
 56 |             self.lines.push(vec![]);
 57 |             response.mark_changed();
 58 |         }
 59 | 
 60 |         let shapes = self
 61 |             .lines
 62 |             .iter()
 63 |             .filter(|line| line.len() >= 2)
 64 |             .map(|line| {
 65 |                 let points: Vec<Pos2> = line.iter().map(|p| to_screen * *p).collect();
 66 |                 egui::Shape::line(points, self.stroke)
 67 |             });
 68 | 
 69 |         painter.extend(shapes);
 70 | 
 71 |         response
 72 |     }
 73 | }
 74 | 
 75 | impl crate::Demo for Painting {
 76 |     fn name(&self) -> &'static str {
 77 |         "🖊 Painting"
 78 |     }
 79 | 
 80 |     fn show(&mut self, ctx: &Context, open: &mut bool) {
 81 |         use crate::View as _;
 82 |         Window::new(self.name())
 83 |             .open(open)
 84 |             .default_size(vec2(512.0, 512.0))
 85 |             .vscroll(false)
 86 |             .show(ctx, |ui| self.ui(ui));
 87 |     }
 88 | }
 89 | 
 90 | impl crate::View for Painting {
 91 |     fn ui(&mut self, ui: &mut Ui) {
 92 |         ui.vertical_centered(|ui| {
 93 |             ui.add(crate::egui_github_link_file!());
 94 |         });
 95 |         self.ui_control(ui);
 96 |         ui.label("Paint with your mouse/touch!");
 97 |         Frame::canvas(ui.style()).show(ui, |ui| {
 98 |             self.ui_content(ui);
 99 |         });
100 |     }
101 | }
102 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/panels.rs:
--------------------------------------------------------------------------------
 1 | #[derive(Clone, Default, PartialEq, Eq)]
 2 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 3 | pub struct Panels {}
 4 | 
 5 | impl crate::Demo for Panels {
 6 |     fn name(&self) -> &'static str {
 7 |         "🗖 Panels"
 8 |     }
 9 | 
10 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
11 |         use crate::View as _;
12 |         let window = egui::Window::new("Panels")
13 |             .default_width(600.0)
14 |             .default_height(400.0)
15 |             .vscroll(false)
16 |             .open(open);
17 |         window.show(ctx, |ui| self.ui(ui));
18 |     }
19 | }
20 | 
21 | impl crate::View for Panels {
22 |     fn ui(&mut self, ui: &mut egui::Ui) {
23 |         // Note that the order we add the panels is very important!
24 | 
25 |         egui::TopBottomPanel::top("top_panel")
26 |             .resizable(true)
27 |             .min_height(32.0)
28 |             .show_inside(ui, |ui| {
29 |                 egui::ScrollArea::vertical().show(ui, |ui| {
30 |                     ui.vertical_centered(|ui| {
31 |                         ui.heading("Expandable Upper Panel");
32 |                     });
33 |                     lorem_ipsum(ui);
34 |                 });
35 |             });
36 | 
37 |         egui::SidePanel::left("left_panel")
38 |             .resizable(true)
39 |             .default_width(150.0)
40 |             .width_range(80.0..=200.0)
41 |             .show_inside(ui, |ui| {
42 |                 ui.vertical_centered(|ui| {
43 |                     ui.heading("Left Panel");
44 |                 });
45 |                 egui::ScrollArea::vertical().show(ui, |ui| {
46 |                     lorem_ipsum(ui);
47 |                 });
48 |             });
49 | 
50 |         egui::SidePanel::right("right_panel")
51 |             .resizable(true)
52 |             .default_width(150.0)
53 |             .width_range(80.0..=200.0)
54 |             .show_inside(ui, |ui| {
55 |                 ui.vertical_centered(|ui| {
56 |                     ui.heading("Right Panel");
57 |                 });
58 |                 egui::ScrollArea::vertical().show(ui, |ui| {
59 |                     lorem_ipsum(ui);
60 |                 });
61 |             });
62 | 
63 |         egui::TopBottomPanel::bottom("bottom_panel")
64 |             .resizable(false)
65 |             .min_height(0.0)
66 |             .show_inside(ui, |ui| {
67 |                 ui.vertical_centered(|ui| {
68 |                     ui.heading("Bottom Panel");
69 |                 });
70 |                 ui.vertical_centered(|ui| {
71 |                     ui.add(crate::egui_github_link_file!());
72 |                 });
73 |             });
74 | 
75 |         egui::CentralPanel::default().show_inside(ui, |ui| {
76 |             ui.vertical_centered(|ui| {
77 |                 ui.heading("Central Panel");
78 |             });
79 |             egui::ScrollArea::vertical().show(ui, |ui| {
80 |                 lorem_ipsum(ui);
81 |             });
82 |         });
83 |     }
84 | }
85 | 
86 | fn lorem_ipsum(ui: &mut egui::Ui) {
87 |     ui.with_layout(
88 |         egui::Layout::top_down(egui::Align::LEFT).with_cross_justify(true),
89 |         |ui| {
90 |             ui.label(egui::RichText::new(crate::LOREM_IPSUM_LONG).small().weak());
91 |             ui.add(egui::Separator::default().grow(8.0));
92 |             ui.label(egui::RichText::new(crate::LOREM_IPSUM_LONG).small().weak());
93 |         },
94 |     );
95 | }
96 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/password.rs:
--------------------------------------------------------------------------------
 1 | //! Source code example about creating a widget which uses `egui::Memory` to store UI state.
 2 | //!
 3 | //! This is meant to be read as a tutorial, hence the plethora of comments.
 4 | 
 5 | /// Password entry field with ability to toggle character hiding.
 6 | ///
 7 | /// ## Example:
 8 | /// ``` ignore
 9 | /// password_ui(ui, &mut my_password);
10 | /// ```
11 | pub fn password_ui(ui: &mut egui::Ui, password: &mut String) -> egui::Response {
12 |     // This widget has its own state — show or hide password characters (`show_plaintext`).
13 |     // In this case we use a simple `bool`, but you can also declare your own type.
14 |     // It must implement at least `Clone` and be `'static`.
15 |     // If you use the `persistence` feature, it also must implement `serde::{Deserialize, Serialize}`.
16 | 
17 |     // Generate an id for the state
18 |     let state_id = ui.id().with("show_plaintext");
19 | 
20 |     // Get state for this widget.
21 |     // You should get state by value, not by reference to avoid borrowing of [`Memory`].
22 |     let mut show_plaintext = ui.data_mut(|d| d.get_temp::<bool>(state_id).unwrap_or(false));
23 | 
24 |     // Process ui, change a local copy of the state
25 |     // We want TextEdit to fill entire space, and have button after that, so in that case we can
26 |     // change direction to right_to_left.
27 |     let result = ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
28 |         // Toggle the `show_plaintext` bool with a button:
29 |         let response = ui
30 |             .selectable_label(show_plaintext, "👁")
31 |             .on_hover_text("Show/hide password");
32 | 
33 |         if response.clicked() {
34 |             show_plaintext = !show_plaintext;
35 |         }
36 | 
37 |         // Show the password field:
38 |         ui.add_sized(
39 |             ui.available_size(),
40 |             egui::TextEdit::singleline(password).password(!show_plaintext),
41 |         );
42 |     });
43 | 
44 |     // Store the (possibly changed) state:
45 |     ui.data_mut(|d| d.insert_temp(state_id, show_plaintext));
46 | 
47 |     // All done! Return the interaction response so the user can check what happened
48 |     // (hovered, clicked, …) and maybe show a tooltip:
49 |     result.response
50 | }
51 | 
52 | // A wrapper that allows the more idiomatic usage pattern: `ui.add(…)`
53 | /// Password entry field with ability to toggle character hiding.
54 | ///
55 | /// ## Example:
56 | /// ``` ignore
57 | /// ui.add(password(&mut my_password));
58 | /// ```
59 | pub fn password(password: &mut String) -> impl egui::Widget + '_ {
60 |     move |ui: &mut egui::Ui| password_ui(ui, password)
61 | }
62 | 
63 | pub fn url_to_file_source_code() -> String {
64 |     format!("https://github.com/emilk/egui/blob/main/{}", file!())
65 | }
66 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/popups.rs:
--------------------------------------------------------------------------------
  1 | use crate::rust_view_ui;
  2 | use egui::color_picker::{Alpha, color_picker_color32};
  3 | use egui::containers::menu::{MenuConfig, SubMenuButton};
  4 | use egui::{
  5 |     Align, Align2, ComboBox, Frame, Id, Layout, Popup, PopupCloseBehavior, RectAlign, RichText,
  6 |     Tooltip, Ui, UiBuilder, include_image,
  7 | };
  8 | 
  9 | /// Showcase [`Popup`].
 10 | #[derive(Clone, PartialEq)]
 11 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 12 | #[cfg_attr(feature = "serde", serde(default))]
 13 | pub struct PopupsDemo {
 14 |     align4: RectAlign,
 15 |     gap: f32,
 16 |     #[cfg_attr(feature = "serde", serde(skip))]
 17 |     close_behavior: PopupCloseBehavior,
 18 |     popup_open: bool,
 19 |     checked: bool,
 20 |     color: egui::Color32,
 21 | }
 22 | 
 23 | impl PopupsDemo {
 24 |     fn apply_options<'a>(&self, popup: Popup<'a>) -> Popup<'a> {
 25 |         popup
 26 |             .align(self.align4)
 27 |             .gap(self.gap)
 28 |             .close_behavior(self.close_behavior)
 29 |     }
 30 | 
 31 |     fn nested_menus(&mut self, ui: &mut Ui) {
 32 |         ui.set_max_width(200.0); // To make sure we wrap long text
 33 | 
 34 |         if ui.button("Open…").clicked() {
 35 |             ui.close();
 36 |         }
 37 |         ui.menu_button("Popups can have submenus", |ui| {
 38 |             ui.menu_button("SubMenu", |ui| {
 39 |                 if ui.button("Open…").clicked() {
 40 |                     ui.close();
 41 |                 }
 42 |                 let _ = ui.button("Item");
 43 |                 ui.menu_button("Recursive", |ui| self.nested_menus(ui));
 44 |             });
 45 |             ui.menu_button("SubMenu", |ui| {
 46 |                 if ui.button("Open…").clicked() {
 47 |                     ui.close();
 48 |                 }
 49 |                 let _ = ui.button("Item");
 50 |             });
 51 |             let _ = ui.button("Item");
 52 |             if ui.button("Open…").clicked() {
 53 |                 ui.close();
 54 |             }
 55 |         });
 56 |         ui.menu_image_text_button(
 57 |             include_image!("../../data/icon.png"),
 58 |             "I have an icon!",
 59 |             |ui| {
 60 |                 let _ = ui.button("Item1");
 61 |                 let _ = ui.button("Item2");
 62 |                 let _ = ui.button("Item3");
 63 |                 let _ = ui.button("Item4");
 64 |                 if ui.button("Open…").clicked() {
 65 |                     ui.close();
 66 |                 }
 67 |             },
 68 |         );
 69 |         let _ = ui.button("Very long text for this item that should be wrapped");
 70 |         SubMenuButton::new("Always CloseOnClickOutside")
 71 |             .config(MenuConfig::new().close_behavior(PopupCloseBehavior::CloseOnClickOutside))
 72 |             .ui(ui, |ui| {
 73 |                 ui.checkbox(&mut self.checked, "Checkbox");
 74 | 
 75 |                 // Customized color SubMenuButton
 76 |                 let is_bright = self.color.intensity() > 0.5;
 77 |                 let text_color = if is_bright {
 78 |                     egui::Color32::BLACK
 79 |                 } else {
 80 |                     egui::Color32::WHITE
 81 |                 };
 82 |                 let mut color_button =
 83 |                     SubMenuButton::new(RichText::new("Background").color(text_color));
 84 |                 color_button.button = color_button.button.fill(self.color);
 85 |                 color_button.button = color_button
 86 |                     .button
 87 |                     .right_text(RichText::new(SubMenuButton::RIGHT_ARROW).color(text_color));
 88 |                 color_button.ui(ui, |ui| {
 89 |                     ui.spacing_mut().slider_width = 200.0;
 90 |                     color_picker_color32(ui, &mut self.color, Alpha::Opaque);
 91 |                 });
 92 | 
 93 |                 if ui.button("Open…").clicked() {
 94 |                     ui.close();
 95 |                 }
 96 |             });
 97 |     }
 98 | }
 99 | 
100 | impl Default for PopupsDemo {
101 |     fn default() -> Self {
102 |         Self {
103 |             align4: RectAlign::default(),
104 |             gap: 4.0,
105 |             close_behavior: PopupCloseBehavior::CloseOnClick,
106 |             popup_open: false,
107 |             checked: false,
108 |             color: egui::Color32::RED,
109 |         }
110 |     }
111 | }
112 | 
113 | impl crate::Demo for PopupsDemo {
114 |     fn name(&self) -> &'static str {
115 |         "\u{2755} Popups"
116 |     }
117 | 
118 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
119 |         egui::Window::new(self.name())
120 |             .open(open)
121 |             .resizable(false)
122 |             .default_width(250.0)
123 |             .constrain(false)
124 |             .show(ctx, |ui| {
125 |                 use crate::View as _;
126 |                 self.ui(ui);
127 |             });
128 |     }
129 | }
130 | 
131 | impl crate::View for PopupsDemo {
132 |     fn ui(&mut self, ui: &mut egui::Ui) {
133 |         let response = Frame::group(ui.style())
134 |             .show(ui, |ui| {
135 |                 ui.set_width(ui.available_width());
136 |                 ui.vertical_centered(|ui| ui.button("Click, right-click and hover me!"))
137 |                     .inner
138 |             })
139 |             .inner;
140 | 
141 |         self.apply_options(Popup::menu(&response).id(Id::new("menu")))
142 |             .show(|ui| self.nested_menus(ui));
143 | 
144 |         self.apply_options(Popup::context_menu(&response).id(Id::new("context_menu")))
145 |             .show(|ui| self.nested_menus(ui));
146 | 
147 |         if self.popup_open {
148 |             self.apply_options(Popup::from_response(&response).id(Id::new("popup")))
149 |                 .show(|ui| {
150 |                     ui.label("Popup contents");
151 |                 });
152 |         }
153 | 
154 |         let mut tooltip = Tooltip::for_enabled(&response);
155 |         tooltip.popup = self.apply_options(tooltip.popup);
156 |         tooltip.show(|ui| {
157 |             ui.label("Tooltips are popups, too!");
158 |         });
159 | 
160 |         Frame::canvas(ui.style()).show(ui, |ui| {
161 |             let mut reset_btn_ui = ui.new_child(
162 |                 UiBuilder::new()
163 |                     .max_rect(ui.max_rect())
164 |                     .layout(Layout::right_to_left(Align::Min)),
165 |             );
166 |             if reset_btn_ui
167 |                 .button("⟲")
168 |                 .on_hover_text("Reset to defaults")
169 |                 .clicked()
170 |             {
171 |                 *self = Self::default();
172 |             }
173 | 
174 |             ui.set_width(ui.available_width());
175 |             ui.style_mut().override_text_style = Some(egui::TextStyle::Monospace);
176 |             ui.spacing_mut().item_spacing.x = 0.0;
177 |             let align_combobox = |ui: &mut Ui, label: &str, align: &mut Align2| {
178 |                 let aligns = [
179 |                     (Align2::LEFT_TOP, "LEFT_TOP"),
180 |                     (Align2::LEFT_CENTER, "LEFT_CENTER"),
181 |                     (Align2::LEFT_BOTTOM, "LEFT_BOTTOM"),
182 |                     (Align2::CENTER_TOP, "CENTER_TOP"),
183 |                     (Align2::CENTER_CENTER, "CENTER_CENTER"),
184 |                     (Align2::CENTER_BOTTOM, "CENTER_BOTTOM"),
185 |                     (Align2::RIGHT_TOP, "RIGHT_TOP"),
186 |                     (Align2::RIGHT_CENTER, "RIGHT_CENTER"),
187 |                     (Align2::RIGHT_BOTTOM, "RIGHT_BOTTOM"),
188 |                 ];
189 | 
190 |                 ComboBox::new(label, "")
191 |                     .selected_text(aligns.iter().find(|(a, _)| a == align).unwrap().1)
192 |                     .show_ui(ui, |ui| {
193 |                         for (align2, name) in &aligns {
194 |                             ui.selectable_value(align, *align2, *name);
195 |                         }
196 |                     });
197 |             };
198 | 
199 |             rust_view_ui(ui, "let align = RectAlign {");
200 |             ui.horizontal(|ui| {
201 |                 rust_view_ui(ui, "    parent: Align2::");
202 |                 align_combobox(ui, "parent", &mut self.align4.parent);
203 |                 rust_view_ui(ui, ",");
204 |             });
205 |             ui.horizontal(|ui| {
206 |                 rust_view_ui(ui, "    child: Align2::");
207 |                 align_combobox(ui, "child", &mut self.align4.child);
208 |                 rust_view_ui(ui, ",");
209 |             });
210 |             rust_view_ui(ui, "};");
211 | 
212 |             ui.horizontal(|ui| {
213 |                 rust_view_ui(ui, "let align = RectAlign::");
214 | 
215 |                 let presets = [
216 |                     (RectAlign::TOP_START, "TOP_START"),
217 |                     (RectAlign::TOP, "TOP"),
218 |                     (RectAlign::TOP_END, "TOP_END"),
219 |                     (RectAlign::RIGHT_START, "RIGHT_START"),
220 |                     (RectAlign::RIGHT, "RIGHT"),
221 |                     (RectAlign::RIGHT_END, "RIGHT_END"),
222 |                     (RectAlign::BOTTOM_START, "BOTTOM_START"),
223 |                     (RectAlign::BOTTOM, "BOTTOM"),
224 |                     (RectAlign::BOTTOM_END, "BOTTOM_END"),
225 |                     (RectAlign::LEFT_START, "LEFT_START"),
226 |                     (RectAlign::LEFT, "LEFT"),
227 |                     (RectAlign::LEFT_END, "LEFT_END"),
228 |                 ];
229 | 
230 |                 ComboBox::new("Preset", "")
231 |                     .selected_text(
232 |                         presets
233 |                             .iter()
234 |                             .find(|(a, _)| a == &self.align4)
235 |                             .map_or("<Select Preset>", |(_, name)| *name),
236 |                     )
237 |                     .show_ui(ui, |ui| {
238 |                         for (align4, name) in &presets {
239 |                             ui.selectable_value(&mut self.align4, *align4, *name);
240 |                         }
241 |                     });
242 |                 rust_view_ui(ui, ";");
243 |             });
244 | 
245 |             ui.horizontal(|ui| {
246 |                 rust_view_ui(ui, "let gap = ");
247 |                 ui.add(egui::DragValue::new(&mut self.gap));
248 |                 rust_view_ui(ui, ";");
249 |             });
250 | 
251 |             rust_view_ui(ui, "let close_behavior");
252 |             ui.horizontal(|ui| {
253 |                 rust_view_ui(ui, "    = PopupCloseBehavior::");
254 |                 let close_behaviors = [
255 |                     (
256 |                         PopupCloseBehavior::CloseOnClick,
257 |                         "CloseOnClick",
258 |                         "Closes when the user clicks anywhere (inside or outside)",
259 |                     ),
260 |                     (
261 |                         PopupCloseBehavior::CloseOnClickOutside,
262 |                         "CloseOnClickOutside",
263 |                         "Closes when the user clicks outside the popup",
264 |                     ),
265 |                     (
266 |                         PopupCloseBehavior::IgnoreClicks,
267 |                         "IgnoreClicks",
268 |                         "Close only when the button is clicked again",
269 |                     ),
270 |                 ];
271 |                 ComboBox::new("Close behavior", "")
272 |                     .selected_text(
273 |                         close_behaviors
274 |                             .iter()
275 |                             .find_map(|(behavior, text, _)| {
276 |                                 (behavior == &self.close_behavior).then_some(*text)
277 |                             })
278 |                             .unwrap(),
279 |                     )
280 |                     .show_ui(ui, |ui| {
281 |                         for (close_behavior, name, tooltip) in &close_behaviors {
282 |                             ui.selectable_value(&mut self.close_behavior, *close_behavior, *name)
283 |                                 .on_hover_text(*tooltip);
284 |                         }
285 |                     });
286 |                 rust_view_ui(ui, ";");
287 |             });
288 | 
289 |             ui.horizontal(|ui| {
290 |                 rust_view_ui(ui, "let popup_open = ");
291 |                 ui.checkbox(&mut self.popup_open, "");
292 |                 rust_view_ui(ui, ";");
293 |             });
294 |             ui.monospace("");
295 |             rust_view_ui(ui, "let response = ui.button(\"Click me!\");");
296 |             rust_view_ui(ui, "Popup::menu(&response)");
297 |             rust_view_ui(ui, "    .gap(gap).align(align)");
298 |             rust_view_ui(ui, "    .close_behavior(close_behavior)");
299 |             rust_view_ui(ui, "    .show(|ui| { /* menu contents */ });");
300 |         });
301 | 
302 |         ui.vertical_centered(|ui| {
303 |             ui.add(crate::egui_github_link_file!());
304 |         });
305 |     }
306 | }
307 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/scene.rs:
--------------------------------------------------------------------------------
 1 | use egui::{Pos2, Rect, Scene, Vec2};
 2 | 
 3 | use super::widget_gallery;
 4 | 
 5 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 6 | pub struct SceneDemo {
 7 |     widget_gallery: widget_gallery::WidgetGallery,
 8 |     scene_rect: Rect,
 9 | }
10 | 
11 | impl Default for SceneDemo {
12 |     fn default() -> Self {
13 |         Self {
14 |             widget_gallery: widget_gallery::WidgetGallery::default().with_date_button(false), // disable date button so that we don't fail the snapshot test
15 |             scene_rect: Rect::ZERO, // `egui::Scene` will initialize this to something valid
16 |         }
17 |     }
18 | }
19 | 
20 | impl crate::Demo for SceneDemo {
21 |     fn name(&self) -> &'static str {
22 |         "🔍 Scene"
23 |     }
24 | 
25 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
26 |         use crate::View as _;
27 |         let window = egui::Window::new("Scene")
28 |             .default_width(300.0)
29 |             .default_height(300.0)
30 |             .scroll(false)
31 |             .open(open);
32 |         window.show(ctx, |ui| self.ui(ui));
33 |     }
34 | }
35 | 
36 | impl crate::View for SceneDemo {
37 |     fn ui(&mut self, ui: &mut egui::Ui) {
38 |         ui.label(
39 |             "You can pan by scrolling, and zoom using cmd-scroll. \
40 |             Double click on the background to reset view.",
41 |         );
42 |         ui.vertical_centered(|ui| {
43 |             ui.add(crate::egui_github_link_file!());
44 |         });
45 |         ui.separator();
46 | 
47 |         ui.label(format!("Scene rect: {:#?}", &mut self.scene_rect));
48 | 
49 |         ui.separator();
50 | 
51 |         egui::Frame::group(ui.style())
52 |             .inner_margin(0.0)
53 |             .show(ui, |ui| {
54 |                 let scene = Scene::new()
55 |                     .max_inner_size([350.0, 1000.0])
56 |                     .zoom_range(0.1..=2.0);
57 | 
58 |                 let mut reset_view = false;
59 |                 let mut inner_rect = Rect::NAN;
60 |                 let response = scene
61 |                     .show(ui, &mut self.scene_rect, |ui| {
62 |                         reset_view = ui.button("Reset view").clicked();
63 | 
64 |                         ui.add_space(16.0);
65 | 
66 |                         self.widget_gallery.ui(ui);
67 | 
68 |                         ui.put(
69 |                             Rect::from_min_size(Pos2::new(0.0, -64.0), Vec2::new(200.0, 16.0)),
70 |                             egui::Label::new("You can put a widget anywhere").selectable(false),
71 |                         );
72 | 
73 |                         inner_rect = ui.min_rect();
74 |                     })
75 |                     .response;
76 | 
77 |                 if reset_view || response.double_clicked() {
78 |                     self.scene_rect = inner_rect;
79 |                 }
80 |             });
81 |     }
82 | }
83 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/screenshot.rs:
--------------------------------------------------------------------------------
 1 | use egui::{Image, UserData, ViewportCommand, Widget as _};
 2 | use std::sync::Arc;
 3 | 
 4 | /// Showcase [`ViewportCommand::Screenshot`].
 5 | #[derive(PartialEq, Eq, Default)]
 6 | pub struct Screenshot {
 7 |     image: Option<(Arc<egui::ColorImage>, egui::TextureHandle)>,
 8 |     continuous: bool,
 9 | }
10 | 
11 | impl crate::Demo for Screenshot {
12 |     fn name(&self) -> &'static str {
13 |         "📷 Screenshot"
14 |     }
15 | 
16 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
17 |         egui::Window::new(self.name())
18 |             .open(open)
19 |             .resizable(false)
20 |             .default_width(250.0)
21 |             .show(ctx, |ui| {
22 |                 use crate::View as _;
23 |                 self.ui(ui);
24 |             });
25 |     }
26 | }
27 | 
28 | impl crate::View for Screenshot {
29 |     fn ui(&mut self, ui: &mut egui::Ui) {
30 |         ui.set_width(300.0);
31 |         ui.vertical_centered(|ui| {
32 |             ui.add(crate::egui_github_link_file!());
33 |         });
34 | 
35 |         ui.horizontal_wrapped(|ui| {
36 |             ui.spacing_mut().item_spacing.x = 0.0;
37 |             ui.label("This demo showcases how to take screenshots via ");
38 |             ui.code("ViewportCommand::Screenshot");
39 |             ui.label(".");
40 |         });
41 | 
42 |         ui.horizontal_top(|ui| {
43 |             let capture = ui.button("📷 Take Screenshot").clicked();
44 |             ui.checkbox(&mut self.continuous, "Capture continuously");
45 |             if capture || self.continuous {
46 |                 ui.ctx()
47 |                     .send_viewport_cmd(ViewportCommand::Screenshot(UserData::default()));
48 |             }
49 |         });
50 | 
51 |         let image = ui.ctx().input(|i| {
52 |             i.events
53 |                 .iter()
54 |                 .filter_map(|e| {
55 |                     if let egui::Event::Screenshot { image, .. } = e {
56 |                         Some(image.clone())
57 |                     } else {
58 |                         None
59 |                     }
60 |                 })
61 |                 .next_back()
62 |         });
63 | 
64 |         if let Some(image) = image {
65 |             self.image = Some((
66 |                 image.clone(),
67 |                 ui.ctx()
68 |                     .load_texture("screenshot_demo", image, Default::default()),
69 |             ));
70 |         }
71 | 
72 |         if let Some((_, texture)) = &self.image {
73 |             Image::new(texture).shrink_to_fit().ui(ui);
74 |         } else {
75 |             ui.group(|ui| {
76 |                 ui.set_width(ui.available_width());
77 |                 ui.set_height(100.0);
78 |                 ui.centered_and_justified(|ui| {
79 |                     ui.label("No screenshot taken yet.");
80 |                 });
81 |             });
82 |         }
83 |     }
84 | }
85 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/sliders.rs:
--------------------------------------------------------------------------------
  1 | use egui::{Slider, SliderClamping, SliderOrientation, Ui, style::HandleShape};
  2 | 
  3 | /// Showcase sliders
  4 | #[derive(PartialEq)]
  5 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  6 | #[cfg_attr(feature = "serde", serde(default))]
  7 | pub struct Sliders {
  8 |     pub min: f64,
  9 |     pub max: f64,
 10 |     pub logarithmic: bool,
 11 |     pub clamping: SliderClamping,
 12 |     pub smart_aim: bool,
 13 |     pub step: f64,
 14 |     pub use_steps: bool,
 15 |     pub integer: bool,
 16 |     pub vertical: bool,
 17 |     pub value: f64,
 18 |     pub trailing_fill: bool,
 19 |     pub handle_shape: HandleShape,
 20 | }
 21 | 
 22 | impl Default for Sliders {
 23 |     fn default() -> Self {
 24 |         Self {
 25 |             min: 0.0,
 26 |             max: 10000.0,
 27 |             logarithmic: true,
 28 |             clamping: SliderClamping::Always,
 29 |             smart_aim: true,
 30 |             step: 10.0,
 31 |             use_steps: false,
 32 |             integer: false,
 33 |             vertical: false,
 34 |             value: 10.0,
 35 |             trailing_fill: false,
 36 |             handle_shape: HandleShape::Circle,
 37 |         }
 38 |     }
 39 | }
 40 | 
 41 | impl crate::Demo for Sliders {
 42 |     fn name(&self) -> &'static str {
 43 |         "⬌ Sliders"
 44 |     }
 45 | 
 46 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 47 |         egui::Window::new(self.name())
 48 |             .open(open)
 49 |             .resizable(false)
 50 |             .show(ctx, |ui| {
 51 |                 use crate::View as _;
 52 |                 self.ui(ui);
 53 |             });
 54 |     }
 55 | }
 56 | 
 57 | impl crate::View for Sliders {
 58 |     fn ui(&mut self, ui: &mut Ui) {
 59 |         let Self {
 60 |             min,
 61 |             max,
 62 |             logarithmic,
 63 |             clamping,
 64 |             smart_aim,
 65 |             step,
 66 |             use_steps,
 67 |             integer,
 68 |             vertical,
 69 |             value,
 70 |             trailing_fill,
 71 |             handle_shape,
 72 |         } = self;
 73 | 
 74 |         ui.label("You can click a slider value to edit it with the keyboard.");
 75 | 
 76 |         let (type_min, type_max) = if *integer {
 77 |             ((i32::MIN as f64), (i32::MAX as f64))
 78 |         } else if *logarithmic {
 79 |             (-f64::INFINITY, f64::INFINITY)
 80 |         } else {
 81 |             (-1e5, 1e5) // linear sliders make little sense with huge numbers
 82 |         };
 83 | 
 84 |         *min = min.clamp(type_min, type_max);
 85 |         *max = max.clamp(type_min, type_max);
 86 | 
 87 |         let orientation = if *vertical {
 88 |             SliderOrientation::Vertical
 89 |         } else {
 90 |             SliderOrientation::Horizontal
 91 |         };
 92 | 
 93 |         let istep = if *use_steps { *step } else { 0.0 };
 94 |         if *integer {
 95 |             let mut value_i32 = *value as i32;
 96 |             ui.add(
 97 |                 Slider::new(&mut value_i32, (*min as i32)..=(*max as i32))
 98 |                     .logarithmic(*logarithmic)
 99 |                     .clamping(*clamping)
100 |                     .smart_aim(*smart_aim)
101 |                     .orientation(orientation)
102 |                     .text("i32 demo slider")
103 |                     .step_by(istep)
104 |                     .trailing_fill(*trailing_fill)
105 |                     .handle_shape(*handle_shape),
106 |             );
107 |             *value = value_i32 as f64;
108 |         } else {
109 |             ui.add(
110 |                 Slider::new(value, (*min)..=(*max))
111 |                     .logarithmic(*logarithmic)
112 |                     .clamping(*clamping)
113 |                     .smart_aim(*smart_aim)
114 |                     .orientation(orientation)
115 |                     .text("f64 demo slider")
116 |                     .step_by(istep)
117 |                     .trailing_fill(*trailing_fill)
118 |                     .handle_shape(*handle_shape),
119 |             );
120 | 
121 |             ui.label(
122 |                 "Sliders will intelligently pick how many decimals to show. \
123 |                 You can always see the full precision value by hovering the value.",
124 |             );
125 | 
126 |             if ui.button("Assign PI").clicked() {
127 |                 self.value = std::f64::consts::PI;
128 |             }
129 |         }
130 | 
131 |         ui.separator();
132 | 
133 |         ui.label("Slider range:");
134 |         ui.add(
135 |             Slider::new(min, type_min..=type_max)
136 |                 .logarithmic(true)
137 |                 .smart_aim(*smart_aim)
138 |                 .text("left")
139 |                 .trailing_fill(*trailing_fill)
140 |                 .handle_shape(*handle_shape),
141 |         );
142 |         ui.add(
143 |             Slider::new(max, type_min..=type_max)
144 |                 .logarithmic(true)
145 |                 .smart_aim(*smart_aim)
146 |                 .text("right")
147 |                 .trailing_fill(*trailing_fill)
148 |                 .handle_shape(*handle_shape),
149 |         );
150 | 
151 |         ui.separator();
152 | 
153 |         ui.checkbox(trailing_fill, "Toggle trailing color");
154 |         ui.label("When enabled, trailing color will be painted up until the handle.");
155 | 
156 |         ui.separator();
157 | 
158 |         handle_shape.ui(ui);
159 | 
160 |         ui.separator();
161 | 
162 |         ui.checkbox(use_steps, "Use steps");
163 |         ui.label("When enabled, the minimal value change would be restricted to a given step.");
164 |         if *use_steps {
165 |             ui.add(egui::DragValue::new(step).speed(1.0));
166 |         }
167 | 
168 |         ui.separator();
169 | 
170 |         ui.horizontal(|ui| {
171 |             ui.label("Slider type:");
172 |             ui.radio_value(integer, true, "i32");
173 |             ui.radio_value(integer, false, "f64");
174 |         })
175 |         .response
176 |         .on_hover_text("All numeric types (f32, usize, …) are supported.");
177 | 
178 |         ui.horizontal(|ui| {
179 |             ui.label("Slider orientation:");
180 |             ui.radio_value(vertical, false, "Horizontal");
181 |             ui.radio_value(vertical, true, "Vertical");
182 |         });
183 |         ui.add_space(8.0);
184 | 
185 |         ui.checkbox(logarithmic, "Logarithmic");
186 |         ui.label("Logarithmic sliders are great for when you want to span a huge range, i.e. from zero to a million.");
187 |         ui.label("Logarithmic sliders can include infinity and zero.");
188 |         ui.add_space(8.0);
189 | 
190 |         ui.horizontal(|ui| {
191 |             ui.label("Clamping:");
192 |             ui.selectable_value(clamping, SliderClamping::Never, "Never");
193 |             ui.selectable_value(clamping, SliderClamping::Edits, "Edits");
194 |             ui.selectable_value(clamping, SliderClamping::Always, "Always");
195 |         });
196 |         ui.label("If true, the slider will clamp incoming and outgoing values to the given range.");
197 |         ui.label("If false, the slider can show values outside its range, and you cannot enter new values outside the range.");
198 |         ui.add_space(8.0);
199 | 
200 |         ui.checkbox(smart_aim, "Smart Aim");
201 |         ui.label("Smart Aim will guide you towards round values when you drag the slider so you you are more likely to hit 250 than 247.23");
202 |         ui.add_space(8.0);
203 | 
204 |         ui.vertical_centered(|ui| {
205 |             egui::reset_button(ui, self, "Reset");
206 |             ui.add(crate::egui_github_link_file!());
207 |         });
208 |     }
209 | }
210 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/strip_demo.rs:
--------------------------------------------------------------------------------
  1 | use egui::{Color32, TextStyle};
  2 | use egui_extras::{Size, StripBuilder};
  3 | 
  4 | /// Shows off a table with dynamic layout
  5 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  6 | #[derive(Default)]
  7 | pub struct StripDemo {}
  8 | 
  9 | impl crate::Demo for StripDemo {
 10 |     fn name(&self) -> &'static str {
 11 |         "▣ Strip"
 12 |     }
 13 | 
 14 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 15 |         egui::Window::new(self.name())
 16 |             .open(open)
 17 |             .resizable(true)
 18 |             .default_width(400.0)
 19 |             .show(ctx, |ui| {
 20 |                 use crate::View as _;
 21 |                 self.ui(ui);
 22 |             });
 23 |     }
 24 | }
 25 | 
 26 | impl crate::View for StripDemo {
 27 |     fn ui(&mut self, ui: &mut egui::Ui) {
 28 |         let dark_mode = ui.visuals().dark_mode;
 29 |         let faded_color = ui.visuals().window_fill();
 30 |         let faded_color = |color: Color32| -> Color32 {
 31 |             use egui::Rgba;
 32 |             let t = if dark_mode { 0.95 } else { 0.8 };
 33 |             egui::lerp(Rgba::from(color)..=Rgba::from(faded_color), t).into()
 34 |         };
 35 | 
 36 |         let body_text_size = TextStyle::Body.resolve(ui.style()).size;
 37 |         StripBuilder::new(ui)
 38 |             .size(Size::exact(50.0))
 39 |             .size(Size::remainder())
 40 |             .size(Size::relative(0.5).at_least(60.0))
 41 |             .size(Size::exact(body_text_size))
 42 |             .vertical(|mut strip| {
 43 |                 strip.cell(|ui| {
 44 |                     ui.painter().rect_filled(
 45 |                         ui.available_rect_before_wrap(),
 46 |                         0.0,
 47 |                         faded_color(Color32::BLUE),
 48 |                     );
 49 |                     ui.label("width: 100%\nheight: 50px");
 50 |                 });
 51 |                 strip.strip(|builder| {
 52 |                     builder.sizes(Size::remainder(), 2).horizontal(|mut strip| {
 53 |                         strip.cell(|ui| {
 54 |                             ui.painter().rect_filled(
 55 |                                 ui.available_rect_before_wrap(),
 56 |                                 0.0,
 57 |                                 faded_color(Color32::RED),
 58 |                             );
 59 |                             ui.label("width: 50%\nheight: remaining");
 60 |                         });
 61 |                         strip.strip(|builder| {
 62 |                             builder.sizes(Size::remainder(), 3).vertical(|mut strip| {
 63 |                                 strip.empty();
 64 |                                 strip.cell(|ui| {
 65 |                                     ui.painter().rect_filled(
 66 |                                         ui.available_rect_before_wrap(),
 67 |                                         0.0,
 68 |                                         faded_color(Color32::YELLOW),
 69 |                                     );
 70 |                                     ui.label("width: 50%\nheight: 1/3 of the red region");
 71 |                                 });
 72 |                                 strip.empty();
 73 |                             });
 74 |                         });
 75 |                     });
 76 |                 });
 77 |                 strip.strip(|builder| {
 78 |                     builder
 79 |                         .size(Size::remainder())
 80 |                         .size(Size::exact(120.0))
 81 |                         .size(Size::remainder())
 82 |                         .size(Size::exact(70.0))
 83 |                         .horizontal(|mut strip| {
 84 |                             strip.empty();
 85 |                             strip.strip(|builder| {
 86 |                                 builder
 87 |                                     .size(Size::remainder())
 88 |                                     .size(Size::exact(60.0))
 89 |                                     .size(Size::remainder())
 90 |                                     .vertical(|mut strip| {
 91 |                                         strip.empty();
 92 |                                         strip.cell(|ui| {
 93 |                                             ui.painter().rect_filled(
 94 |                                                 ui.available_rect_before_wrap(),
 95 |                                                 0.0,
 96 |                                                 faded_color(Color32::GOLD),
 97 |                                             );
 98 |                                             ui.label("width: 120px\nheight: 60px");
 99 |                                         });
100 |                                     });
101 |                             });
102 |                             strip.empty();
103 |                             strip.cell(|ui| {
104 |                                 ui.painter().rect_filled(
105 |                                     ui.available_rect_before_wrap(),
106 |                                     0.0,
107 |                                     faded_color(Color32::GREEN),
108 |                                 );
109 |                                 ui.label("width: 70px\n\nheight: 50%, but at least 60px.");
110 |                             });
111 |                         });
112 |                 });
113 |                 strip.cell(|ui| {
114 |                     ui.vertical_centered(|ui| {
115 |                         ui.add(crate::egui_github_link_file!());
116 |                     });
117 |                 });
118 |             });
119 |     }
120 | }
121 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/table_demo.rs:
--------------------------------------------------------------------------------
  1 | use egui::{TextStyle, TextWrapMode};
  2 | 
  3 | #[derive(PartialEq)]
  4 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  5 | enum DemoType {
  6 |     Manual,
  7 |     ManyHomogeneous,
  8 |     ManyHeterogenous,
  9 | }
 10 | 
 11 | /// Shows off a table with dynamic layout
 12 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 13 | pub struct TableDemo {
 14 |     demo: DemoType,
 15 |     striped: bool,
 16 |     overline: bool,
 17 |     resizable: bool,
 18 |     clickable: bool,
 19 |     num_rows: usize,
 20 |     scroll_to_row_slider: usize,
 21 |     scroll_to_row: Option<usize>,
 22 |     selection: std::collections::HashSet<usize>,
 23 |     checked: bool,
 24 |     reversed: bool,
 25 | }
 26 | 
 27 | impl Default for TableDemo {
 28 |     fn default() -> Self {
 29 |         Self {
 30 |             demo: DemoType::Manual,
 31 |             striped: true,
 32 |             overline: true,
 33 |             resizable: true,
 34 |             clickable: true,
 35 |             num_rows: 10_000,
 36 |             scroll_to_row_slider: 0,
 37 |             scroll_to_row: None,
 38 |             selection: Default::default(),
 39 |             checked: false,
 40 |             reversed: false,
 41 |         }
 42 |     }
 43 | }
 44 | 
 45 | impl crate::Demo for TableDemo {
 46 |     fn name(&self) -> &'static str {
 47 |         "☰ Table"
 48 |     }
 49 | 
 50 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 51 |         egui::Window::new(self.name())
 52 |             .open(open)
 53 |             .default_width(400.0)
 54 |             .show(ctx, |ui| {
 55 |                 use crate::View as _;
 56 |                 self.ui(ui);
 57 |             });
 58 |     }
 59 | }
 60 | 
 61 | const NUM_MANUAL_ROWS: usize = 20;
 62 | 
 63 | impl crate::View for TableDemo {
 64 |     fn ui(&mut self, ui: &mut egui::Ui) {
 65 |         let mut reset = false;
 66 | 
 67 |         ui.vertical(|ui| {
 68 |             ui.horizontal(|ui| {
 69 |                 ui.checkbox(&mut self.striped, "Striped");
 70 |                 ui.checkbox(&mut self.overline, "Overline some rows");
 71 |                 ui.checkbox(&mut self.resizable, "Resizable columns");
 72 |                 ui.checkbox(&mut self.clickable, "Clickable rows");
 73 |             });
 74 | 
 75 |             ui.label("Table type:");
 76 |             ui.radio_value(&mut self.demo, DemoType::Manual, "Few, manual rows");
 77 |             ui.radio_value(
 78 |                 &mut self.demo,
 79 |                 DemoType::ManyHomogeneous,
 80 |                 "Thousands of rows of same height",
 81 |             );
 82 |             ui.radio_value(
 83 |                 &mut self.demo,
 84 |                 DemoType::ManyHeterogenous,
 85 |                 "Thousands of rows of differing heights",
 86 |             );
 87 | 
 88 |             if self.demo != DemoType::Manual {
 89 |                 ui.add(
 90 |                     egui::Slider::new(&mut self.num_rows, 0..=100_000)
 91 |                         .logarithmic(true)
 92 |                         .text("Num rows"),
 93 |                 );
 94 |             }
 95 | 
 96 |             {
 97 |                 let max_rows = if self.demo == DemoType::Manual {
 98 |                     NUM_MANUAL_ROWS
 99 |                 } else {
100 |                     self.num_rows
101 |                 };
102 | 
103 |                 let slider_response = ui.add(
104 |                     egui::Slider::new(&mut self.scroll_to_row_slider, 0..=max_rows)
105 |                         .logarithmic(true)
106 |                         .text("Row to scroll to"),
107 |                 );
108 |                 if slider_response.changed() {
109 |                     self.scroll_to_row = Some(self.scroll_to_row_slider);
110 |                 }
111 |             }
112 | 
113 |             reset = ui.button("Reset").clicked();
114 |         });
115 | 
116 |         ui.separator();
117 | 
118 |         // Leave room for the source code link after the table demo:
119 |         let body_text_size = TextStyle::Body.resolve(ui.style()).size;
120 |         use egui_extras::{Size, StripBuilder};
121 |         StripBuilder::new(ui)
122 |             .size(Size::remainder().at_least(100.0)) // for the table
123 |             .size(Size::exact(body_text_size)) // for the source code link
124 |             .vertical(|mut strip| {
125 |                 strip.cell(|ui| {
126 |                     egui::ScrollArea::horizontal().show(ui, |ui| {
127 |                         self.table_ui(ui, reset);
128 |                     });
129 |                 });
130 |                 strip.cell(|ui| {
131 |                     ui.vertical_centered(|ui| {
132 |                         ui.add(crate::egui_github_link_file!());
133 |                     });
134 |                 });
135 |             });
136 |     }
137 | }
138 | 
139 | impl TableDemo {
140 |     fn table_ui(&mut self, ui: &mut egui::Ui, reset: bool) {
141 |         use egui_extras::{Column, TableBuilder};
142 | 
143 |         let text_height = egui::TextStyle::Body
144 |             .resolve(ui.style())
145 |             .size
146 |             .max(ui.spacing().interact_size.y);
147 | 
148 |         let available_height = ui.available_height();
149 |         let mut table = TableBuilder::new(ui)
150 |             .striped(self.striped)
151 |             .resizable(self.resizable)
152 |             .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
153 |             .column(Column::auto())
154 |             .column(
155 |                 Column::remainder()
156 |                     .at_least(40.0)
157 |                     .clip(true)
158 |                     .resizable(true),
159 |             )
160 |             .column(Column::auto())
161 |             .column(Column::remainder())
162 |             .column(Column::remainder())
163 |             .min_scrolled_height(0.0)
164 |             .max_scroll_height(available_height);
165 | 
166 |         if self.clickable {
167 |             table = table.sense(egui::Sense::click());
168 |         }
169 | 
170 |         if let Some(row_index) = self.scroll_to_row.take() {
171 |             table = table.scroll_to_row(row_index, None);
172 |         }
173 | 
174 |         if reset {
175 |             table.reset();
176 |         }
177 | 
178 |         table
179 |             .header(20.0, |mut header| {
180 |                 header.col(|ui| {
181 |                     egui::Sides::new().show(
182 |                         ui,
183 |                         |ui| {
184 |                             ui.strong("Row");
185 |                         },
186 |                         |ui| {
187 |                             self.reversed ^=
188 |                                 ui.button(if self.reversed { "⬆" } else { "⬇" }).clicked();
189 |                         },
190 |                     );
191 |                 });
192 |                 header.col(|ui| {
193 |                     ui.strong("Clipped text");
194 |                 });
195 |                 header.col(|ui| {
196 |                     ui.strong("Expanding content");
197 |                 });
198 |                 header.col(|ui| {
199 |                     ui.strong("Interaction");
200 |                 });
201 |                 header.col(|ui| {
202 |                     ui.strong("Content");
203 |                 });
204 |             })
205 |             .body(|mut body| match self.demo {
206 |                 DemoType::Manual => {
207 |                     for row_index in 0..NUM_MANUAL_ROWS {
208 |                         let row_index = if self.reversed {
209 |                             NUM_MANUAL_ROWS - 1 - row_index
210 |                         } else {
211 |                             row_index
212 |                         };
213 | 
214 |                         let is_thick = thick_row(row_index);
215 |                         let row_height = if is_thick { 30.0 } else { 18.0 };
216 |                         body.row(row_height, |mut row| {
217 |                             row.set_selected(self.selection.contains(&row_index));
218 |                             row.set_overline(self.overline && row_index % 7 == 3);
219 | 
220 |                             row.col(|ui| {
221 |                                 ui.label(row_index.to_string());
222 |                             });
223 |                             row.col(|ui| {
224 |                                 ui.label(long_text(row_index));
225 |                             });
226 |                             row.col(|ui| {
227 |                                 expanding_content(ui);
228 |                             });
229 |                             row.col(|ui| {
230 |                                 ui.checkbox(&mut self.checked, "Click me");
231 |                             });
232 |                             row.col(|ui| {
233 |                                 ui.style_mut().wrap_mode = Some(egui::TextWrapMode::Extend);
234 |                                 if is_thick {
235 |                                     ui.heading("Extra thick row");
236 |                                 } else {
237 |                                     ui.label("Normal row");
238 |                                 }
239 |                             });
240 | 
241 |                             self.toggle_row_selection(row_index, &row.response());
242 |                         });
243 |                     }
244 |                 }
245 |                 DemoType::ManyHomogeneous => {
246 |                     body.rows(text_height, self.num_rows, |mut row| {
247 |                         let row_index = if self.reversed {
248 |                             self.num_rows - 1 - row.index()
249 |                         } else {
250 |                             row.index()
251 |                         };
252 | 
253 |                         row.set_selected(self.selection.contains(&row_index));
254 |                         row.set_overline(self.overline && row_index % 7 == 3);
255 | 
256 |                         row.col(|ui| {
257 |                             ui.label(row_index.to_string());
258 |                         });
259 |                         row.col(|ui| {
260 |                             ui.label(long_text(row_index));
261 |                         });
262 |                         row.col(|ui| {
263 |                             expanding_content(ui);
264 |                         });
265 |                         row.col(|ui| {
266 |                             ui.checkbox(&mut self.checked, "Click me");
267 |                         });
268 |                         row.col(|ui| {
269 |                             ui.add(
270 |                                 egui::Label::new("Thousands of rows of even height")
271 |                                     .wrap_mode(TextWrapMode::Extend),
272 |                             );
273 |                         });
274 | 
275 |                         self.toggle_row_selection(row_index, &row.response());
276 |                     });
277 |                 }
278 |                 DemoType::ManyHeterogenous => {
279 |                     let row_height = |i: usize| if thick_row(i) { 30.0 } else { 18.0 };
280 |                     body.heterogeneous_rows((0..self.num_rows).map(row_height), |mut row| {
281 |                         let row_index = if self.reversed {
282 |                             self.num_rows - 1 - row.index()
283 |                         } else {
284 |                             row.index()
285 |                         };
286 | 
287 |                         row.set_selected(self.selection.contains(&row_index));
288 |                         row.set_overline(self.overline && row_index % 7 == 3);
289 | 
290 |                         row.col(|ui| {
291 |                             ui.label(row_index.to_string());
292 |                         });
293 |                         row.col(|ui| {
294 |                             ui.label(long_text(row_index));
295 |                         });
296 |                         row.col(|ui| {
297 |                             expanding_content(ui);
298 |                         });
299 |                         row.col(|ui| {
300 |                             ui.checkbox(&mut self.checked, "Click me");
301 |                         });
302 |                         row.col(|ui| {
303 |                             ui.style_mut().wrap_mode = Some(egui::TextWrapMode::Extend);
304 |                             if thick_row(row_index) {
305 |                                 ui.heading("Extra thick row");
306 |                             } else {
307 |                                 ui.label("Normal row");
308 |                             }
309 |                         });
310 | 
311 |                         self.toggle_row_selection(row_index, &row.response());
312 |                     });
313 |                 }
314 |             });
315 |     }
316 | 
317 |     fn toggle_row_selection(&mut self, row_index: usize, row_response: &egui::Response) {
318 |         if row_response.clicked() {
319 |             if self.selection.contains(&row_index) {
320 |                 self.selection.remove(&row_index);
321 |             } else {
322 |                 self.selection.insert(row_index);
323 |             }
324 |         }
325 |     }
326 | }
327 | 
328 | fn expanding_content(ui: &mut egui::Ui) {
329 |     ui.add(egui::Separator::default().horizontal());
330 | }
331 | 
332 | fn long_text(row_index: usize) -> String {
333 |     format!(
334 |         "Row {row_index} has some long text that you may want to clip, or it will take up too much horizontal space!"
335 |     )
336 | }
337 | 
338 | fn thick_row(row_index: usize) -> bool {
339 |     row_index % 6 == 0
340 | }
341 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/clipboard_test.rs:
--------------------------------------------------------------------------------
 1 | pub struct ClipboardTest {
 2 |     text: String,
 3 | }
 4 | 
 5 | impl Default for ClipboardTest {
 6 |     fn default() -> Self {
 7 |         Self {
 8 |             text: "Example text you can copy-and-paste".to_owned(),
 9 |         }
10 |     }
11 | }
12 | 
13 | impl crate::Demo for ClipboardTest {
14 |     fn name(&self) -> &'static str {
15 |         "Clipboard Test"
16 |     }
17 | 
18 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
19 |         egui::Window::new(self.name()).open(open).show(ctx, |ui| {
20 |             use crate::View as _;
21 |             self.ui(ui);
22 |         });
23 |     }
24 | }
25 | 
26 | impl crate::View for ClipboardTest {
27 |     fn ui(&mut self, ui: &mut egui::Ui) {
28 |         ui.label("egui integrates with the system clipboard.");
29 |         ui.label("Try copy-cut-pasting text in the text edit below.");
30 | 
31 |         let text_edit_response = ui
32 |             .horizontal(|ui| {
33 |                 let text_edit_response = ui.text_edit_singleline(&mut self.text);
34 |                 if ui.button("📋").clicked() {
35 |                     ui.ctx().copy_text(self.text.clone());
36 |                 }
37 |                 text_edit_response
38 |             })
39 |             .inner;
40 | 
41 |         if !cfg!(target_arch = "wasm32") {
42 |             // These commands are not yet implemented on web
43 |             ui.horizontal(|ui| {
44 |                 for (name, cmd) in [
45 |                     ("Copy", egui::ViewportCommand::RequestCopy),
46 |                     ("Cut", egui::ViewportCommand::RequestCut),
47 |                     ("Paste", egui::ViewportCommand::RequestPaste),
48 |                 ] {
49 |                     if ui.button(name).clicked() {
50 |                         // Next frame we should get a copy/cut/paste-event…
51 |                         ui.ctx().send_viewport_cmd(cmd);
52 | 
53 |                         // …that should en up here:
54 |                         text_edit_response.request_focus();
55 |                     }
56 |                 }
57 |             });
58 |         }
59 | 
60 |         ui.separator();
61 | 
62 |         ui.label("You can also copy images:");
63 |         ui.horizontal(|ui| {
64 |             let image_source = egui::include_image!("../../../data/icon.png");
65 |             let uri = image_source.uri().unwrap().to_owned();
66 |             ui.image(image_source);
67 | 
68 |             if let Ok(egui::load::ImagePoll::Ready { image }) =
69 |                 ui.ctx().try_load_image(&uri, Default::default())
70 |             {
71 |                 if ui.button("📋").clicked() {
72 |                     ui.ctx().copy_image((*image).clone());
73 |                 }
74 |             }
75 |         });
76 | 
77 |         ui.vertical_centered_justified(|ui| {
78 |             ui.add(crate::egui_github_link_file!());
79 |         });
80 |     }
81 | }
82 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/cursor_test.rs:
--------------------------------------------------------------------------------
 1 | #[derive(Default)]
 2 | pub struct CursorTest {}
 3 | 
 4 | impl crate::Demo for CursorTest {
 5 |     fn name(&self) -> &'static str {
 6 |         "Cursor Test"
 7 |     }
 8 | 
 9 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
10 |         egui::Window::new(self.name()).open(open).show(ctx, |ui| {
11 |             use crate::View as _;
12 |             self.ui(ui);
13 |         });
14 |     }
15 | }
16 | 
17 | impl crate::View for CursorTest {
18 |     fn ui(&mut self, ui: &mut egui::Ui) {
19 |         ui.vertical_centered_justified(|ui| {
20 |             ui.heading("Hover to switch cursor icon:");
21 |             for &cursor_icon in &egui::CursorIcon::ALL {
22 |                 let _ = ui
23 |                     .button(format!("{cursor_icon:?}"))
24 |                     .on_hover_cursor(cursor_icon);
25 |             }
26 |             ui.add(crate::egui_github_link_file!());
27 |         });
28 |     }
29 | }
30 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/grid_test.rs:
--------------------------------------------------------------------------------
  1 | #[derive(PartialEq)]
  2 | pub struct GridTest {
  3 |     num_cols: usize,
  4 |     num_rows: usize,
  5 |     min_col_width: f32,
  6 |     max_col_width: f32,
  7 |     text_length: usize,
  8 | }
  9 | 
 10 | impl Default for GridTest {
 11 |     fn default() -> Self {
 12 |         Self {
 13 |             num_cols: 4,
 14 |             num_rows: 4,
 15 |             min_col_width: 10.0,
 16 |             max_col_width: 200.0,
 17 |             text_length: 10,
 18 |         }
 19 |     }
 20 | }
 21 | 
 22 | impl crate::Demo for GridTest {
 23 |     fn name(&self) -> &'static str {
 24 |         "Grid Test"
 25 |     }
 26 | 
 27 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 28 |         egui::Window::new(self.name()).open(open).show(ctx, |ui| {
 29 |             use crate::View as _;
 30 |             self.ui(ui);
 31 |         });
 32 |     }
 33 | }
 34 | 
 35 | impl crate::View for GridTest {
 36 |     fn ui(&mut self, ui: &mut egui::Ui) {
 37 |         ui.add(
 38 |             egui::Slider::new(&mut self.min_col_width, 0.0..=400.0).text("Minimum column width"),
 39 |         );
 40 |         ui.add(
 41 |             egui::Slider::new(&mut self.max_col_width, 0.0..=400.0).text("Maximum column width"),
 42 |         );
 43 |         ui.add(egui::Slider::new(&mut self.num_cols, 0..=5).text("Columns"));
 44 |         ui.add(egui::Slider::new(&mut self.num_rows, 0..=20).text("Rows"));
 45 | 
 46 |         ui.separator();
 47 | 
 48 |         let words = [
 49 |             "random", "words", "in", "a", "random", "order", "that", "just", "keeps", "going",
 50 |             "with", "some", "more",
 51 |         ];
 52 | 
 53 |         egui::Grid::new("my_grid")
 54 |             .striped(true)
 55 |             .min_col_width(self.min_col_width)
 56 |             .max_col_width(self.max_col_width)
 57 |             .show(ui, |ui| {
 58 |                 for row in 0..self.num_rows {
 59 |                     for col in 0..self.num_cols {
 60 |                         if col == 0 {
 61 |                             ui.label(format!("row {row}"));
 62 |                         } else {
 63 |                             let word_idx = row * 3 + col * 5;
 64 |                             let word_count = (row * 5 + col * 75) % 13;
 65 |                             let mut string = String::new();
 66 |                             for word in words.iter().cycle().skip(word_idx).take(word_count) {
 67 |                                 string += word;
 68 |                                 string += " ";
 69 |                             }
 70 |                             ui.label(string);
 71 |                         }
 72 |                     }
 73 |                     ui.end_row();
 74 |                 }
 75 |             });
 76 | 
 77 |         ui.separator();
 78 |         ui.add(egui::Slider::new(&mut self.text_length, 1..=40).text("Text length"));
 79 |         egui::Grid::new("parent grid").striped(true).show(ui, |ui| {
 80 |             ui.vertical(|ui| {
 81 |                 ui.label("Vertical nest1");
 82 |                 ui.label("Vertical nest2");
 83 |             });
 84 |             ui.label("First row, second column");
 85 |             ui.end_row();
 86 | 
 87 |             ui.horizontal(|ui| {
 88 |                 ui.label("Horizontal nest1");
 89 |                 ui.label("Horizontal nest2");
 90 |             });
 91 |             ui.label("Second row, second column");
 92 |             ui.end_row();
 93 | 
 94 |             ui.scope(|ui| {
 95 |                 ui.label("Scope nest 1");
 96 |                 ui.label("Scope nest 2");
 97 |             });
 98 |             ui.label("Third row, second column");
 99 |             ui.end_row();
100 | 
101 |             egui::Grid::new("nested grid").show(ui, |ui| {
102 |                 ui.label("Grid nest11");
103 |                 ui.label("Grid nest12");
104 |                 ui.end_row();
105 |                 ui.label("Grid nest21");
106 |                 ui.label("Grid nest22");
107 |                 ui.end_row();
108 |             });
109 |             ui.label("Fourth row, second column");
110 |             ui.end_row();
111 | 
112 |             let mut dyn_text = String::from("O");
113 |             dyn_text.extend(std::iter::repeat_n('h', self.text_length));
114 |             ui.label(dyn_text);
115 |             ui.label("Fifth row, second column");
116 |             ui.end_row();
117 |         });
118 | 
119 |         ui.vertical_centered(|ui| {
120 |             egui::reset_button(ui, self, "Reset");
121 |             ui.add(crate::egui_github_link_file!());
122 |         });
123 |     }
124 | }
125 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/id_test.rs:
--------------------------------------------------------------------------------
 1 | #[derive(Default)]
 2 | pub struct IdTest {}
 3 | 
 4 | impl crate::Demo for IdTest {
 5 |     fn name(&self) -> &'static str {
 6 |         "ID Test"
 7 |     }
 8 | 
 9 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
10 |         egui::Window::new(self.name()).open(open).show(ctx, |ui| {
11 |             use crate::View as _;
12 |             self.ui(ui);
13 |         });
14 |     }
15 | }
16 | 
17 | impl crate::View for IdTest {
18 |     fn ui(&mut self, ui: &mut egui::Ui) {
19 |         // Make sure the warnings are on (by default they are only on in debug builds).
20 |         ui.ctx().options_mut(|opt| opt.warn_on_id_clash = true);
21 | 
22 |         ui.heading("Name collision example");
23 | 
24 |         ui.label("\
25 |             Widgets that store state require unique and persisting identifiers so we can track their state between frames.\n\
26 |             For instance, collapsible headers needs to store whether or not they are open. \
27 |             Their Id:s are derived from their names. \
28 |             If you fail to give them unique names then clicking one will open both. \
29 |             To help you debug this, an error message is printed on screen:");
30 | 
31 |         ui.collapsing("Collapsing header", |ui| {
32 |             ui.label("Contents of first foldable ui");
33 |         });
34 |         ui.collapsing("Collapsing header", |ui| {
35 |             ui.label("Contents of second foldable ui");
36 |         });
37 | 
38 |         ui.label("\
39 |             Any widget that can be interacted with also need a unique Id. \
40 |             For most widgets the Id is generated by a running counter. \
41 |             As long as elements are not added or removed, the Id stays the same. \
42 |             This is fine, because during interaction (i.e. while dragging a slider), \
43 |             the number of widgets previously in the same window is most likely not changing \
44 |             (and if it is, the window will have a new layout, and the slider will end up somewhere else, and so aborting the interaction probably makes sense).");
45 | 
46 |         ui.label("So these buttons have automatic Id:s, and therefore there is no name clash:");
47 |         let _ = ui.button("Button");
48 |         let _ = ui.button("Button");
49 | 
50 |         ui.vertical_centered(|ui| {
51 |             ui.add(crate::egui_github_link_file!());
52 |         });
53 |     }
54 | }
55 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/input_event_history.rs:
--------------------------------------------------------------------------------
  1 | //! Show the history of all the input events to
  2 | 
  3 | struct HistoryEntry {
  4 |     summary: String,
  5 |     entries: Vec<String>,
  6 | }
  7 | 
  8 | #[derive(Default)]
  9 | struct DeduplicatedHistory {
 10 |     history: std::collections::VecDeque<HistoryEntry>,
 11 | }
 12 | 
 13 | impl DeduplicatedHistory {
 14 |     fn add(&mut self, summary: String, full: String) {
 15 |         if let Some(entry) = self.history.back_mut() {
 16 |             if entry.summary == summary {
 17 |                 entry.entries.push(full);
 18 |                 return;
 19 |             }
 20 |         }
 21 |         self.history.push_back(HistoryEntry {
 22 |             summary,
 23 |             entries: vec![full],
 24 |         });
 25 |         if self.history.len() > 100 {
 26 |             self.history.pop_front();
 27 |         }
 28 |     }
 29 | 
 30 |     fn ui(&self, ui: &mut egui::Ui) {
 31 |         egui::ScrollArea::vertical()
 32 |             .auto_shrink(false)
 33 |             .show(ui, |ui| {
 34 |                 ui.spacing_mut().item_spacing.y = 4.0;
 35 |                 ui.style_mut().wrap_mode = Some(egui::TextWrapMode::Extend);
 36 | 
 37 |                 for HistoryEntry { summary, entries } in self.history.iter().rev() {
 38 |                     ui.horizontal(|ui| {
 39 |                         let response = ui.code(summary);
 40 |                         if entries.len() < 2 {
 41 |                             response
 42 |                         } else {
 43 |                             response | ui.weak(format!(" x{}", entries.len()))
 44 |                         }
 45 |                     })
 46 |                     .inner
 47 |                     .on_hover_ui(|ui| {
 48 |                         ui.spacing_mut().item_spacing.y = 4.0;
 49 |                         ui.style_mut().wrap_mode = Some(egui::TextWrapMode::Extend);
 50 |                         for entry in entries.iter().rev() {
 51 |                             ui.code(entry);
 52 |                         }
 53 |                     });
 54 |                 }
 55 |             });
 56 |     }
 57 | }
 58 | 
 59 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 60 | #[derive(Default)]
 61 | pub struct InputEventHistory {
 62 |     #[cfg_attr(feature = "serde", serde(skip))]
 63 |     history: DeduplicatedHistory,
 64 | 
 65 |     include_pointer_movements: bool,
 66 | }
 67 | 
 68 | impl crate::Demo for InputEventHistory {
 69 |     fn name(&self) -> &'static str {
 70 |         "Input Event History"
 71 |     }
 72 | 
 73 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 74 |         egui::Window::new(self.name())
 75 |             .default_width(800.0)
 76 |             .open(open)
 77 |             .resizable(true)
 78 |             .scroll(false)
 79 |             .show(ctx, |ui| {
 80 |                 use crate::View as _;
 81 |                 self.ui(ui);
 82 |             });
 83 |     }
 84 | }
 85 | 
 86 | impl crate::View for InputEventHistory {
 87 |     fn ui(&mut self, ui: &mut egui::Ui) {
 88 |         ui.input(|i| {
 89 |             for event in &i.raw.events {
 90 |                 if !self.include_pointer_movements
 91 |                     && matches!(
 92 |                         event,
 93 |                         egui::Event::PointerMoved { .. }
 94 |                             | egui::Event::MouseMoved { .. }
 95 |                             | egui::Event::Touch { .. }
 96 |                     )
 97 |                 {
 98 |                     continue;
 99 |                 }
100 | 
101 |                 let summary = event_summary(event);
102 |                 let full = format!("{event:#?}");
103 |                 self.history.add(summary, full);
104 |             }
105 |         });
106 | 
107 |         ui.vertical_centered(|ui| {
108 |             ui.add(crate::egui_github_link_file!());
109 |         });
110 | 
111 |         ui.label("Recent history of raw input events to egui.");
112 |         ui.label("Hover any entry for details.");
113 |         ui.checkbox(
114 |             &mut self.include_pointer_movements,
115 |             "Include pointer/mouse movements",
116 |         );
117 | 
118 |         ui.add_space(8.0);
119 | 
120 |         self.history.ui(ui);
121 |     }
122 | }
123 | 
124 | fn event_summary(event: &egui::Event) -> String {
125 |     match event {
126 |         egui::Event::PointerMoved { .. } => "PointerMoved { .. }".to_owned(),
127 |         egui::Event::MouseMoved { .. } => "MouseMoved { .. }".to_owned(),
128 |         egui::Event::Zoom { .. } => "Zoom { .. }".to_owned(),
129 |         egui::Event::Touch { phase, .. } => format!("Touch {{ phase: {phase:?}, .. }}"),
130 |         egui::Event::MouseWheel { unit, .. } => format!("MouseWheel {{ unit: {unit:?}, .. }}"),
131 | 
132 |         _ => format!("{event:?}"),
133 |     }
134 | }
135 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/input_test.rs:
--------------------------------------------------------------------------------
  1 | struct HistoryEntry {
  2 |     text: String,
  3 |     repeated: usize,
  4 | }
  5 | 
  6 | #[derive(Default)]
  7 | struct DeduplicatedHistory {
  8 |     history: std::collections::VecDeque<HistoryEntry>,
  9 | }
 10 | 
 11 | impl DeduplicatedHistory {
 12 |     fn add(&mut self, text: String) {
 13 |         if let Some(entry) = self.history.back_mut() {
 14 |             if entry.text == text {
 15 |                 entry.repeated += 1;
 16 |                 return;
 17 |             }
 18 |         }
 19 |         self.history.push_back(HistoryEntry { text, repeated: 1 });
 20 |         if self.history.len() > 100 {
 21 |             self.history.pop_front();
 22 |         }
 23 |     }
 24 | 
 25 |     fn ui(&self, ui: &mut egui::Ui) {
 26 |         egui::ScrollArea::vertical()
 27 |             .auto_shrink(false)
 28 |             .show(ui, |ui| {
 29 |                 ui.spacing_mut().item_spacing.y = 4.0;
 30 |                 for HistoryEntry { text, repeated } in self.history.iter().rev() {
 31 |                     ui.horizontal(|ui| {
 32 |                         if text.is_empty() {
 33 |                             ui.weak("(empty)");
 34 |                         } else {
 35 |                             ui.label(text);
 36 |                         }
 37 |                         if 1 < *repeated {
 38 |                             ui.weak(format!(" x{repeated}"));
 39 |                         }
 40 |                     });
 41 |                 }
 42 |             });
 43 |     }
 44 | }
 45 | 
 46 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 47 | #[derive(Default)]
 48 | pub struct InputTest {
 49 |     #[cfg_attr(feature = "serde", serde(skip))]
 50 |     history: [DeduplicatedHistory; 4],
 51 | 
 52 |     late_interaction: bool,
 53 | 
 54 |     show_hovers: bool,
 55 | }
 56 | 
 57 | impl crate::Demo for InputTest {
 58 |     fn name(&self) -> &'static str {
 59 |         "Input Test"
 60 |     }
 61 | 
 62 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 63 |         egui::Window::new(self.name())
 64 |             .default_width(800.0)
 65 |             .open(open)
 66 |             .resizable(true)
 67 |             .scroll(false)
 68 |             .show(ctx, |ui| {
 69 |                 use crate::View as _;
 70 |                 self.ui(ui);
 71 |             });
 72 |     }
 73 | }
 74 | 
 75 | impl crate::View for InputTest {
 76 |     fn ui(&mut self, ui: &mut egui::Ui) {
 77 |         ui.spacing_mut().item_spacing.y = 8.0;
 78 | 
 79 |         ui.vertical_centered(|ui| {
 80 |             ui.add(crate::egui_github_link_file!());
 81 |         });
 82 | 
 83 |         ui.horizontal(|ui| {
 84 |             if ui.button("Clear").clicked() {
 85 |                 *self = Default::default();
 86 |             }
 87 | 
 88 |             ui.checkbox(&mut self.show_hovers, "Show hover state");
 89 |         });
 90 | 
 91 |         ui.checkbox(&mut self.late_interaction, "Use Response::interact");
 92 | 
 93 |         ui.label("This tests how egui::Response reports events.\n\
 94 |             The different buttons are sensitive to different things.\n\
 95 |             Try interacting with them with any mouse button by clicking, double-clicking, triple-clicking, or dragging them.");
 96 | 
 97 |         ui.columns(4, |columns| {
 98 |             for (i, (sense_name, sense)) in [
 99 |                 ("Sense::hover", egui::Sense::hover()),
100 |                 ("Sense::click", egui::Sense::click()),
101 |                 ("Sense::drag", egui::Sense::drag()),
102 |                 ("Sense::click_and_drag", egui::Sense::click_and_drag()),
103 |             ]
104 |             .into_iter()
105 |             .enumerate()
106 |             {
107 |                 columns[i].push_id(i, |ui| {
108 |                     let response = if self.late_interaction {
109 |                         let first_response =
110 |                             ui.add(egui::Button::new(sense_name).sense(egui::Sense::hover()));
111 |                         first_response.interact(sense)
112 |                     } else {
113 |                         ui.add(egui::Button::new(sense_name).sense(sense))
114 |                     };
115 |                     let info = response_summary(&response, self.show_hovers);
116 |                     self.history[i].add(info.trim().to_owned());
117 |                     self.history[i].ui(ui);
118 |                 });
119 |             }
120 |         });
121 |     }
122 | }
123 | 
124 | fn response_summary(response: &egui::Response, show_hovers: bool) -> String {
125 |     use std::fmt::Write as _;
126 | 
127 |     let mut new_info = String::new();
128 | 
129 |     if show_hovers {
130 |         if response.hovered() {
131 |             writeln!(new_info, "hovered").ok();
132 |         }
133 |         if response.contains_pointer() {
134 |             writeln!(new_info, "contains_pointer").ok();
135 |         }
136 |         if response.is_pointer_button_down_on() {
137 |             writeln!(new_info, "pointer_down_on").ok();
138 |         }
139 |         if let Some(pos) = response.interact_pointer_pos() {
140 |             writeln!(new_info, "response.interact_pointer_pos: {pos:?}").ok();
141 |         }
142 |     }
143 | 
144 |     for &button in &[
145 |         egui::PointerButton::Primary,
146 |         egui::PointerButton::Secondary,
147 |         egui::PointerButton::Middle,
148 |         egui::PointerButton::Extra1,
149 |         egui::PointerButton::Extra2,
150 |     ] {
151 |         let button_suffix = if button == egui::PointerButton::Primary {
152 |             // Reduce visual clutter in common case:
153 |             String::default()
154 |         } else {
155 |             format!(" by {button:?} button")
156 |         };
157 | 
158 |         // These are in inverse logical/chonological order, because we show them in the ui that way:
159 | 
160 |         if response.triple_clicked_by(button) {
161 |             writeln!(new_info, "Triple-clicked{button_suffix}").ok();
162 |         }
163 |         if response.double_clicked_by(button) {
164 |             writeln!(new_info, "Double-clicked{button_suffix}").ok();
165 |         }
166 |         if response.clicked_by(button) {
167 |             writeln!(new_info, "Clicked{button_suffix}").ok();
168 |         }
169 | 
170 |         if response.drag_stopped_by(button) {
171 |             writeln!(new_info, "Drag stopped{button_suffix}").ok();
172 |         }
173 |         if response.dragged_by(button) {
174 |             writeln!(new_info, "Dragged{button_suffix}").ok();
175 |         }
176 |         if response.drag_started_by(button) {
177 |             writeln!(new_info, "Drag started{button_suffix}").ok();
178 |         }
179 |     }
180 | 
181 |     if response.long_touched() {
182 |         writeln!(new_info, "Clicked with long-press").ok();
183 |     }
184 | 
185 |     new_info
186 | }
187 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/layout_test.rs:
--------------------------------------------------------------------------------
  1 | use egui::{Align, Direction, Layout, Resize, Slider, Ui, vec2};
  2 | 
  3 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  4 | #[cfg_attr(feature = "serde", serde(default))]
  5 | pub struct LayoutTest {
  6 |     // Identical to contents of `egui::Layout`
  7 |     layout: LayoutSettings,
  8 | 
  9 |     // Extra for testing wrapping:
 10 |     wrap_column_width: f32,
 11 |     wrap_row_height: f32,
 12 | }
 13 | 
 14 | impl Default for LayoutTest {
 15 |     fn default() -> Self {
 16 |         Self {
 17 |             layout: LayoutSettings::top_down(),
 18 |             wrap_column_width: 150.0,
 19 |             wrap_row_height: 20.0,
 20 |         }
 21 |     }
 22 | }
 23 | 
 24 | #[derive(Clone, Copy, PartialEq, Eq)]
 25 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 26 | #[cfg_attr(feature = "serde", serde(default))]
 27 | pub struct LayoutSettings {
 28 |     // Similar to the contents of `egui::Layout`
 29 |     main_dir: Direction,
 30 |     main_wrap: bool,
 31 |     cross_align: Align,
 32 |     cross_justify: bool,
 33 | }
 34 | 
 35 | impl Default for LayoutSettings {
 36 |     fn default() -> Self {
 37 |         Self::top_down()
 38 |     }
 39 | }
 40 | 
 41 | impl LayoutSettings {
 42 |     fn top_down() -> Self {
 43 |         Self {
 44 |             main_dir: Direction::TopDown,
 45 |             main_wrap: false,
 46 |             cross_align: Align::Min,
 47 |             cross_justify: false,
 48 |         }
 49 |     }
 50 | 
 51 |     fn top_down_justified_centered() -> Self {
 52 |         Self {
 53 |             main_dir: Direction::TopDown,
 54 |             main_wrap: false,
 55 |             cross_align: Align::Center,
 56 |             cross_justify: true,
 57 |         }
 58 |     }
 59 | 
 60 |     fn horizontal_wrapped() -> Self {
 61 |         Self {
 62 |             main_dir: Direction::LeftToRight,
 63 |             main_wrap: true,
 64 |             cross_align: Align::Center,
 65 |             cross_justify: false,
 66 |         }
 67 |     }
 68 | 
 69 |     fn layout(&self) -> Layout {
 70 |         Layout::from_main_dir_and_cross_align(self.main_dir, self.cross_align)
 71 |             .with_main_wrap(self.main_wrap)
 72 |             .with_cross_justify(self.cross_justify)
 73 |     }
 74 | }
 75 | 
 76 | impl crate::Demo for LayoutTest {
 77 |     fn name(&self) -> &'static str {
 78 |         "Layout Test"
 79 |     }
 80 | 
 81 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 82 |         egui::Window::new(self.name())
 83 |             .open(open)
 84 |             .resizable(false)
 85 |             .show(ctx, |ui| {
 86 |                 use crate::View as _;
 87 |                 self.ui(ui);
 88 |             });
 89 |     }
 90 | }
 91 | 
 92 | impl crate::View for LayoutTest {
 93 |     fn ui(&mut self, ui: &mut Ui) {
 94 |         ui.label("Tests and demonstrates the limits of the egui layouts");
 95 |         self.content_ui(ui);
 96 |         Resize::default()
 97 |             .default_size([150.0, 200.0])
 98 |             .show(ui, |ui| {
 99 |                 if self.layout.main_wrap {
100 |                     if self.layout.main_dir.is_horizontal() {
101 |                         ui.allocate_ui(
102 |                             vec2(ui.available_size_before_wrap().x, self.wrap_row_height),
103 |                             |ui| ui.with_layout(self.layout.layout(), demo_ui),
104 |                         );
105 |                     } else {
106 |                         ui.allocate_ui(
107 |                             vec2(self.wrap_column_width, ui.available_size_before_wrap().y),
108 |                             |ui| ui.with_layout(self.layout.layout(), demo_ui),
109 |                         );
110 |                     }
111 |                 } else {
112 |                     ui.with_layout(self.layout.layout(), demo_ui);
113 |                 }
114 |             });
115 |         ui.label("Resize to see effect");
116 | 
117 |         ui.vertical_centered(|ui| {
118 |             ui.add(crate::egui_github_link_file!());
119 |         });
120 |     }
121 | }
122 | 
123 | impl LayoutTest {
124 |     pub fn content_ui(&mut self, ui: &mut Ui) {
125 |         ui.horizontal(|ui| {
126 |             ui.selectable_value(&mut self.layout, LayoutSettings::top_down(), "Top-down");
127 |             ui.selectable_value(
128 |                 &mut self.layout,
129 |                 LayoutSettings::top_down_justified_centered(),
130 |                 "Top-down, centered and justified",
131 |             );
132 |             ui.selectable_value(
133 |                 &mut self.layout,
134 |                 LayoutSettings::horizontal_wrapped(),
135 |                 "Horizontal wrapped",
136 |             );
137 |         });
138 | 
139 |         ui.horizontal(|ui| {
140 |             ui.label("Main Direction:");
141 |             for &dir in &[
142 |                 Direction::LeftToRight,
143 |                 Direction::RightToLeft,
144 |                 Direction::TopDown,
145 |                 Direction::BottomUp,
146 |             ] {
147 |                 ui.radio_value(&mut self.layout.main_dir, dir, format!("{dir:?}"));
148 |             }
149 |         });
150 | 
151 |         ui.horizontal(|ui| {
152 |             ui.checkbox(&mut self.layout.main_wrap, "Main wrap")
153 |                 .on_hover_text("Wrap when next widget doesn't fit the current row/column");
154 | 
155 |             if self.layout.main_wrap {
156 |                 if self.layout.main_dir.is_horizontal() {
157 |                     ui.add(Slider::new(&mut self.wrap_row_height, 0.0..=200.0).text("Row height"));
158 |                 } else {
159 |                     ui.add(
160 |                         Slider::new(&mut self.wrap_column_width, 0.0..=200.0).text("Column width"),
161 |                     );
162 |                 }
163 |             }
164 |         });
165 | 
166 |         ui.horizontal(|ui| {
167 |             ui.label("Cross Align:");
168 |             for &align in &[Align::Min, Align::Center, Align::Max] {
169 |                 ui.radio_value(&mut self.layout.cross_align, align, format!("{align:?}"));
170 |             }
171 |         });
172 | 
173 |         ui.checkbox(&mut self.layout.cross_justify, "Cross Justified")
174 |             .on_hover_text("Try to fill full width/height (e.g. buttons)");
175 |     }
176 | }
177 | 
178 | fn demo_ui(ui: &mut Ui) {
179 |     ui.add(egui::Label::new("Wrapping text followed by example widgets:").wrap());
180 |     let mut dummy = false;
181 |     ui.checkbox(&mut dummy, "checkbox");
182 |     ui.radio_value(&mut dummy, false, "radio");
183 |     let _ = ui.button("button");
184 | }
185 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/manual_layout_test.rs:
--------------------------------------------------------------------------------
 1 | #[derive(Clone, Copy, Debug, PartialEq)]
 2 | enum WidgetType {
 3 |     Label,
 4 |     Button,
 5 |     TextEdit,
 6 | }
 7 | 
 8 | #[derive(Clone, Debug, PartialEq)]
 9 | pub struct ManualLayoutTest {
10 |     widget_offset: egui::Vec2,
11 |     widget_size: egui::Vec2,
12 |     widget_type: WidgetType,
13 |     text_edit_contents: String,
14 | }
15 | 
16 | impl Default for ManualLayoutTest {
17 |     fn default() -> Self {
18 |         Self {
19 |             widget_offset: egui::Vec2::splat(150.0),
20 |             widget_size: egui::vec2(200.0, 100.0),
21 |             widget_type: WidgetType::Button,
22 |             text_edit_contents: crate::LOREM_IPSUM.to_owned(),
23 |         }
24 |     }
25 | }
26 | 
27 | impl crate::Demo for ManualLayoutTest {
28 |     fn name(&self) -> &'static str {
29 |         "Manual Layout Test"
30 |     }
31 | 
32 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
33 |         egui::Window::new(self.name())
34 |             .resizable(false)
35 |             .open(open)
36 |             .show(ctx, |ui| {
37 |                 use crate::View as _;
38 |                 self.ui(ui);
39 |             });
40 |     }
41 | }
42 | 
43 | impl crate::View for ManualLayoutTest {
44 |     fn ui(&mut self, ui: &mut egui::Ui) {
45 |         egui::reset_button(ui, self, "Reset");
46 | 
47 |         let Self {
48 |             widget_offset,
49 |             widget_size,
50 |             widget_type,
51 |             text_edit_contents,
52 |         } = self;
53 |         ui.horizontal(|ui| {
54 |             ui.label("Test widget:");
55 |             ui.radio_value(widget_type, WidgetType::Button, "Button");
56 |             ui.radio_value(widget_type, WidgetType::Label, "Label");
57 |             ui.radio_value(widget_type, WidgetType::TextEdit, "TextEdit");
58 |         });
59 |         egui::Grid::new("pos_size").show(ui, |ui| {
60 |             ui.label("Widget position:");
61 |             ui.add(egui::Slider::new(&mut widget_offset.x, 0.0..=400.0));
62 |             ui.add(egui::Slider::new(&mut widget_offset.y, 0.0..=400.0));
63 |             ui.end_row();
64 | 
65 |             ui.label("Widget size:");
66 |             ui.add(egui::Slider::new(&mut widget_size.x, 0.0..=400.0));
67 |             ui.add(egui::Slider::new(&mut widget_size.y, 0.0..=400.0));
68 |             ui.end_row();
69 |         });
70 | 
71 |         let widget_rect =
72 |             egui::Rect::from_min_size(ui.min_rect().min + *widget_offset, *widget_size);
73 | 
74 |         ui.add(crate::egui_github_link_file!());
75 | 
76 |         // Showing how to place a widget anywhere in the [`Ui`]:
77 |         match *widget_type {
78 |             WidgetType::Button => {
79 |                 ui.put(widget_rect, egui::Button::new("Example button"));
80 |             }
81 |             WidgetType::Label => {
82 |                 ui.put(widget_rect, egui::Label::new("Example label"));
83 |             }
84 |             WidgetType::TextEdit => {
85 |                 ui.put(widget_rect, egui::TextEdit::multiline(text_edit_contents));
86 |             }
87 |         }
88 |     }
89 | }
90 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/mod.rs:
--------------------------------------------------------------------------------
 1 | mod clipboard_test;
 2 | mod cursor_test;
 3 | mod grid_test;
 4 | mod id_test;
 5 | mod input_event_history;
 6 | mod input_test;
 7 | mod layout_test;
 8 | mod manual_layout_test;
 9 | mod svg_test;
10 | mod tessellation_test;
11 | mod window_resize_test;
12 | 
13 | pub use clipboard_test::ClipboardTest;
14 | pub use cursor_test::CursorTest;
15 | pub use grid_test::GridTest;
16 | pub use id_test::IdTest;
17 | pub use input_event_history::InputEventHistory;
18 | pub use input_test::InputTest;
19 | pub use layout_test::LayoutTest;
20 | pub use manual_layout_test::ManualLayoutTest;
21 | pub use svg_test::SvgTest;
22 | pub use tessellation_test::TessellationTest;
23 | pub use window_resize_test::WindowResizeTest;
24 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/svg_test.rs:
--------------------------------------------------------------------------------
 1 | pub struct SvgTest {
 2 |     color: egui::Color32,
 3 | }
 4 | 
 5 | impl Default for SvgTest {
 6 |     fn default() -> Self {
 7 |         Self {
 8 |             color: egui::Color32::LIGHT_RED,
 9 |         }
10 |     }
11 | }
12 | 
13 | impl crate::Demo for SvgTest {
14 |     fn name(&self) -> &'static str {
15 |         "SVG Test"
16 |     }
17 | 
18 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
19 |         egui::Window::new(self.name()).open(open).show(ctx, |ui| {
20 |             use crate::View as _;
21 |             self.ui(ui);
22 |         });
23 |     }
24 | }
25 | 
26 | impl crate::View for SvgTest {
27 |     fn ui(&mut self, ui: &mut egui::Ui) {
28 |         let Self { color } = self;
29 |         ui.color_edit_button_srgba(color);
30 |         let img_src = egui::include_image!("../../../data/peace.svg");
31 | 
32 |         // First paint a small version, sized the same as the source…
33 |         ui.add(
34 |             egui::Image::new(img_src.clone())
35 |                 .fit_to_original_size(1.0)
36 |                 .tint(*color),
37 |         );
38 | 
39 |         // …then a big one, to make sure they are both crisp
40 |         ui.add(egui::Image::new(img_src).tint(*color));
41 |     }
42 | }
43 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/tessellation_test.rs:
--------------------------------------------------------------------------------
  1 | use egui::{
  2 |     Color32, Pos2, Rect, Sense, StrokeKind, Vec2,
  3 |     emath::{GuiRounding as _, TSTransform},
  4 |     epaint::{self, RectShape},
  5 |     vec2,
  6 | };
  7 | 
  8 | #[derive(Clone, Debug, PartialEq)]
  9 | pub struct TessellationTest {
 10 |     shape: RectShape,
 11 | 
 12 |     magnification_pixel_size: f32,
 13 |     tessellation_options: epaint::TessellationOptions,
 14 |     paint_edges: bool,
 15 | }
 16 | 
 17 | impl Default for TessellationTest {
 18 |     fn default() -> Self {
 19 |         let shape = Self::interesting_shapes()[0].1.clone();
 20 |         Self {
 21 |             shape,
 22 |             magnification_pixel_size: 12.0,
 23 |             tessellation_options: Default::default(),
 24 |             paint_edges: false,
 25 |         }
 26 |     }
 27 | }
 28 | 
 29 | impl TessellationTest {
 30 |     fn interesting_shapes() -> Vec<(&'static str, RectShape)> {
 31 |         fn sized(size: impl Into<Vec2>) -> Rect {
 32 |             Rect::from_center_size(Pos2::ZERO, size.into())
 33 |         }
 34 | 
 35 |         let baby_blue = Color32::from_rgb(0, 181, 255);
 36 | 
 37 |         let mut shapes = vec![
 38 |             (
 39 |                 "Normal",
 40 |                 RectShape::new(
 41 |                     sized([20.0, 16.0]),
 42 |                     2.0,
 43 |                     baby_blue,
 44 |                     (1.0, Color32::WHITE),
 45 |                     StrokeKind::Inside,
 46 |                 ),
 47 |             ),
 48 |             (
 49 |                 "Minimal rounding",
 50 |                 RectShape::new(
 51 |                     sized([20.0, 16.0]),
 52 |                     1.0,
 53 |                     baby_blue,
 54 |                     (1.0, Color32::WHITE),
 55 |                     StrokeKind::Inside,
 56 |                 ),
 57 |             ),
 58 |             (
 59 |                 "Thin filled",
 60 |                 RectShape::filled(sized([20.0, 0.5]), 2.0, baby_blue),
 61 |             ),
 62 |             (
 63 |                 "Thin stroked",
 64 |                 RectShape::new(
 65 |                     sized([20.0, 0.5]),
 66 |                     2.0,
 67 |                     baby_blue,
 68 |                     (0.5, Color32::WHITE),
 69 |                     StrokeKind::Inside,
 70 |                 ),
 71 |             ),
 72 |             (
 73 |                 "Blurred",
 74 |                 RectShape::filled(sized([20.0, 16.0]), 2.0, baby_blue).with_blur_width(50.0),
 75 |             ),
 76 |             (
 77 |                 "Thick stroke, minimal rounding",
 78 |                 RectShape::new(
 79 |                     sized([20.0, 16.0]),
 80 |                     1.0,
 81 |                     baby_blue,
 82 |                     (3.0, Color32::WHITE),
 83 |                     StrokeKind::Inside,
 84 |                 ),
 85 |             ),
 86 |             (
 87 |                 "Blurred stroke",
 88 |                 RectShape::new(
 89 |                     sized([20.0, 16.0]),
 90 |                     0.0,
 91 |                     baby_blue,
 92 |                     (5.0, Color32::WHITE),
 93 |                     StrokeKind::Inside,
 94 |                 )
 95 |                 .with_blur_width(5.0),
 96 |             ),
 97 |             (
 98 |                 "Additive rectangle",
 99 |                 RectShape::new(
100 |                     sized([24.0, 12.0]),
101 |                     0.0,
102 |                     egui::Color32::LIGHT_RED.additive().linear_multiply(0.025),
103 |                     (
104 |                         1.0,
105 |                         egui::Color32::LIGHT_BLUE.additive().linear_multiply(0.1),
106 |                     ),
107 |                     StrokeKind::Outside,
108 |                 ),
109 |             ),
110 |         ];
111 | 
112 |         for (_name, shape) in &mut shapes {
113 |             shape.round_to_pixels = Some(true);
114 |         }
115 | 
116 |         shapes
117 |     }
118 | }
119 | 
120 | impl crate::Demo for TessellationTest {
121 |     fn name(&self) -> &'static str {
122 |         "Tessellation Test"
123 |     }
124 | 
125 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
126 |         egui::Window::new(self.name())
127 |             .resizable(false)
128 |             .open(open)
129 |             .show(ctx, |ui| {
130 |                 use crate::View as _;
131 |                 self.ui(ui);
132 |             });
133 |     }
134 | }
135 | 
136 | impl crate::View for TessellationTest {
137 |     fn ui(&mut self, ui: &mut egui::Ui) {
138 |         ui.add(crate::egui_github_link_file!());
139 |         egui::reset_button(ui, self, "Reset");
140 | 
141 |         ui.horizontal(|ui| {
142 |             ui.group(|ui| {
143 |                 ui.vertical(|ui| {
144 |                     rect_shape_ui(ui, &mut self.shape);
145 |                 });
146 |             });
147 | 
148 |             ui.group(|ui| {
149 |                 ui.vertical(|ui| {
150 |                     ui.heading("Real size");
151 |                     egui::Frame::dark_canvas(ui.style()).show(ui, |ui| {
152 |                         let (resp, painter) =
153 |                             ui.allocate_painter(Vec2::splat(128.0), Sense::hover());
154 |                         let canvas = resp.rect;
155 | 
156 |                         let pixels_per_point = ui.pixels_per_point();
157 |                         let pixel_size = 1.0 / pixels_per_point;
158 |                         let mut shape = self.shape.clone();
159 |                         shape.rect = Rect::from_center_size(canvas.center(), shape.rect.size())
160 |                             .round_to_pixel_center(pixels_per_point)
161 |                             .translate(Vec2::new(pixel_size / 3.0, pixel_size / 5.0)); // Intentionally offset to test the effect of rounding
162 |                         painter.add(shape);
163 |                     });
164 |                 });
165 |             });
166 |         });
167 | 
168 |         ui.group(|ui| {
169 |             ui.heading("Zoomed in");
170 |             let magnification_pixel_size = &mut self.magnification_pixel_size;
171 |             let tessellation_options = &mut self.tessellation_options;
172 | 
173 |             egui::Grid::new("TessellationOptions")
174 |                 .num_columns(2)
175 |                 .spacing([12.0, 8.0])
176 |                 .striped(true)
177 |                 .show(ui, |ui| {
178 |                     ui.label("Magnification");
179 |                     ui.add(
180 |                         egui::DragValue::new(magnification_pixel_size)
181 |                             .speed(0.5)
182 |                             .range(1.0..=32.0),
183 |                     );
184 |                     ui.end_row();
185 | 
186 |                     ui.label("Feathering width");
187 |                     ui.horizontal(|ui| {
188 |                         ui.checkbox(&mut tessellation_options.feathering, "");
189 |                         ui.add_enabled(
190 |                             tessellation_options.feathering,
191 |                             egui::DragValue::new(
192 |                                 &mut tessellation_options.feathering_size_in_pixels,
193 |                             )
194 |                             .speed(0.1)
195 |                             .range(0.0..=4.0)
196 |                             .suffix(" px"),
197 |                         );
198 |                     });
199 |                     ui.end_row();
200 | 
201 |                     ui.label("Paint edges");
202 |                     ui.checkbox(&mut self.paint_edges, "");
203 |                     ui.end_row();
204 |                 });
205 | 
206 |             let magnification_pixel_size = *magnification_pixel_size;
207 | 
208 |             egui::Frame::dark_canvas(ui.style()).show(ui, |ui| {
209 |                 let (resp, painter) = ui.allocate_painter(
210 |                     magnification_pixel_size * (self.shape.rect.size() + Vec2::splat(8.0)),
211 |                     Sense::hover(),
212 |                 );
213 |                 let canvas = resp.rect;
214 | 
215 |                 let mut shape = self.shape.clone();
216 |                 shape.rect = shape.rect.translate(Vec2::new(1.0 / 3.0, 1.0 / 5.0)); // Intentionally offset to test the effect of rounding
217 | 
218 |                 let mut mesh = epaint::Mesh::default();
219 |                 let mut tessellator = epaint::Tessellator::new(
220 |                     1.0,
221 |                     *tessellation_options,
222 |                     ui.fonts(|f| f.font_image_size()),
223 |                     vec![],
224 |                 );
225 |                 tessellator.tessellate_rect(&shape, &mut mesh);
226 | 
227 |                 // Scale and position the mesh:
228 |                 mesh.transform(
229 |                     TSTransform::from_translation(canvas.center().to_vec2())
230 |                         * TSTransform::from_scaling(magnification_pixel_size),
231 |                 );
232 |                 let mesh = std::sync::Arc::new(mesh);
233 |                 painter.add(epaint::Shape::mesh(mesh.clone()));
234 | 
235 |                 if self.paint_edges {
236 |                     let stroke = epaint::Stroke::new(0.5, Color32::MAGENTA);
237 |                     for triangle in mesh.triangles() {
238 |                         let a = mesh.vertices[triangle[0] as usize];
239 |                         let b = mesh.vertices[triangle[1] as usize];
240 |                         let c = mesh.vertices[triangle[2] as usize];
241 | 
242 |                         painter.line_segment([a.pos, b.pos], stroke);
243 |                         painter.line_segment([b.pos, c.pos], stroke);
244 |                         painter.line_segment([c.pos, a.pos], stroke);
245 |                     }
246 |                 }
247 | 
248 |                 if 3.0 < magnification_pixel_size {
249 |                     // Draw pixel centers:
250 |                     let pixel_radius = 0.75;
251 |                     let pixel_color = Color32::GRAY;
252 |                     for yi in 0.. {
253 |                         let y = (yi as f32 + 0.5) * magnification_pixel_size;
254 |                         if y > canvas.height() / 2.0 {
255 |                             break;
256 |                         }
257 |                         for xi in 0.. {
258 |                             let x = (xi as f32 + 0.5) * magnification_pixel_size;
259 |                             if x > canvas.width() / 2.0 {
260 |                                 break;
261 |                             }
262 |                             for offset in [vec2(x, y), vec2(x, -y), vec2(-x, y), vec2(-x, -y)] {
263 |                                 painter.circle_filled(
264 |                                     canvas.center() + offset,
265 |                                     pixel_radius,
266 |                                     pixel_color,
267 |                                 );
268 |                             }
269 |                         }
270 |                     }
271 |                 }
272 |             });
273 |         });
274 |     }
275 | }
276 | 
277 | fn rect_shape_ui(ui: &mut egui::Ui, shape: &mut RectShape) {
278 |     egui::ComboBox::from_id_salt("prefabs")
279 |         .selected_text("Prefabs")
280 |         .show_ui(ui, |ui| {
281 |             for (name, prefab) in TessellationTest::interesting_shapes() {
282 |                 ui.selectable_value(shape, prefab, name);
283 |             }
284 |         });
285 | 
286 |     ui.add_space(4.0);
287 | 
288 |     let RectShape {
289 |         rect,
290 |         corner_radius,
291 |         fill,
292 |         stroke,
293 |         stroke_kind,
294 |         blur_width,
295 |         round_to_pixels,
296 |         brush: _,
297 |     } = shape;
298 | 
299 |     let round_to_pixels = round_to_pixels.get_or_insert(true);
300 | 
301 |     egui::Grid::new("RectShape")
302 |         .num_columns(2)
303 |         .spacing([12.0, 8.0])
304 |         .striped(true)
305 |         .show(ui, |ui| {
306 |             ui.label("Size");
307 |             ui.horizontal(|ui| {
308 |                 let mut size = rect.size();
309 |                 ui.add(
310 |                     egui::DragValue::new(&mut size.x)
311 |                         .speed(0.2)
312 |                         .range(0.0..=64.0),
313 |                 );
314 |                 ui.add(
315 |                     egui::DragValue::new(&mut size.y)
316 |                         .speed(0.2)
317 |                         .range(0.0..=64.0),
318 |                 );
319 |                 *rect = Rect::from_center_size(Pos2::ZERO, size);
320 |             });
321 |             ui.end_row();
322 | 
323 |             ui.label("Corner radius");
324 |             ui.add(corner_radius);
325 |             ui.end_row();
326 | 
327 |             ui.label("Fill");
328 |             ui.color_edit_button_srgba(fill);
329 |             ui.end_row();
330 | 
331 |             ui.label("Stroke");
332 |             ui.add(stroke);
333 |             ui.end_row();
334 | 
335 |             ui.label("Stroke kind");
336 |             ui.horizontal(|ui| {
337 |                 ui.selectable_value(stroke_kind, StrokeKind::Inside, "Inside");
338 |                 ui.selectable_value(stroke_kind, StrokeKind::Middle, "Middle");
339 |                 ui.selectable_value(stroke_kind, StrokeKind::Outside, "Outside");
340 |             });
341 |             ui.end_row();
342 | 
343 |             ui.label("Blur width");
344 |             ui.add(
345 |                 egui::DragValue::new(blur_width)
346 |                     .speed(0.5)
347 |                     .range(0.0..=20.0),
348 |             );
349 |             ui.end_row();
350 | 
351 |             ui.label("Round to pixels");
352 |             ui.checkbox(round_to_pixels, "");
353 |             ui.end_row();
354 |         });
355 | }
356 | 
357 | #[cfg(test)]
358 | mod tests {
359 |     use crate::View as _;
360 | 
361 |     use super::*;
362 | 
363 |     #[test]
364 |     fn snapshot_tessellation_test() {
365 |         for (name, shape) in TessellationTest::interesting_shapes() {
366 |             let mut test = TessellationTest {
367 |                 shape,
368 |                 ..Default::default()
369 |             };
370 |             let mut harness = egui_kittest::Harness::new_ui(|ui| {
371 |                 test.ui(ui);
372 |             });
373 | 
374 |             harness.fit_contents();
375 |             harness.run();
376 | 
377 |             harness.snapshot(format!("tessellation_test/{name}"));
378 |         }
379 |     }
380 | }
381 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tests/window_resize_test.rs:
--------------------------------------------------------------------------------
  1 | pub struct WindowResizeTest {
  2 |     text: String,
  3 | }
  4 | 
  5 | impl Default for WindowResizeTest {
  6 |     fn default() -> Self {
  7 |         Self {
  8 |             text: crate::LOREM_IPSUM_LONG.to_owned(),
  9 |         }
 10 |     }
 11 | }
 12 | 
 13 | impl crate::Demo for WindowResizeTest {
 14 |     fn name(&self) -> &'static str {
 15 |         "Window Resize Test"
 16 |     }
 17 | 
 18 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 19 |         use egui::{Resize, ScrollArea, TextEdit, Window};
 20 | 
 21 |         Window::new("↔ auto-sized")
 22 |             .open(open)
 23 |             .auto_sized()
 24 |             .show(ctx, |ui| {
 25 |                 ui.label("This window will auto-size based on its contents.");
 26 |                 ui.heading("Resize this area:");
 27 |                 Resize::default().show(ui, |ui| {
 28 |                     lorem_ipsum(ui, crate::LOREM_IPSUM);
 29 |                 });
 30 |                 ui.heading("Resize the above area!");
 31 |             });
 32 | 
 33 |         Window::new("↔ resizable + scroll")
 34 |             .open(open)
 35 |             .vscroll(true)
 36 |             .resizable(true)
 37 |             .default_height(300.0)
 38 |             .show(ctx, |ui| {
 39 |                 ui.label(
 40 |                     "This window is resizable and has a scroll area. You can shrink it to any size.",
 41 |                 );
 42 |                 ui.separator();
 43 |                 lorem_ipsum(ui, crate::LOREM_IPSUM_LONG);
 44 |             });
 45 | 
 46 |         Window::new("↔ resizable + embedded scroll")
 47 |             .open(open)
 48 |             .vscroll(false)
 49 |             .resizable(true)
 50 |             .default_height(300.0)
 51 |             .show(ctx, |ui| {
 52 |                 ui.label("This window is resizable but has no built-in scroll area.");
 53 |                 ui.label("However, we have a sub-region with a scroll bar:");
 54 |                 ui.separator();
 55 |                 ScrollArea::vertical().show(ui, |ui| {
 56 |                     let lorem_ipsum_extra_long =
 57 |                         format!("{}\n\n{}", crate::LOREM_IPSUM_LONG, crate::LOREM_IPSUM_LONG);
 58 |                     lorem_ipsum(ui, &lorem_ipsum_extra_long);
 59 |                 });
 60 |                 // ui.heading("Some additional text here, that should also be visible"); // this works, but messes with the resizing a bit
 61 |             });
 62 | 
 63 |         Window::new("↔ resizable without scroll")
 64 |             .open(open)
 65 |             .vscroll(false)
 66 |             .resizable(true)
 67 |             .show(ctx, |ui| {
 68 |                 ui.label("This window is resizable but has no scroll area. This means it can only be resized to a size where all the contents is visible.");
 69 |                 ui.label("egui will not clip the contents of a window, nor add whitespace to it.");
 70 |                 ui.separator();
 71 |                 lorem_ipsum(ui, crate::LOREM_IPSUM);
 72 |             });
 73 | 
 74 |         Window::new("↔ resizable with TextEdit")
 75 |             .open(open)
 76 |             .vscroll(false)
 77 |             .resizable(true)
 78 |             .default_height(300.0)
 79 |             .show(ctx, |ui| {
 80 |                 ui.label("Shows how you can fill an area with a widget.");
 81 |                 ui.add_sized(ui.available_size(), TextEdit::multiline(&mut self.text));
 82 |             });
 83 | 
 84 |         Window::new("↔ freely resized")
 85 |             .open(open)
 86 |             .vscroll(false)
 87 |             .resizable(true)
 88 |             .default_size([250.0, 150.0])
 89 |             .show(ctx, |ui| {
 90 |                 ui.label("This window has empty space that fills up the available space, preventing auto-shrink.");
 91 |                 ui.vertical_centered(|ui| {
 92 |                     ui.add(crate::egui_github_link_file!());
 93 |                 });
 94 |                 ui.allocate_space(ui.available_size());
 95 |             });
 96 |     }
 97 | }
 98 | 
 99 | fn lorem_ipsum(ui: &mut egui::Ui, text: &str) {
100 |     ui.with_layout(
101 |         egui::Layout::top_down(egui::Align::LEFT).with_cross_justify(true),
102 |         |ui| {
103 |             ui.label(egui::RichText::new(text).weak());
104 |         },
105 |     );
106 | }
107 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/text_edit.rs:
--------------------------------------------------------------------------------
  1 | /// Showcase [`egui::TextEdit`].
  2 | #[derive(PartialEq, Eq)]
  3 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  4 | #[cfg_attr(feature = "serde", serde(default))]
  5 | pub struct TextEditDemo {
  6 |     pub text: String,
  7 | }
  8 | 
  9 | impl Default for TextEditDemo {
 10 |     fn default() -> Self {
 11 |         Self {
 12 |             text: "Edit this text".to_owned(),
 13 |         }
 14 |     }
 15 | }
 16 | 
 17 | impl crate::Demo for TextEditDemo {
 18 |     fn name(&self) -> &'static str {
 19 |         "🖹 TextEdit"
 20 |     }
 21 | 
 22 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 23 |         egui::Window::new(self.name())
 24 |             .open(open)
 25 |             .resizable(false)
 26 |             .show(ctx, |ui| {
 27 |                 use crate::View as _;
 28 |                 self.ui(ui);
 29 |             });
 30 |     }
 31 | }
 32 | 
 33 | impl crate::View for TextEditDemo {
 34 |     fn ui(&mut self, ui: &mut egui::Ui) {
 35 |         ui.vertical_centered(|ui| {
 36 |             ui.add(crate::egui_github_link_file!());
 37 |         });
 38 | 
 39 |         let Self { text } = self;
 40 | 
 41 |         ui.horizontal(|ui| {
 42 |             ui.spacing_mut().item_spacing.x = 0.0;
 43 |             ui.label("Advanced usage of ");
 44 |             ui.code("TextEdit");
 45 |             ui.label(".");
 46 |         });
 47 | 
 48 |         let output = egui::TextEdit::multiline(text)
 49 |             .hint_text("Type something!")
 50 |             .show(ui);
 51 | 
 52 |         ui.horizontal(|ui| {
 53 |             ui.spacing_mut().item_spacing.x = 0.0;
 54 |             ui.label("Selected text: ");
 55 |             if let Some(text_cursor_range) = output.cursor_range {
 56 |                 let selected_text = text_cursor_range.slice_str(text);
 57 |                 ui.code(selected_text);
 58 |             }
 59 |         });
 60 | 
 61 |         let anything_selected = output.cursor_range.is_some_and(|cursor| !cursor.is_empty());
 62 | 
 63 |         ui.add_enabled(
 64 |             anything_selected,
 65 |             egui::Label::new("Press ctrl+Y to toggle the case of selected text (cmd+Y on Mac)"),
 66 |         );
 67 | 
 68 |         if ui.input_mut(|i| i.consume_key(egui::Modifiers::COMMAND, egui::Key::Y)) {
 69 |             if let Some(text_cursor_range) = output.cursor_range {
 70 |                 use egui::TextBuffer as _;
 71 |                 let selected_chars = text_cursor_range.as_sorted_char_range();
 72 |                 let selected_text = text.char_range(selected_chars.clone());
 73 |                 let upper_case = selected_text.to_uppercase();
 74 |                 let new_text = if selected_text == upper_case {
 75 |                     selected_text.to_lowercase()
 76 |                 } else {
 77 |                     upper_case
 78 |                 };
 79 |                 text.delete_char_range(selected_chars.clone());
 80 |                 text.insert_text(&new_text, selected_chars.start);
 81 |             }
 82 |         }
 83 | 
 84 |         ui.horizontal(|ui| {
 85 |             ui.label("Move cursor to the:");
 86 | 
 87 |             if ui.button("start").clicked() {
 88 |                 let text_edit_id = output.response.id;
 89 |                 if let Some(mut state) = egui::TextEdit::load_state(ui.ctx(), text_edit_id) {
 90 |                     let ccursor = egui::text::CCursor::new(0);
 91 |                     state
 92 |                         .cursor
 93 |                         .set_char_range(Some(egui::text::CCursorRange::one(ccursor)));
 94 |                     state.store(ui.ctx(), text_edit_id);
 95 |                     ui.ctx().memory_mut(|mem| mem.request_focus(text_edit_id)); // give focus back to the [`TextEdit`].
 96 |                 }
 97 |             }
 98 | 
 99 |             if ui.button("end").clicked() {
100 |                 let text_edit_id = output.response.id;
101 |                 if let Some(mut state) = egui::TextEdit::load_state(ui.ctx(), text_edit_id) {
102 |                     let ccursor = egui::text::CCursor::new(text.chars().count());
103 |                     state
104 |                         .cursor
105 |                         .set_char_range(Some(egui::text::CCursorRange::one(ccursor)));
106 |                     state.store(ui.ctx(), text_edit_id);
107 |                     ui.ctx().memory_mut(|mem| mem.request_focus(text_edit_id)); // give focus back to the [`TextEdit`].
108 |                 }
109 |             }
110 |         });
111 |     }
112 | }
113 | 
114 | #[cfg(test)]
115 | mod tests {
116 |     use egui::{CentralPanel, Key, Modifiers, accesskit};
117 |     use egui_kittest::Harness;
118 |     use egui_kittest::kittest::Queryable as _;
119 | 
120 |     #[test]
121 |     pub fn should_type() {
122 |         let text = "Hello, world!".to_owned();
123 |         let mut harness = Harness::new_state(
124 |             move |ctx, text| {
125 |                 CentralPanel::default().show(ctx, |ui| {
126 |                     ui.text_edit_singleline(text);
127 |                 });
128 |             },
129 |             text,
130 |         );
131 | 
132 |         harness.run();
133 | 
134 |         let text_edit = harness.get_by_role(accesskit::Role::TextInput);
135 |         assert_eq!(text_edit.value().as_deref(), Some("Hello, world!"));
136 |         text_edit.focus();
137 | 
138 |         harness.key_press_modifiers(Modifiers::COMMAND, Key::A);
139 |         text_edit.type_text("Hi ");
140 | 
141 |         harness.run();
142 |         harness
143 |             .get_by_role(accesskit::Role::TextInput)
144 |             .type_text("there!");
145 | 
146 |         harness.run();
147 |         let text_edit = harness.get_by_role(accesskit::Role::TextInput);
148 |         assert_eq!(text_edit.value().as_deref(), Some("Hi there!"));
149 |         assert_eq!(harness.state(), "Hi there!");
150 |     }
151 | }
152 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/text_layout.rs:
--------------------------------------------------------------------------------
  1 | /// Showcase text layout
  2 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  3 | #[cfg_attr(feature = "serde", serde(default))]
  4 | pub struct TextLayoutDemo {
  5 |     break_anywhere: bool,
  6 |     max_rows: usize,
  7 |     overflow_character: Option<char>,
  8 |     extra_letter_spacing_pixels: i32,
  9 |     line_height_pixels: u32,
 10 |     lorem_ipsum: bool,
 11 | }
 12 | 
 13 | impl Default for TextLayoutDemo {
 14 |     fn default() -> Self {
 15 |         Self {
 16 |             max_rows: 6,
 17 |             break_anywhere: true,
 18 |             overflow_character: Some('…'),
 19 |             extra_letter_spacing_pixels: 0,
 20 |             line_height_pixels: 0,
 21 |             lorem_ipsum: true,
 22 |         }
 23 |     }
 24 | }
 25 | 
 26 | impl crate::Demo for TextLayoutDemo {
 27 |     fn name(&self) -> &'static str {
 28 |         "🖹 Text Layout"
 29 |     }
 30 | 
 31 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 32 |         egui::Window::new(self.name())
 33 |             .open(open)
 34 |             .resizable(true)
 35 |             .show(ctx, |ui| {
 36 |                 use crate::View as _;
 37 |                 self.ui(ui);
 38 |             });
 39 |     }
 40 | }
 41 | 
 42 | impl crate::View for TextLayoutDemo {
 43 |     fn ui(&mut self, ui: &mut egui::Ui) {
 44 |         let Self {
 45 |             break_anywhere,
 46 |             max_rows,
 47 |             overflow_character,
 48 |             extra_letter_spacing_pixels,
 49 |             line_height_pixels,
 50 |             lorem_ipsum,
 51 |         } = self;
 52 | 
 53 |         use egui::text::LayoutJob;
 54 | 
 55 |         let pixels_per_point = ui.ctx().pixels_per_point();
 56 |         let points_per_pixel = 1.0 / pixels_per_point;
 57 | 
 58 |         ui.vertical_centered(|ui| {
 59 |             ui.add(crate::egui_github_link_file_line!());
 60 |         });
 61 | 
 62 |         ui.add_space(12.0);
 63 | 
 64 |         egui::Grid::new("TextLayoutDemo")
 65 |             .num_columns(2)
 66 |             .show(ui, |ui| {
 67 |                 ui.label("Max rows:");
 68 |                 ui.add(egui::DragValue::new(max_rows));
 69 |                 ui.end_row();
 70 | 
 71 |                 ui.label("Line-break:");
 72 |                 ui.horizontal(|ui| {
 73 |                     ui.radio_value(break_anywhere, false, "word boundaries");
 74 |                     ui.radio_value(break_anywhere, true, "anywhere");
 75 |                 });
 76 |                 ui.end_row();
 77 | 
 78 |                 ui.label("Overflow character:");
 79 |                 ui.horizontal(|ui| {
 80 |                     ui.selectable_value(overflow_character, None, "None");
 81 |                     ui.selectable_value(overflow_character, Some('…'), "…");
 82 |                     ui.selectable_value(overflow_character, Some('—'), "—");
 83 |                     ui.selectable_value(overflow_character, Some('-'), "  -  ");
 84 |                 });
 85 |                 ui.end_row();
 86 | 
 87 |                 ui.label("Extra letter spacing:");
 88 |                 ui.add(egui::DragValue::new(extra_letter_spacing_pixels).suffix(" pixels"));
 89 |                 ui.end_row();
 90 | 
 91 |                 ui.label("Line height:");
 92 |                 ui.horizontal(|ui| {
 93 |                     if ui
 94 |                         .selectable_label(*line_height_pixels == 0, "Default")
 95 |                         .clicked()
 96 |                     {
 97 |                         *line_height_pixels = 0;
 98 |                     }
 99 |                     if ui
100 |                         .selectable_label(*line_height_pixels != 0, "Custom")
101 |                         .clicked()
102 |                     {
103 |                         *line_height_pixels = (pixels_per_point * 20.0).round() as _;
104 |                     }
105 |                     if *line_height_pixels != 0 {
106 |                         ui.add(egui::DragValue::new(line_height_pixels).suffix(" pixels"));
107 |                     }
108 |                 });
109 |                 ui.end_row();
110 | 
111 |                 ui.label("Text:");
112 |                 ui.horizontal(|ui| {
113 |                     ui.selectable_value(lorem_ipsum, true, "Lorem Ipsum");
114 |                     ui.selectable_value(lorem_ipsum, false, "La Pasionaria");
115 |                 });
116 |             });
117 | 
118 |         ui.add_space(12.0);
119 | 
120 |         let text = if *lorem_ipsum {
121 |             crate::LOREM_IPSUM_LONG
122 |         } else {
123 |             TO_BE_OR_NOT_TO_BE
124 |         };
125 | 
126 |         egui::ScrollArea::vertical()
127 |             .auto_shrink(false)
128 |             .show(ui, |ui| {
129 |                 let extra_letter_spacing = points_per_pixel * *extra_letter_spacing_pixels as f32;
130 |                 let line_height = (*line_height_pixels != 0)
131 |                     .then_some(points_per_pixel * *line_height_pixels as f32);
132 | 
133 |                 let mut job = LayoutJob::single_section(
134 |                     text.to_owned(),
135 |                     egui::TextFormat {
136 |                         extra_letter_spacing,
137 |                         line_height,
138 |                         ..Default::default()
139 |                     },
140 |                 );
141 |                 job.wrap = egui::text::TextWrapping {
142 |                     max_rows: *max_rows,
143 |                     break_anywhere: *break_anywhere,
144 |                     overflow_character: *overflow_character,
145 |                     ..Default::default()
146 |                 };
147 | 
148 |                 // NOTE: `Label` overrides some of the wrapping settings, e.g. wrap width
149 |                 ui.label(job);
150 |             });
151 |     }
152 | }
153 | 
154 | /// Excerpt from Dolores Ibárruri's farwel speech to the International Brigades:
155 | const TO_BE_OR_NOT_TO_BE: &str = "Mothers! Women!\n
156 | When the years pass by and the wounds of war are stanched; when the memory of the sad and bloody days dissipates in a present of liberty, of peace and of wellbeing; when the rancor have died out and pride in a free country is felt equally by all Spaniards, speak to your children. Tell them of these men of the International Brigades.\n\
157 | \n\
158 | Recount for them how, coming over seas and mountains, crossing frontiers bristling with bayonets, sought by raving dogs thirsting to tear their flesh, these men reached our country as crusaders for freedom, to fight and die for Spain’s liberty and independence threatened by German and Italian fascism. \
159 | They gave up everything — their loves, their countries, home and fortune, fathers, mothers, wives, brothers, sisters and children — and they came and said to us: “We are here. Your cause, Spain’s cause, is ours. It is the cause of all advanced and progressive mankind.”\n\
160 | \n\
161 | - Dolores Ibárruri, 1938";
162 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/toggle_switch.rs:
--------------------------------------------------------------------------------
  1 | //! Source code example of how to create your own widget.
  2 | //! This is meant to be read as a tutorial, hence the plethora of comments.
  3 | 
  4 | /// iOS-style toggle switch:
  5 | ///
  6 | /// ``` text
  7 | ///      _____________
  8 | ///     /       /.....\
  9 | ///    |       |.......|
 10 | ///     \_______\_____/
 11 | /// ```
 12 | ///
 13 | /// ## Example:
 14 | /// ``` ignore
 15 | /// toggle_ui(ui, &mut my_bool);
 16 | /// ```
 17 | pub fn toggle_ui(ui: &mut egui::Ui, on: &mut bool) -> egui::Response {
 18 |     // Widget code can be broken up in four steps:
 19 |     //  1. Decide a size for the widget
 20 |     //  2. Allocate space for it
 21 |     //  3. Handle interactions with the widget (if any)
 22 |     //  4. Paint the widget
 23 | 
 24 |     // 1. Deciding widget size:
 25 |     // You can query the `ui` how much space is available,
 26 |     // but in this example we have a fixed size widget based on the height of a standard button:
 27 |     let desired_size = ui.spacing().interact_size.y * egui::vec2(2.0, 1.0);
 28 | 
 29 |     // 2. Allocating space:
 30 |     // This is where we get a region of the screen assigned.
 31 |     // We also tell the Ui to sense clicks in the allocated region.
 32 |     let (rect, mut response) = ui.allocate_exact_size(desired_size, egui::Sense::click());
 33 | 
 34 |     // 3. Interact: Time to check for clicks!
 35 |     if response.clicked() {
 36 |         *on = !*on;
 37 |         response.mark_changed(); // report back that the value changed
 38 |     }
 39 | 
 40 |     // Attach some meta-data to the response which can be used by screen readers:
 41 |     response.widget_info(|| {
 42 |         egui::WidgetInfo::selected(egui::WidgetType::Checkbox, ui.is_enabled(), *on, "")
 43 |     });
 44 | 
 45 |     // 4. Paint!
 46 |     // Make sure we need to paint:
 47 |     if ui.is_rect_visible(rect) {
 48 |         // Let's ask for a simple animation from egui.
 49 |         // egui keeps track of changes in the boolean associated with the id and
 50 |         // returns an animated value in the 0-1 range for how much "on" we are.
 51 |         let how_on = ui.ctx().animate_bool_responsive(response.id, *on);
 52 |         // We will follow the current style by asking
 53 |         // "how should something that is being interacted with be painted?".
 54 |         // This will, for instance, give us different colors when the widget is hovered or clicked.
 55 |         let visuals = ui.style().interact_selectable(&response, *on);
 56 |         // All coordinates are in absolute screen coordinates so we use `rect` to place the elements.
 57 |         let rect = rect.expand(visuals.expansion);
 58 |         let radius = 0.5 * rect.height();
 59 |         ui.painter().rect(
 60 |             rect,
 61 |             radius,
 62 |             visuals.bg_fill,
 63 |             visuals.bg_stroke,
 64 |             egui::StrokeKind::Inside,
 65 |         );
 66 |         // Paint the circle, animating it from left to right with `how_on`:
 67 |         let circle_x = egui::lerp((rect.left() + radius)..=(rect.right() - radius), how_on);
 68 |         let center = egui::pos2(circle_x, rect.center().y);
 69 |         ui.painter()
 70 |             .circle(center, 0.75 * radius, visuals.bg_fill, visuals.fg_stroke);
 71 |     }
 72 | 
 73 |     // All done! Return the interaction response so the user can check what happened
 74 |     // (hovered, clicked, ...) and maybe show a tooltip:
 75 |     response
 76 | }
 77 | 
 78 | /// Here is the same code again, but a bit more compact:
 79 | #[expect(dead_code)]
 80 | fn toggle_ui_compact(ui: &mut egui::Ui, on: &mut bool) -> egui::Response {
 81 |     let desired_size = ui.spacing().interact_size.y * egui::vec2(2.0, 1.0);
 82 |     let (rect, mut response) = ui.allocate_exact_size(desired_size, egui::Sense::click());
 83 |     if response.clicked() {
 84 |         *on = !*on;
 85 |         response.mark_changed();
 86 |     }
 87 |     response.widget_info(|| {
 88 |         egui::WidgetInfo::selected(egui::WidgetType::Checkbox, ui.is_enabled(), *on, "")
 89 |     });
 90 | 
 91 |     if ui.is_rect_visible(rect) {
 92 |         let how_on = ui.ctx().animate_bool_responsive(response.id, *on);
 93 |         let visuals = ui.style().interact_selectable(&response, *on);
 94 |         let rect = rect.expand(visuals.expansion);
 95 |         let radius = 0.5 * rect.height();
 96 |         ui.painter().rect(
 97 |             rect,
 98 |             radius,
 99 |             visuals.bg_fill,
100 |             visuals.bg_stroke,
101 |             egui::StrokeKind::Inside,
102 |         );
103 |         let circle_x = egui::lerp((rect.left() + radius)..=(rect.right() - radius), how_on);
104 |         let center = egui::pos2(circle_x, rect.center().y);
105 |         ui.painter()
106 |             .circle(center, 0.75 * radius, visuals.bg_fill, visuals.fg_stroke);
107 |     }
108 | 
109 |     response
110 | }
111 | 
112 | // A wrapper that allows the more idiomatic usage pattern: `ui.add(toggle(&mut my_bool))`
113 | /// iOS-style toggle switch.
114 | ///
115 | /// ## Example:
116 | /// ``` ignore
117 | /// ui.add(toggle(&mut my_bool));
118 | /// ```
119 | pub fn toggle(on: &mut bool) -> impl egui::Widget + '_ {
120 |     move |ui: &mut egui::Ui| toggle_ui(ui, on)
121 | }
122 | 
123 | pub fn url_to_file_source_code() -> String {
124 |     format!("https://github.com/emilk/egui/blob/main/{}", file!())
125 | }
126 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/tooltips.rs:
--------------------------------------------------------------------------------
  1 | #[derive(Clone, PartialEq, Eq)]
  2 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  3 | pub struct Tooltips {
  4 |     enabled: bool,
  5 | }
  6 | 
  7 | impl Default for Tooltips {
  8 |     fn default() -> Self {
  9 |         Self { enabled: true }
 10 |     }
 11 | }
 12 | 
 13 | impl crate::Demo for Tooltips {
 14 |     fn name(&self) -> &'static str {
 15 |         "🗖 Tooltips"
 16 |     }
 17 | 
 18 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 19 |         use crate::View as _;
 20 |         let window = egui::Window::new("Tooltips")
 21 |             .constrain(false) // So we can test how tooltips behave close to the screen edge
 22 |             .resizable(true)
 23 |             .default_size([450.0, 300.0])
 24 |             .scroll(false)
 25 |             .open(open);
 26 |         window.show(ctx, |ui| self.ui(ui));
 27 |     }
 28 | }
 29 | 
 30 | impl crate::View for Tooltips {
 31 |     fn ui(&mut self, ui: &mut egui::Ui) {
 32 |         ui.spacing_mut().item_spacing.y = 8.0;
 33 | 
 34 |         ui.vertical_centered(|ui| {
 35 |             ui.add(crate::egui_github_link_file_line!());
 36 |         });
 37 | 
 38 |         egui::SidePanel::right("scroll_test").show_inside(ui, |ui| {
 39 |             ui.label(
 40 |                 "The scroll area below has many labels with interactive tooltips. \
 41 |                  The purpose is to test that the tooltips close when you scroll.",
 42 |             )
 43 |             .on_hover_text("Try hovering a label below, then scroll!");
 44 |             egui::ScrollArea::vertical()
 45 |                 .auto_shrink(false)
 46 |                 .show(ui, |ui| {
 47 |                     for i in 0..1000 {
 48 |                         ui.label(format!("This is line {i}")).on_hover_ui(|ui| {
 49 |                             ui.style_mut().interaction.selectable_labels = true;
 50 |                             ui.label(
 51 |                             "This tooltip is interactive, because the text in it is selectable.",
 52 |                         );
 53 |                         });
 54 |                     }
 55 |                 });
 56 |         });
 57 | 
 58 |         egui::CentralPanel::default().show_inside(ui, |ui| {
 59 |             self.misc_tests(ui);
 60 |         });
 61 |     }
 62 | }
 63 | 
 64 | impl Tooltips {
 65 |     fn misc_tests(&mut self, ui: &mut egui::Ui) {
 66 |         ui.label("All labels in this demo have tooltips.")
 67 |             .on_hover_text("Yes, even this one.");
 68 | 
 69 |         ui.label("Some widgets have multiple tooltips!")
 70 |             .on_hover_text("The first tooltip.")
 71 |             .on_hover_text("The second tooltip.");
 72 | 
 73 |         ui.label("Tooltips can contain interactive widgets.")
 74 |             .on_hover_ui(|ui| {
 75 |                 ui.label("This tooltip contains a link:");
 76 |                 ui.hyperlink_to("www.egui.rs", "https://www.egui.rs/")
 77 |                     .on_hover_text("The tooltip has a tooltip in it!");
 78 |             });
 79 | 
 80 |         ui.label("You can put selectable text in tooltips too.")
 81 |             .on_hover_ui(|ui| {
 82 |                 ui.style_mut().interaction.selectable_labels = true;
 83 |                 ui.label("You can select this text.");
 84 |             });
 85 | 
 86 |         ui.label("This tooltip shows at the mouse cursor.")
 87 |             .on_hover_text_at_pointer("Move me around!!");
 88 | 
 89 |         ui.separator(); // ---------------------------------------------------------
 90 | 
 91 |         let tooltip_ui = |ui: &mut egui::Ui| {
 92 |             ui.horizontal(|ui| {
 93 |                 ui.label("This tooltip was created with");
 94 |                 ui.code(".on_hover_ui(…)");
 95 |             });
 96 |         };
 97 |         let disabled_tooltip_ui = |ui: &mut egui::Ui| {
 98 |             ui.label("A different tooltip when widget is disabled.");
 99 |             ui.horizontal(|ui| {
100 |                 ui.label("This tooltip was created with");
101 |                 ui.code(".on_disabled_hover_ui(…)");
102 |             });
103 |         };
104 | 
105 |         ui.label("You can have different tooltips depending on whether or not a widget is enabled:")
106 |             .on_hover_text("Check the tooltip of the button below, and see how it changes depending on whether or not it is enabled.");
107 | 
108 |         ui.horizontal(|ui| {
109 |             ui.checkbox(&mut self.enabled, "Enabled")
110 |                 .on_hover_text("Controls whether or not the following button is enabled.");
111 | 
112 |             ui.add_enabled(self.enabled, egui::Button::new("Sometimes clickable"))
113 |                 .on_hover_ui(tooltip_ui)
114 |                 .on_disabled_hover_ui(disabled_tooltip_ui);
115 |         });
116 |     }
117 | }
118 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/undo_redo.rs:
--------------------------------------------------------------------------------
 1 | use egui::{Button, util::undoer::Undoer};
 2 | 
 3 | #[derive(Debug, PartialEq, Eq, Clone)]
 4 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 5 | #[cfg_attr(feature = "serde", serde(default))]
 6 | pub struct State {
 7 |     pub toggle_value: bool,
 8 |     pub text: String,
 9 | }
10 | 
11 | impl Default for State {
12 |     fn default() -> Self {
13 |         Self {
14 |             toggle_value: Default::default(),
15 |             text: "Text with undo/redo".to_owned(),
16 |         }
17 |     }
18 | }
19 | 
20 | /// Showcase [`egui::util::undoer::Undoer`]
21 | #[derive(Debug, Default)]
22 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
23 | #[cfg_attr(feature = "serde", serde(default))]
24 | pub struct UndoRedoDemo {
25 |     pub state: State,
26 |     pub undoer: Undoer<State>,
27 | }
28 | 
29 | impl crate::Demo for UndoRedoDemo {
30 |     fn name(&self) -> &'static str {
31 |         "⟲ Undo Redo"
32 |     }
33 | 
34 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
35 |         egui::Window::new(self.name())
36 |             .open(open)
37 |             .resizable(false)
38 |             .show(ctx, |ui| {
39 |                 use crate::View as _;
40 |                 self.ui(ui);
41 |             });
42 |     }
43 | }
44 | 
45 | impl crate::View for UndoRedoDemo {
46 |     fn ui(&mut self, ui: &mut egui::Ui) {
47 |         ui.vertical_centered(|ui| {
48 |             ui.add(crate::egui_github_link_file!());
49 |         });
50 | 
51 |         ui.checkbox(&mut self.state.toggle_value, "Checkbox with undo/redo");
52 |         ui.text_edit_singleline(&mut self.state.text);
53 | 
54 |         ui.separator();
55 | 
56 |         let can_undo = self.undoer.has_undo(&self.state);
57 |         let can_redo = self.undoer.has_redo(&self.state);
58 | 
59 |         ui.horizontal(|ui| {
60 |             let undo = ui.add_enabled(can_undo, Button::new("⟲ Undo")).clicked();
61 |             let redo = ui.add_enabled(can_redo, Button::new("⟳ Redo")).clicked();
62 | 
63 |             if undo {
64 |                 if let Some(undo_text) = self.undoer.undo(&self.state) {
65 |                     self.state = undo_text.clone();
66 |                 }
67 |             }
68 |             if redo {
69 |                 if let Some(redo_text) = self.undoer.redo(&self.state) {
70 |                     self.state = redo_text.clone();
71 |                 }
72 |             }
73 |         });
74 | 
75 |         self.undoer
76 |             .feed_state(ui.ctx().input(|input| input.time), &self.state);
77 |     }
78 | }
79 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/widget_gallery.rs:
--------------------------------------------------------------------------------
  1 | #[derive(Debug, PartialEq)]
  2 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  3 | enum Enum {
  4 |     First,
  5 |     Second,
  6 |     Third,
  7 | }
  8 | 
  9 | /// Shows off one example of each major type of widget.
 10 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
 11 | pub struct WidgetGallery {
 12 |     enabled: bool,
 13 |     visible: bool,
 14 |     boolean: bool,
 15 |     opacity: f32,
 16 |     radio: Enum,
 17 |     scalar: f32,
 18 |     string: String,
 19 |     color: egui::Color32,
 20 |     animate_progress_bar: bool,
 21 | 
 22 |     #[cfg(feature = "chrono")]
 23 |     #[cfg_attr(feature = "serde", serde(skip))]
 24 |     date: Option<chrono::NaiveDate>,
 25 | 
 26 |     #[cfg(feature = "chrono")]
 27 |     with_date_button: bool,
 28 | }
 29 | 
 30 | impl Default for WidgetGallery {
 31 |     fn default() -> Self {
 32 |         Self {
 33 |             enabled: true,
 34 |             visible: true,
 35 |             opacity: 1.0,
 36 |             boolean: false,
 37 |             radio: Enum::First,
 38 |             scalar: 42.0,
 39 |             string: Default::default(),
 40 |             color: egui::Color32::LIGHT_BLUE.linear_multiply(0.5),
 41 |             animate_progress_bar: false,
 42 |             #[cfg(feature = "chrono")]
 43 |             date: None,
 44 |             #[cfg(feature = "chrono")]
 45 |             with_date_button: true,
 46 |         }
 47 |     }
 48 | }
 49 | 
 50 | impl WidgetGallery {
 51 |     #[allow(unused_mut, clippy::allow_attributes)] // if not chrono
 52 |     #[inline]
 53 |     pub fn with_date_button(mut self, _with_date_button: bool) -> Self {
 54 |         #[cfg(feature = "chrono")]
 55 |         {
 56 |             self.with_date_button = _with_date_button;
 57 |         }
 58 |         self
 59 |     }
 60 | }
 61 | 
 62 | impl crate::Demo for WidgetGallery {
 63 |     fn name(&self) -> &'static str {
 64 |         "🗄 Widget Gallery"
 65 |     }
 66 | 
 67 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 68 |         egui::Window::new(self.name())
 69 |             .open(open)
 70 |             .resizable([true, false]) // resizable so we can shrink if the text edit grows
 71 |             .default_width(280.0)
 72 |             .show(ctx, |ui| {
 73 |                 use crate::View as _;
 74 |                 self.ui(ui);
 75 |             });
 76 |     }
 77 | }
 78 | 
 79 | impl crate::View for WidgetGallery {
 80 |     fn ui(&mut self, ui: &mut egui::Ui) {
 81 |         let mut ui_builder = egui::UiBuilder::new();
 82 |         if !self.enabled {
 83 |             ui_builder = ui_builder.disabled();
 84 |         }
 85 |         if !self.visible {
 86 |             ui_builder = ui_builder.invisible();
 87 |         }
 88 | 
 89 |         ui.scope_builder(ui_builder, |ui| {
 90 |             ui.multiply_opacity(self.opacity);
 91 | 
 92 |             egui::Grid::new("my_grid")
 93 |                 .num_columns(2)
 94 |                 .spacing([40.0, 4.0])
 95 |                 .striped(true)
 96 |                 .show(ui, |ui| {
 97 |                     self.gallery_grid_contents(ui);
 98 |                 });
 99 |         });
100 | 
101 |         ui.separator();
102 | 
103 |         ui.horizontal(|ui| {
104 |             ui.checkbox(&mut self.visible, "Visible")
105 |                 .on_hover_text("Uncheck to hide all the widgets.");
106 |             if self.visible {
107 |                 ui.checkbox(&mut self.enabled, "Interactive")
108 |                     .on_hover_text("Uncheck to inspect how the widgets look when disabled.");
109 |                 (ui.add(
110 |                     egui::DragValue::new(&mut self.opacity)
111 |                         .speed(0.01)
112 |                         .range(0.0..=1.0),
113 |                 ) | ui.label("Opacity"))
114 |                 .on_hover_text("Reduce this value to make widgets semi-transparent");
115 |             }
116 |         });
117 | 
118 |         ui.separator();
119 | 
120 |         ui.vertical_centered(|ui| {
121 |             let tooltip_text = "The full egui documentation.\nYou can also click the different widgets names in the left column.";
122 |             ui.hyperlink("https://docs.rs/egui/").on_hover_text(tooltip_text);
123 |             ui.add(crate::egui_github_link_file!(
124 |                 "Source code of the widget gallery"
125 |             ));
126 |         });
127 |     }
128 | }
129 | 
130 | impl WidgetGallery {
131 |     fn gallery_grid_contents(&mut self, ui: &mut egui::Ui) {
132 |         let Self {
133 |             enabled: _,
134 |             visible: _,
135 |             opacity: _,
136 |             boolean,
137 |             radio,
138 |             scalar,
139 |             string,
140 |             color,
141 |             animate_progress_bar,
142 |             #[cfg(feature = "chrono")]
143 |             date,
144 |             #[cfg(feature = "chrono")]
145 |             with_date_button,
146 |         } = self;
147 | 
148 |         ui.add(doc_link_label("Label", "label"));
149 |         ui.label("Welcome to the widget gallery!");
150 |         ui.end_row();
151 | 
152 |         ui.add(doc_link_label("Hyperlink", "Hyperlink"));
153 |         use egui::special_emojis::GITHUB;
154 |         ui.hyperlink_to(
155 |             format!("{GITHUB} egui on GitHub"),
156 |             "https://github.com/emilk/egui",
157 |         );
158 |         ui.end_row();
159 | 
160 |         ui.add(doc_link_label("TextEdit", "TextEdit"));
161 |         ui.add(egui::TextEdit::singleline(string).hint_text("Write something here"));
162 |         ui.end_row();
163 | 
164 |         ui.add(doc_link_label("Button", "button"));
165 |         if ui.button("Click me!").clicked() {
166 |             *boolean = !*boolean;
167 |         }
168 |         ui.end_row();
169 | 
170 |         ui.add(doc_link_label("Link", "link"));
171 |         if ui.link("Click me!").clicked() {
172 |             *boolean = !*boolean;
173 |         }
174 |         ui.end_row();
175 | 
176 |         ui.add(doc_link_label("Checkbox", "checkbox"));
177 |         ui.checkbox(boolean, "Checkbox");
178 |         ui.end_row();
179 | 
180 |         ui.add(doc_link_label("RadioButton", "radio"));
181 |         ui.horizontal(|ui| {
182 |             ui.radio_value(radio, Enum::First, "First");
183 |             ui.radio_value(radio, Enum::Second, "Second");
184 |             ui.radio_value(radio, Enum::Third, "Third");
185 |         });
186 |         ui.end_row();
187 | 
188 |         ui.add(doc_link_label("SelectableLabel", "SelectableLabel"));
189 |         ui.horizontal(|ui| {
190 |             ui.selectable_value(radio, Enum::First, "First");
191 |             ui.selectable_value(radio, Enum::Second, "Second");
192 |             ui.selectable_value(radio, Enum::Third, "Third");
193 |         });
194 |         ui.end_row();
195 | 
196 |         ui.add(doc_link_label("ComboBox", "ComboBox"));
197 | 
198 |         egui::ComboBox::from_label("Take your pick")
199 |             .selected_text(format!("{radio:?}"))
200 |             .show_ui(ui, |ui| {
201 |                 ui.selectable_value(radio, Enum::First, "First");
202 |                 ui.selectable_value(radio, Enum::Second, "Second");
203 |                 ui.selectable_value(radio, Enum::Third, "Third");
204 |             });
205 |         ui.end_row();
206 | 
207 |         ui.add(doc_link_label("Slider", "Slider"));
208 |         ui.add(egui::Slider::new(scalar, 0.0..=360.0).suffix("°"));
209 |         ui.end_row();
210 | 
211 |         ui.add(doc_link_label("DragValue", "DragValue"));
212 |         ui.add(egui::DragValue::new(scalar).speed(1.0));
213 |         ui.end_row();
214 | 
215 |         ui.add(doc_link_label("ProgressBar", "ProgressBar"));
216 |         let progress = *scalar / 360.0;
217 |         let progress_bar = egui::ProgressBar::new(progress)
218 |             .show_percentage()
219 |             .animate(*animate_progress_bar);
220 |         *animate_progress_bar = ui
221 |             .add(progress_bar)
222 |             .on_hover_text("The progress bar can be animated!")
223 |             .hovered();
224 |         ui.end_row();
225 | 
226 |         ui.add(doc_link_label("Color picker", "color_edit"));
227 |         ui.color_edit_button_srgba(color);
228 |         ui.end_row();
229 | 
230 |         ui.add(doc_link_label("Image", "Image"));
231 |         let egui_icon = egui::include_image!("../../data/icon.png");
232 |         ui.add(egui::Image::new(egui_icon.clone()));
233 |         ui.end_row();
234 | 
235 |         ui.add(doc_link_label(
236 |             "Button with image",
237 |             "Button::image_and_text",
238 |         ));
239 |         if ui
240 |             .add(egui::Button::image_and_text(egui_icon, "Click me!"))
241 |             .clicked()
242 |         {
243 |             *boolean = !*boolean;
244 |         }
245 |         ui.end_row();
246 | 
247 |         #[cfg(feature = "chrono")]
248 |         if *with_date_button {
249 |             let date = date.get_or_insert_with(|| chrono::offset::Utc::now().date_naive());
250 |             ui.add(doc_link_label_with_crate(
251 |                 "egui_extras",
252 |                 "DatePickerButton",
253 |                 "DatePickerButton",
254 |             ));
255 |             ui.add(egui_extras::DatePickerButton::new(date));
256 |             ui.end_row();
257 |         }
258 | 
259 |         ui.add(doc_link_label("Separator", "separator"));
260 |         ui.separator();
261 |         ui.end_row();
262 | 
263 |         ui.add(doc_link_label("CollapsingHeader", "collapsing"));
264 |         ui.collapsing("Click to see what is hidden!", |ui| {
265 |             ui.horizontal_wrapped(|ui| {
266 |                 ui.spacing_mut().item_spacing.x = 0.0;
267 |                 ui.label("It's a ");
268 |                 ui.add(doc_link_label("Spinner", "spinner"));
269 |                 ui.add_space(4.0);
270 |                 ui.add(egui::Spinner::new());
271 |             });
272 |         });
273 |         ui.end_row();
274 | 
275 |         ui.hyperlink_to(
276 |             "Custom widget",
277 |             super::toggle_switch::url_to_file_source_code(),
278 |         );
279 |         ui.add(super::toggle_switch::toggle(boolean)).on_hover_text(
280 |             "It's easy to create your own widgets!\n\
281 |             This toggle switch is just 15 lines of code.",
282 |         );
283 |         ui.end_row();
284 |     }
285 | }
286 | 
287 | fn doc_link_label<'a>(title: &'a str, search_term: &'a str) -> impl egui::Widget + 'a {
288 |     doc_link_label_with_crate("egui", title, search_term)
289 | }
290 | 
291 | fn doc_link_label_with_crate<'a>(
292 |     crate_name: &'a str,
293 |     title: &'a str,
294 |     search_term: &'a str,
295 | ) -> impl egui::Widget + 'a {
296 |     let url = format!("https://docs.rs/{crate_name}?search={search_term}");
297 |     move |ui: &mut egui::Ui| {
298 |         ui.hyperlink_to(title, url).on_hover_ui(|ui| {
299 |             ui.horizontal_wrapped(|ui| {
300 |                 ui.label("Search egui docs for");
301 |                 ui.code(search_term);
302 |             });
303 |         })
304 |     }
305 | }
306 | 
307 | #[cfg(feature = "chrono")]
308 | #[cfg(test)]
309 | mod tests {
310 |     use super::*;
311 |     use crate::View as _;
312 |     use egui::Vec2;
313 |     use egui_kittest::Harness;
314 | 
315 |     #[test]
316 |     pub fn should_match_screenshot() {
317 |         let mut demo = WidgetGallery {
318 |             // If we don't set a fixed date, the snapshot test will fail.
319 |             date: Some(chrono::NaiveDate::from_ymd_opt(2024, 1, 1).unwrap()),
320 |             ..Default::default()
321 |         };
322 | 
323 |         for pixels_per_point in [1, 2] {
324 |             for theme in [egui::Theme::Light, egui::Theme::Dark] {
325 |                 let mut harness = Harness::builder()
326 |                     .with_pixels_per_point(pixels_per_point as f32)
327 |                     .with_theme(theme)
328 |                     .with_size(Vec2::new(380.0, 550.0))
329 |                     .build_ui(|ui| {
330 |                         egui_extras::install_image_loaders(ui.ctx());
331 |                         demo.ui(ui);
332 |                     });
333 | 
334 |                 harness.fit_contents();
335 | 
336 |                 let theme_name = match theme {
337 |                     egui::Theme::Light => "light",
338 |                     egui::Theme::Dark => "dark",
339 |                 };
340 |                 let image_name = format!("widget_gallery_{theme_name}_x{pixels_per_point}");
341 |                 harness.snapshot(&image_name);
342 |             }
343 |         }
344 |     }
345 | }
346 | 


--------------------------------------------------------------------------------
/crates/egui_demo_lib/src/demo/window_options.rs:
--------------------------------------------------------------------------------
  1 | use egui::{UiKind, Vec2b};
  2 | 
  3 | #[derive(Clone, PartialEq)]
  4 | #[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
  5 | pub struct WindowOptions {
  6 |     title: String,
  7 |     title_bar: bool,
  8 |     closable: bool,
  9 |     collapsible: bool,
 10 |     resizable: bool,
 11 |     constrain: bool,
 12 |     scroll2: Vec2b,
 13 |     disabled_time: f64,
 14 | 
 15 |     anchored: bool,
 16 |     anchor: egui::Align2,
 17 |     anchor_offset: egui::Vec2,
 18 | }
 19 | 
 20 | impl Default for WindowOptions {
 21 |     fn default() -> Self {
 22 |         Self {
 23 |             title: "🗖 Window Options".to_owned(),
 24 |             title_bar: true,
 25 |             closable: true,
 26 |             collapsible: true,
 27 |             resizable: true,
 28 |             constrain: true,
 29 |             scroll2: Vec2b::TRUE,
 30 |             disabled_time: f64::NEG_INFINITY,
 31 |             anchored: false,
 32 |             anchor: egui::Align2::RIGHT_TOP,
 33 |             anchor_offset: egui::Vec2::ZERO,
 34 |         }
 35 |     }
 36 | }
 37 | 
 38 | impl crate::Demo for WindowOptions {
 39 |     fn name(&self) -> &'static str {
 40 |         "🗖 Window Options"
 41 |     }
 42 | 
 43 |     fn show(&mut self, ctx: &egui::Context, open: &mut bool) {
 44 |         let Self {
 45 |             title,
 46 |             title_bar,
 47 |             closable,
 48 |             collapsible,
 49 |             resizable,
 50 |             constrain,
 51 |             scroll2,
 52 |             disabled_time,
 53 |             anchored,
 54 |             anchor,
 55 |             anchor_offset,
 56 |         } = self.clone();
 57 | 
 58 |         let enabled = ctx.input(|i| i.time) - disabled_time > 2.0;
 59 |         if !enabled {
 60 |             ctx.request_repaint();
 61 |         }
 62 | 
 63 |         use crate::View as _;
 64 |         let mut window = egui::Window::new(title)
 65 |             .id(egui::Id::new("demo_window_options")) // required since we change the title
 66 |             .resizable(resizable)
 67 |             .constrain(constrain)
 68 |             .collapsible(collapsible)
 69 |             .title_bar(title_bar)
 70 |             .scroll(scroll2)
 71 |             .enabled(enabled);
 72 |         if closable {
 73 |             window = window.open(open);
 74 |         }
 75 |         if anchored {
 76 |             window = window.anchor(anchor, anchor_offset);
 77 |         }
 78 |         window.show(ctx, |ui| self.ui(ui));
 79 |     }
 80 | }
 81 | 
 82 | impl crate::View for WindowOptions {
 83 |     fn ui(&mut self, ui: &mut egui::Ui) {
 84 |         let Self {
 85 |             title,
 86 |             title_bar,
 87 |             closable,
 88 |             collapsible,
 89 |             resizable,
 90 |             constrain,
 91 |             scroll2,
 92 |             disabled_time: _,
 93 |             anchored,
 94 |             anchor,
 95 |             anchor_offset,
 96 |         } = self;
 97 |         ui.horizontal(|ui| {
 98 |             ui.label("title:");
 99 |             ui.text_edit_singleline(title);
100 |         });
101 | 
102 |         ui.horizontal(|ui| {
103 |             ui.group(|ui| {
104 |                 ui.vertical(|ui| {
105 |                     ui.checkbox(title_bar, "title_bar");
106 |                     ui.checkbox(closable, "closable");
107 |                     ui.checkbox(collapsible, "collapsible");
108 |                     ui.checkbox(resizable, "resizable");
109 |                     ui.checkbox(constrain, "constrain")
110 |                         .on_hover_text("Constrain window to the screen");
111 |                     ui.checkbox(&mut scroll2[0], "hscroll");
112 |                     ui.checkbox(&mut scroll2[1], "vscroll");
113 |                 });
114 |             });
115 |             ui.group(|ui| {
116 |                 ui.vertical(|ui| {
117 |                     ui.checkbox(anchored, "anchored");
118 |                     if !*anchored {
119 |                         ui.disable();
120 |                     }
121 |                     ui.horizontal(|ui| {
122 |                         ui.label("x:");
123 |                         ui.selectable_value(&mut anchor[0], egui::Align::LEFT, "Left");
124 |                         ui.selectable_value(&mut anchor[0], egui::Align::Center, "Center");
125 |                         ui.selectable_value(&mut anchor[0], egui::Align::RIGHT, "Right");
126 |                     });
127 |                     ui.horizontal(|ui| {
128 |                         ui.label("y:");
129 |                         ui.selectable_value(&mut anchor[1], egui::Align::TOP, "Top");
130 |                         ui.selectable_value(&mut anchor[1], egui::Align::Center, "Center");
131 |                         ui.selectable_value(&mut anchor[1], egui::Align::BOTTOM, "Bottom");
132 |                     });
133 |                     ui.horizontal(|ui| {
134 |                         ui.label("Offset:");
135 |                         ui.add(egui::DragValue::new(&mut anchor_offset.x));
136 |                         ui.add(egui::DragValue::new(&mut anchor_offset.y));
137 |                     });
138 |                 });
139 |             });
140 |         });
141 | 
142 |         ui.separator();
143 |         let on_top = Some(ui.layer_id()) == ui.ctx().top_layer_id();
144 |         ui.label(format!("This window is on top: {on_top}."));
145 | 
146 |         ui.separator();
147 |         ui.horizontal(|ui| {
148 |             if ui.button("Disable for 2 seconds").clicked() {
149 |                 self.disabled_time = ui.input(|i| i.time);
150 |             }
151 |             egui::reset_button(ui, self, "Reset");
152 |             if ui
153 |                 .button("Close")
154 |                 .on_hover_text("You can collapse / close Windows via Ui::close")
155 |                 .clicked()
156 |             {
157 |                 // Calling close would close the collapsible within the window
158 |                 // ui.close();
159 |                 // Instead, we close the window itself
160 |                 ui.close_kind(UiKind::Window);
161 |             }
162 |             ui.add(crate::egui_github_link_file!());
163 |         });
164 |     }
165 | }
166 | 


--------------------------------------------------------------------------------


