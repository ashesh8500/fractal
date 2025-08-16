## Fractal Frontend Refactor Plan (Prototype → Production Yew/WASM Workbench)

Status: Draft pillar document for production migration (replace egui web usage with Yew-based UI). Scope: Strategy Workbench first, then broader portfolio visualization.

---
### 1. Design Philosophy
Guiding principles (memorize acronym LO-DPACE):
1. Lean: smallest surface to deliver strategy iteration & insight; avoid premature abstractions.
2. Observable: explicit state transitions; easy instrumentation & logging of user + data flow events.
3. Deterministic: pure data transforms for analytics (idempotent functions, no hidden globals).
4. Progressive: degrade gracefully (charts → basic text metrics if Canvas unsupported).
5. Accessible: keyboard-first flows, semantic regions, ARIA labeling for interactive charts.
6. Composable: orthogonal modules (API client, domain transforms, render primitives, shell layouts).
7. Extensible: plugin slots for panels (allocations, trades, risk, ML diagnostics) without core edits.

Visual & UX Tenets:
- Information density > chrome; emphasize clarity through spacing hierarchy and subdued palette.
- Direct manipulation: edit → validate → backtest loop w/ immediate visual feedback.
- Progressive disclosure: advanced diagnostics behind expandable sections (avoid overwhelming new users).
- Temporal continuity: preserve scroll/selection & diff highlighting across edits and backtests.
- Performance (perceived): optimistic UI for fast ops; spinner only >200ms latency; micro-skeletons for charts.

---
### 2. High-Level Architecture

Layered model (bottom→top):
1. Transport Layer: HTTP (initial), WebSocket/SSE (streaming progress) via thin wrappers.
2. API Client Layer: typed async functions mapping endpoints → strongly typed DTOs.
3. Domain Services: transforms & enrichment (e.g., compute cumulative returns, normalized drawdowns, join series for aligned timestamps, caching last N results for diff metrics).
4. State Layer: global `AppState` (user/session/env/theme) + feature-scoped workbench state machine; unidirectional event dispatch (Action → Reducer → State → View).
5. Presentation Components: pure Yew function components; minimal logic (subscribe & render).
6. Render Primitives: canvas chart engine, table virtualizer, code editor wrapper (Monaco) – isolated side-effects.
7. Shell & Layout: responsive grid, panel registry, plugin injection points.

Data Flow: User Event → Action → Reducer mutates State → Effects (async) dispatch success/failure actions → Rerender minimal diff → Chart engine incremental draw.

---
### 3. Module Breakdown (Production Target)

`src/`
- `main.rs` (wasm entry) / `lib.rs` (renderer bootstrap, panic hook, global providers).
- `api/` (each endpoint file or mod grouping):
  - `mod.rs` (re-exports, base client builder)
  - `strategies.rs` (list, get_source, validate, register, inline_backtest)
  - Future: `stream.rs` (websocket subscription for live backtest progress / logs)
- `dto/` (serde DTOs mirroring backend contracts; keep flat to avoid cyc deps)
- `domain/`
  - `metrics.rs` (derived metrics: CAGR, calmar, sortino, rolling stats)
  - `alignment.rs` (time alignment utilities for series, resampling)
  - `transforms.rs` (portfolio_values → drawdowns if backend omission, normalization helpers)
  - `cache.rs` (LRU for recent backtest responses keyed by source hash)
- `state/`
  - `actions.rs` (enum WorkbenchAction)
  - `reducer.rs` (pure state transitions)
  - `selectors.rs` (memoized derived slices for components)
  - `types.rs` (AppState, WorkbenchState, ChartState etc.)
- `effects/`
  - async side-effect orchestrators (separate from UI components) mapping actions → API calls.
- `components/`
  - `editor/` (Monaco integration wrapper; diff + syntax highlight; lazy load)
  - `charts/` (canvas engine, overlays, interactivity, theming hooks)
  - `panels/` (StrategyListPanel, SourcePanel, ParamsPanel, ResultsPanel, TradesPanel, AllocationsPanel)
  - `layout/` (ResizableSplit, DockArea, PanelContainer)
  - `primitives/` (Button, Input, Toggle, Badge, Tooltip, Skeleton, ScrollArea)
- `theme/`
  - `tokens.rs` (semantic color + spacing + typography tokens)
  - `mode.rs` (light/dark mapping) / future custom themes.
- `util/` (time formatting, percent formatting, throttling/debouncing, hash of strategy code)
- `plugin/` (registry trait + dynamic panel mounting) – future extension mechanism.

---
### 4. Backend API Contracts (Current Minimal Set)

Base: `/api/v1`
1. `GET /strategies` → `{ strategies: [String] }`
2. `GET /strategies/source?module=<name>` → `{ module: String, source: String }`
3. `POST /strategies/validate` Body: `{ code: String, class_name?: String }` → `{ ok: bool, message: String, class_name?: String }`
4. `POST /strategies/register` Body: `{ class_name: String, code: String, strategy_name?: String }` → `{ ok: bool, class_name?: String, message?: String }`
5. `POST /strategies/backtest-inline` Body: `{ code, symbols[], start_date, end_date, initial_capital, commission, slippage, rebalance, benchmark }`
   → `{ ok, message?, strategy_name?, total_return?, annualized_return?, volatility?, sharpe_ratio?, max_drawdown?, benchmark_return?, alpha?, beta?, portfolio_values?, timestamps?, drawdowns?, daily_returns?, benchmark_values?, holdings_history?, rebalance_details?, allocation_weights? }`

Planned Additions:
- `GET /strategies/templates` (optional pattern library)
- `WS /strategies/backtest-stream` (progress ticks { pct, equity, last_trade })
- `GET /strategies/metrics/schema` (dynamic metric registry)

Contract Discipline:
- All optional fields explicit `Option<T>` – front-end gracefully degrades.
- Version header (`x-api-rev`) for forward compatibility; front-end logs mismatch.

---
### 5. Chart Engine (Canvas Architecture)

Goals: High-performance incremental redraw, unified time axis, interactivity (hover, tooltip, crosshair, pan/zoom), themable.

Design:
1. Stateless draw functions replaced by `ChartHandle` owning off-screen buffers (double buffering reduces flicker).
2. Series Registry: each chart registers named series with metadata (color, scale group, visibility, stacking mode).
3. Scale System: multi-scale (left primary, right secondary) + percent overlay (normalize to 1.0 base). Align timestamps by index mapping precomputed by domain layer.
4. Interaction Layer: pointer events captured at wrapper component → translate to data coordinates → request overlays (crosshair, value labels) → partial re-render overlay layer only (layered canvases: base + overlay).
5. Layout: responsive sizing via ResizeObserver (wasm binding) triggers recalculation of scales with throttling.
6. Accessibility: ARIA live region updates on focus navigation (arrow keys cycle key points, announce date/value).

Performance Considerations:
- Avoid full redraw on every mousemove: paint static data once; overlay separate canvas (crosshair). 
- Precompute min/max ranges; maintain incremental min/max for streaming updates (O(1) rather than scanning entire vector).
- Memory: cap retained historical points (e.g., downsample beyond N using largest-triangle-three-buckets or simple stride for display scale).

---
### 6. State Management Strategy

Pattern: Single root reducer per domain slice. Yew components subscribe to narrowed selectors returning immutable snapshots (derive PartialEq → skip re-render).

Action Taxonomy:
- User Intents: LoadStrategies, SelectStrategy, EditSource, Validate, Register, RunBacktest, ChangeParam(Field, Value)
- System Events: StrategiesLoaded, SourceLoaded, ValidationResult, BacktestResult, BacktestError, StreamingProgress, ThemeChanged
- Internal: SetStatus, ClearStatus, CacheInsert, CacheHit

Derivations (Selectors):
- `is_dirty` (edited != source)
- `equity_series` (portfolio_values normalized if base not 1.0)
- `alpha_beta_summary` (alpha, beta or placeholders)
- `risk_badges` (max_dd, vol, sharpe buckets → color-coded severity)

Backtest Flow FSM:
- Idle → Running (optimistic UI) → Success (Result) | Failure (Error) → Idle
- Streaming branch: Running(Stream) with partial updates populating ephemeral progress state.

---
### 7. Code Editor Integration (Monaco)

Approach:
1. Lazy load Monaco via dynamic ES module injection once SourcePanel mounts.
2. Provide wrapper component exposing events: on_change, on_cursor_data, on_diff_ready.
3. Diff Mode: base = last validated source; highlight unsaved edits.
4. Provide language configuration for Python (syntax / basic lint markers via server feedback).

Security: No evaluation of user code on client. All execution remains backend. Sanitize displayed server messages.

---
### 8. Theming & Design Tokens

Token Buckets:
- Color (semantic): bg.surface, bg.sunken, border.default, text.primary, text.muted, accent.primary, accent.positive, accent.negative, warn, grid.line.
- Spacing: xs(2), sm(4), md(8), lg(12), xl(16), xxl(24)
- Typography roles: heading, body, mono, label, metric.
- Elevation: depth0..depth3 (shadow or border intensities).

Runtime Theme Switch: context provider + CSS variables injected at root; canvas engine reads computed styles or stored token map.

---
### 9. UX Workflow Enhancements

Shortcuts:
- Cmd+Enter: Run backtest
- Cmd+S: Validate (also triggers diff baseline update on success)
- Cmd+K: Focus symbol input
- Arrow Up/Down in strategy list cycles selection & auto-load source (debounced)

Notifications: non-blocking toast system (success / warn / error) with queue & timeout.

Metrics Badges: color-coded pills (neutral/green/amber/red) using thresholds (configurable) for volatility, drawdown, sharpe.

Empty & Error States: purposeful copy w/ action (e.g., “No backtest yet – run one (Cmd+Enter)”).

---
### 10. Extensibility / Plugin Model (Phase 4+)

Panel Registration:
- Trait `WorkbenchPanel` { id(), label(), mount(props) }.
- Registry static vector mutated during init (feature-gated). Core layout iterates registry to render panels in configured slots.

Extension Use Cases:
- Custom risk metrics panel
- Algorithm explanation (LLM) panel
- Trade path visualizer

Isolation: Panels receive read-only selectors + controlled dispatch (no direct state mutation).

---
### 11. Testing Strategy

Test Layers:
1. Pure Units: domain transforms (metrics, drawdown) – standard Rust tests.
2. Wasm Tests: limited (feature gating) using `wasm-bindgen-test` for chart util invariants.
3. Integration: mock HTTP server (compile-time cfg) verifying action→state transitions.
4. Visual Regression (optional): deterministic canvas snapshot hashing (serialize pixel subset) for core charts.
5. E2E (Phase 3+): Playwright hitting built wasm bundle (scripts separate repo / CI job).

CI Gates:
- Build (native + wasm)
- Lints (clippy restricted set), fmt, unit tests
- (Optional) Snapshot diff threshold

---
### 12. Performance & Instrumentation

Metrics Captured (structured logs → console + optional backend ingestion):
- Backtest latency (queue, compute, total)
- Render time (first meaningful paint, chart draw duration)
- Action dispatch counts per minute
- Memory footprint (approx vector sizes; dev-only)

Optimizations Roadmap:
1. Memoized selectors to reduce Yew rerenders.
2. Chart virtualization (downsample for >10k points).
3. Streaming partial backtest updates (plots incremental).
4. Worker Offload: heavy transforms (rolling stats) to WebWorker (via `wasm-bindgen-rayon` future consideration).

---
### 13. Accessibility Checklist

- Keyboard navigation order stable & logical.
- Focus outlines preserved (custom but visible).
- ARIA roles for listbox (strategy list), tablist (future panel tabs), status region (live backtest status).
- Chart alternative text summarizing key metrics.
- Color contrast AA for text & line hues > 4.5:1 baseline.

---
### 14. Security Considerations

- Strict Content Security Policy (no inline eval once Monaco loaded through hashed script tag).
- Separate origin for backend optional (CORS locked to explicit host in prod build config).
- Strategy source never persisted client side beyond memory (opt-in localStorage toggle for drafts with hashing + version tagging).
- Input validation: symbol whitelist (A-Z,.), date format ISO, numeric ranges clamped client-side before request.

---
### 15. Migration & Phased Delivery

Phase 0 (DONE): Prototype (list / load / edit / validate / backtest + basic charts).
Phase 1 (Foundations): State layer refactor, API client modularization, theming tokens, improved chart engine base, keyboard shortcuts.
Phase 2 (Parity): Monaco editor, diff view, interactive charts (hover tooltips, pan/zoom), metrics badges, allocations & trades panels.
Phase 3 (Advanced Analytics): Rolling metrics, factor exposure, distribution charts (histogram, violin), export (CSV/JSON), strategy templating.
Phase 4 (Streaming & Extensibility): WebSocket progress, plugin panel registry, panel layout persistence, snapshot share links.
Phase 5 (Optimization & Polish): Performance tuning, accessibility audits, visual regression harness, documentation site.

Cutover Strategy:
- Keep egui native for desktop packaging if needed; remove wasm path.
- Tag final egui web commit; freeze; begin Yew-only merges.
- Gate new features behind Yew flag until Phase 2 parity; then delete egui web-specific code paths.

Rollback Plan:
- Maintain branch `egui_web_legacy` for hotfixes until 30 days after full cutover.

---
### 16. Coding Conventions

Rust (frontend):
- No `unwrap()` outside tests or clearly impossible invariants (documented). Use `?` and map errors to user status gracefully.
- Modules favor small file sizes (<400 LOC). Extract pure helpers to domain/util.
- Naming: `*_state.rs` (pure types), `*_actions.rs`, `*_reducer.rs`, `*_panel.rs`.

UI Style:
- Inline style objects replaced by centralized token-driven classes (Phase 1.5) generated from tokens -> hashed class names (simple build step, or just style module constants initially).
- Avoid magic numbers: use spacing & color tokens.

---
### 17. Open Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Chart engine scope creep | Delays parity | MVP line/area/bar + hover first; defer zoom/pan |
| Monaco bundle size | Load perf | Lazy load + gzip + optionally use dynamic import after first interaction |
| Streaming complexity | Instability | Introduce after stable synchronous backtests; feature flag |
| Response schema drift | Runtime errors | Version header; tolerant parsing, log unknown fields |
| Large strategies causing lag | Editor UX | Debounce validations; diff only changed ranges |

---
### 18. Minimal File References (Context Only)

Current Prototype Files Relevant:
- `refactor_ui/src/strategy_workbench.rs` (will split into panels & actions)
- `refactor_ui/src/charts.rs` (to evolve into engine under `components/charts/`)
- Backend: `backend_server/app/routes.py` (strategy endpoints), `backend_server/app/schemas.py` (DTO fields).

No other legacy egui files needed for refactor decisions.

---
### 19. Immediate Next Steps (Actionable Sprint Backlog)

1. Establish `api/strategies.rs` with typed functions + move DTOs out of component file.
2. Introduce `state/` directory with actions & reducer (migrate WorkbenchState logic).
3. Replace inline styles for core surfaces with token constants.
4. Implement responsive chart sizing (ResizeObserver wrapper) & overlay canvas for hover crosshair.
5. Add keyboard shortcuts (Cmd+Enter, Cmd+S) & status toast system.
6. Integrate Monaco (lazy load) — basic editing + diff vs last validated.
7. Add allocation & trades panel placeholders (degrade to “No data” if missing fields).

---
### 20. Success Criteria (Phase 2 Parity)

Functional:
- All current egui web features reproduced or improved.
- Strategy validate & backtest flows < 500ms UI overhead (excluding backend compute).
- Charts interactive (hover + values) with < 16ms average frame on interaction.

Qualitative:
- Users can iterate code-change → validate → backtest without cognitive friction.
- Clear visual hierarchy; metrics readability at a glance.

Operational:
- CI green on wasm build & unit tests.
- No console panic logs in normal flows.

---
### 21. Long-Term (Post Parity) Vision

- Hybrid packaging: WASM UI inside Tauri (desktop) + pure web deploy reuse.
- Data streaming & partial real-time updates (live paper trading integration).
- Extensible strategy metadata introspection (docstrings, parameters surfaced automatically).
- Scenario runner (batch backtests with parameter grid; results matrix visualization).

---
End of Plan.
