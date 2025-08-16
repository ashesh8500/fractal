use web_sys::{HtmlCanvasElement, CanvasRenderingContext2d};
use wasm_bindgen::JsCast;

pub struct LineSeries<'a> { pub label: &'a str, pub data: &'a [f64], pub color: &'a str }

pub fn draw_line_chart(id: &str, series: &[LineSeries], height: i32) {
    if series.is_empty() { return; }
    let window = web_sys::window().unwrap();
    let document = window.document().unwrap();
    let Some(canvas_el) = document.get_element_by_id(id) else { return; };
    let canvas: HtmlCanvasElement = match canvas_el.dyn_into() { Ok(c) => c, Err(_) => return };
    let width = canvas.client_width() as i32;
    canvas.set_width(width as u32);
    canvas.set_height(height as u32);
    let ctx: CanvasRenderingContext2d = match canvas.get_context("2d").unwrap().unwrap().dyn_into() { Ok(c) => c, Err(_) => return };
    ctx.set_fill_style(&"#0f1115".into());
    ctx.fill_rect(0.0, 0.0, width as f64, height as f64);
    let mut gmin = f64::INFINITY; let mut gmax = f64::NEG_INFINITY; let mut max_len = 0usize;
    for s in series { for v in s.data { if v.is_finite() { if *v < gmin { gmin=*v;} if *v>gmax { gmax=*v;} } } if s.data.len()>max_len { max_len=s.data.len(); }}
    if !gmax.is_finite() || !gmin.is_finite() || max_len < 2 { return; }
    if (gmax - gmin).abs() < 1e-12 { gmax += 1.0; gmin -= 1.0; }
    let left_pad = 34.0; let right_pad = 8.0; let top_pad = 6.0; let bottom_pad = 14.0;
    let plot_w = (width as f64) - left_pad - right_pad; let plot_h = (height as f64) - top_pad - bottom_pad;
    ctx.set_stroke_style(&"#1f2530".into()); ctx.set_line_width(1.0);
    for i in 0..=4 { let y = top_pad + plot_h * (i as f64 / 4.0); ctx.begin_path(); ctx.move_to(left_pad, y); ctx.line_to(left_pad + plot_w, y); ctx.stroke(); }
    ctx.set_fill_style(&"#6a7688".into()); ctx.set_font("10px sans-serif");
    let min_txt = format!("{:.2}", gmin); let max_txt = format!("{:.2}", gmax);
    ctx.fill_text(&max_txt, 2.0, top_pad + 8.0).ok();
    ctx.fill_text(&min_txt, 2.0, top_pad + plot_h).ok();
    for s in series {
        ctx.set_stroke_style(&s.color.into()); ctx.set_line_width(1.5); ctx.begin_path();
        for (i, v) in s.data.iter().enumerate() { if !v.is_finite() { continue; } let x = left_pad + (i as f64 / (max_len - 1) as f64) * plot_w; let y = top_pad + (gmax - v) / (gmax - gmin) * plot_h; if i == 0 { ctx.move_to(x, y); } else { ctx.line_to(x, y); } }
        ctx.stroke();
    }
    let mut lx = left_pad; let ly = top_pad + 4.0;
    for s in series { ctx.set_fill_style(&s.color.into()); ctx.fill_rect(lx, ly - 7.0, 12.0, 3.0); ctx.set_fill_style(&"#9aa8b8".into()); ctx.fill_text(s.label, lx + 16.0, ly).ok(); lx += 78.0; }
}

pub fn draw_area_chart(id: &str, data: &[f64], height: i32, color: &str) {
    if data.len() < 2 { return; }
    let window = web_sys::window().unwrap();
    let document = window.document().unwrap();
    let Some(canvas_el) = document.get_element_by_id(id) else { return; };
    let canvas: HtmlCanvasElement = match canvas_el.dyn_into() { Ok(c) => c, Err(_) => return };
    let width = canvas.client_width() as i32; canvas.set_width(width as u32); canvas.set_height(height as u32);
    let ctx: CanvasRenderingContext2d = match canvas.get_context("2d").unwrap().unwrap().dyn_into() { Ok(c) => c, Err(_) => return };
    ctx.set_fill_style(&"#0f1115".into()); ctx.fill_rect(0.0, 0.0, width as f64, height as f64);
    let mut min = f64::INFINITY; let mut max = f64::NEG_INFINITY; for v in data { if v.is_finite() { if *v < min { min=*v;} if *v>max { max=*v;} }}
    if !min.is_finite() || !max.is_finite() { return; }
    if (max - min).abs() < 1e-12 { max += 1.0; min -= 1.0; }
    let left_pad = 34.0; let right_pad = 8.0; let top_pad = 6.0; let bottom_pad = 14.0;
    let plot_w = (width as f64) - left_pad - right_pad; let plot_h = (height as f64) - top_pad - bottom_pad;
    ctx.set_stroke_style(&"#2a3038".into()); ctx.set_line_width(1.0);
    if min < 0.0 && max > 0.0 { let zero_y = top_pad + (max / (max - min)) * plot_h; ctx.begin_path(); ctx.move_to(left_pad, zero_y); ctx.line_to(left_pad + plot_w, zero_y); ctx.stroke(); }
    ctx.begin_path();
    for (i,v) in data.iter().enumerate() { if !v.is_finite() { continue; } let x = left_pad + (i as f64 / (data.len()-1) as f64) * plot_w; let y = top_pad + (max - v)/(max - min) * plot_h; if i==0 { ctx.move_to(x,y);} else { ctx.line_to(x,y);} }
    ctx.line_to(left_pad + plot_w, top_pad + plot_h); ctx.line_to(left_pad, top_pad + plot_h); ctx.close_path();
    ctx.set_fill_style(&format!("{}33", color).into()); ctx.fill();
    ctx.set_stroke_style(&color.into()); ctx.set_line_width(1.2); ctx.stroke();
}

pub fn draw_bar_chart(id: &str, data: &[f64], height: i32, pos_color: &str, neg_color: &str) {
    if data.is_empty() { return; }
    let window = web_sys::window().unwrap();
    let document = window.document().unwrap();
    let Some(canvas_el) = document.get_element_by_id(id) else { return; };
    let canvas: HtmlCanvasElement = match canvas_el.dyn_into() { Ok(c) => c, Err(_) => return };
    let width = canvas.client_width() as i32; canvas.set_width(width as u32); canvas.set_height(height as u32);
    let ctx: CanvasRenderingContext2d = match canvas.get_context("2d").unwrap().unwrap().dyn_into() { Ok(c) => c, Err(_) => return };
    ctx.set_fill_style(&"#0f1115".into()); ctx.fill_rect(0.0, 0.0, width as f64, height as f64);
    let mut min = 0.0; let mut max = 0.0; for v in data { if *v < min { min = *v; } if *v > max { max = *v; }} if (max - min).abs() < 1e-9 { max = 1.0; min = -1.0; }
    let left_pad = 28.0; let right_pad = 6.0; let top_pad = 4.0; let bottom_pad = 12.0;
    let plot_w = (width as f64) - left_pad - right_pad; let plot_h = (height as f64) - top_pad - bottom_pad;
    let zero_y = if min < 0.0 { top_pad + (max / (max - min)) * plot_h } else { top_pad + plot_h };
    ctx.set_stroke_style(&"#2a3038".into()); ctx.set_line_width(1.0); ctx.begin_path(); ctx.move_to(left_pad, zero_y); ctx.line_to(left_pad + plot_w, zero_y); ctx.stroke();
    let bar_w = plot_w / (data.len().max(1) as f64);
    for (i,v) in data.iter().enumerate() { if !v.is_finite() { continue; } let x = left_pad + i as f64 * bar_w + 0.5; let y = top_pad + (max - v)/(max - min) * plot_h; let h = (zero_y - y).abs(); ctx.set_fill_style(&(if *v>=0.0 { pos_color } else { neg_color }).into()); if *v>=0.0 { ctx.fill_rect(x, y, bar_w*0.9, h); } else { ctx.fill_rect(x, zero_y, bar_w*0.9, h); } }
}
