# Refactor UI Prototype (Strategy Workbench)

Minimal standalone Yew + Rust/WASM implementation of the Strategy Workbench
against the existing FastAPI backend (`/api/v1/...`). Focus: lean, high-performance
feel (monospace, low-chrome) rather than commercial dashboard styling.

## Features
- List strategies
- Load & edit source
- Validate & register strategy
- Inline backtest with core metrics
- Lightweight state, no JS framework beyond Yew

## Build (wasm)
```
cargo install trunk wasm-bindgen-cli
cd refactor_ui
trunk serve --open
```
(Ensure backend running at http://127.0.0.1:8000)

From the repository root you can also run (note: pass the index path positionally, no `--index` flag exists):
```
trunk serve refactor_ui/index.html --config refactor_ui/Trunk.toml --dist refactor_ui/dist --open
```
Or use the helper script (after making it executable):
```
chmod +x serve_refactor_ui.sh
./serve_refactor_ui.sh
```

Override API base:
```
FRONTEND_API_BASE=http://localhost:8000/api/v1 trunk serve
```

## Next Steps
- Add charts via web-sys + canvas or integrate Plotly/ECharts
- Progressive enhancement: live diff view, code syntax highlight (Monaco via wasm interop)
- Streaming progress for backtests
