"""
LangChain Tools for Strategy Workbench.

These tools constrain the LLM to operate within the supported strategy pattern:
- Strategies must subclass BaseStrategy and implement `execute(...) -> StrategyResult`.
- Trades must use portfolio_lib.models.strategy.Trade and TradeAction.
- Only allowed file area for writes: portfolio_lib/services/strategy/custom/
- No network/file access outside the repository.

The tools provide minimal, safe operations to list, read, validate, create and patch
strategy implementations.
"""
from __future__ import annotations

import importlib
import inspect
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

from portfolio_lib.services.strategy.base import BaseStrategy

# Safe base path for user strategies
CUSTOM_STRATEGY_DIR = os.path.join(
    os.path.dirname(__file__), "..", "services", "strategy", "custom"
)
CUSTOM_STRATEGY_DIR = os.path.abspath(CUSTOM_STRATEGY_DIR)

# Ensure package path is importable
PKG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

CUSTOM_PKG = "portfolio_lib.services.strategy.custom"


@dataclass
class ValidationResult:
    ok: bool
    message: str
    module: Optional[str] = None
    class_name: Optional[str] = None


def ensure_custom_pkg() -> None:
    os.makedirs(CUSTOM_STRATEGY_DIR, exist_ok=True)
    init_file = os.path.join(CUSTOM_STRATEGY_DIR, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w", encoding="utf-8") as f:
            f.write("\n# User-created strategies live here.\n")


def list_available_strategies() -> List[str]:
    """List import paths of all BaseStrategy subclasses in stock and custom packages."""
    ensure_custom_pkg()
    # import used to ensure package is discoverable; kept for side-effects if needed
    import portfolio_lib.services.strategy  # noqa: F401

    names: List[str] = []

    # Walk package modules
    def _collect(pkg_name: str) -> None:
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            return
        pkg_path = getattr(pkg, "__path__", None)
        if not pkg_path:
            return
        import pkgutil

        for _, mod_name, _ in pkgutil.iter_modules(pkg.__path__, pkg_name + "."):
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                continue
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if obj is BaseStrategy:
                    continue
                if issubclass(obj, BaseStrategy):
                    names.append(f"{mod_name}:{obj.__name__}")

    _collect("portfolio_lib.services.strategy")
    _collect(CUSTOM_PKG)

    # De-duplicate
    out = sorted(list(dict.fromkeys(names)))
    return out


def read_strategy_source(module_path: str) -> str:
    """Read the source of a strategy module given 'module.submodule:ClassName' or module path only."""
    ensure_custom_pkg()
    if ":" in module_path:
        module_path, _ = module_path.split(":", 1)
    mod = importlib.import_module(module_path)
    try:
        return inspect.getsource(mod)
    except OSError:
        # Might be a compiled module; try file
        file = getattr(mod, "__file__", None)
        if not file or not os.path.exists(file):
            raise FileNotFoundError(f"Cannot locate file for {module_path}")
        with open(file, "r", encoding="utf-8") as f:
            return f.read()


SAFE_CLASS_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SAFE_FILE_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+\.py$")


def _sanitize_class_name(name: str) -> str:
    name = name.strip()
    if not SAFE_CLASS_NAME_RE.match(name):
        raise ValueError("Invalid class name. Use alphanumerics and underscores, starting with a letter/_.")
    return name


def _deduce_file_name(class_name: str) -> str:
    snake = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", class_name)
    snake = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", snake).lower()
    return f"{snake}.py"


TEMPLATE = """from typing import Dict
import pandas as pd
import numpy as np
from portfolio_lib.models.strategy import StrategyConfig, StrategyResult, Trade, TradeAction
from portfolio_lib.services.strategy.base import BaseStrategy

class {class_name}(BaseStrategy):
    '''LLM-authored strategy. Keep compute light; no external I/O.'''
    def __init__(self):
        super().__init__("{strategy_name}")

    def execute(
        self,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        config: StrategyConfig,
    ) -> StrategyResult:
        from datetime import datetime, timezone
        self._validate_inputs(portfolio_weights, price_history, current_prices)

        # Example: equal-weight rebalance with max position size
        tickers = list(portfolio_weights.keys()) or list(price_history.keys())
        n = len(tickers)
        if n == 0:
            raise ValueError("No symbols available")
        max_w = getattr(config, "max_position_size", 1.0)
        target = {t: min(1.0 / n, max_w) for t in tickers}

        # Normalize
        s = pd.Series(target)
        s = s / float(s.sum())

        # Compute deltas and emit trades as weight fractions
        trades = []
        for t in tickers:
            cur = float(portfolio_weights.get(t, 0.0))
            tar = float(s.get(t, 0.0))
            delta = tar - cur
            if delta > 1e-6:
                trades.append(Trade(symbol=t, action=TradeAction.BUY, quantity=delta))
            elif delta < -1e-6:
                trades.append(Trade(symbol=t, action=TradeAction.SELL, quantity=-delta))

        return StrategyResult(
            strategy_name=self.name,
            trades=trades,
            expected_return=0.0,
            timestamp=datetime.now(timezone.utc),
            confidence=0.5,
            new_weights=s.to_dict(),
        )
"""


def write_new_strategy(class_name: str, strategy_name: Optional[str] = None, source: Optional[str] = None) -> Tuple[str, str]:
    """Create a new strategy module in the custom package.

    Returns (module_import_path, class_name)
    """
    ensure_custom_pkg()
    class_name = _sanitize_class_name(class_name)
    file_name = _deduce_file_name(class_name)
    if not SAFE_FILE_NAME_RE.match(file_name):
        raise ValueError("Unsafe filename generated")

    path = os.path.join(CUSTOM_STRATEGY_DIR, file_name)
    if os.path.exists(path):
        raise FileExistsError(f"File already exists: {path}")

    if source is None:
        strategy_name = strategy_name or class_name
        source = TEMPLATE.format(class_name=class_name, strategy_name=strategy_name)

    with open(path, "w", encoding="utf-8") as f:
        f.write(source)

    # Invalidate import caches and return import path
    importlib.invalidate_caches()
    module_path = f"{CUSTOM_PKG}.{file_name[:-3]}"
    return module_path, class_name


def validate_strategy(module_cls: str) -> ValidationResult:
    """Validate that the given module:Class is importable and a BaseStrategy subclass with execute method."""
    ensure_custom_pkg()
    if ":" in module_cls:
        module_name, cls_name = module_cls.split(":", 1)
    else:
        module_name, cls_name = module_cls, None

    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        return ValidationResult(False, f"Import failed: {e}")

    if cls_name is None:
        # try to find the first BaseStrategy subclass
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if obj is BaseStrategy:
                continue
            if issubclass(obj, BaseStrategy):
                cls_name = obj.__name__
                break
        if cls_name is None:
            return ValidationResult(False, "No BaseStrategy subclass found in module")

    try:
        cls = getattr(mod, cls_name)
    except Exception as e:
        return ValidationResult(False, f"Class not found: {e}", module=module_name)

    if not issubclass(cls, BaseStrategy):
        return ValidationResult(False, "Class is not a BaseStrategy subclass", module=module_name, class_name=cls_name)

    # Check execute signature
    sig = inspect.signature(cls.execute)
    params = list(sig.parameters.keys())
    expected = ["self", "portfolio_weights", "price_history", "current_prices", "config"]
    if params[:5] != expected:
        return ValidationResult(False, f"Invalid execute signature: {params}", module=module_name, class_name=cls_name)

    return ValidationResult(True, "OK", module=module_name, class_name=cls_name)


def instantiate_strategy(module_cls: str) -> BaseStrategy:
    ensure_custom_pkg()
    if ":" in module_cls:
        module_name, cls_name = module_cls.split(":", 1)
    else:
        module_name, cls_name = module_cls, None
    mod = importlib.import_module(module_name)
    if cls_name is None:
        cls = next(
            obj for _, obj in inspect.getmembers(mod, inspect.isclass) if issubclass(obj, BaseStrategy) and obj is not BaseStrategy
        )
    else:
        cls = getattr(mod, cls_name)
    # Inspect constructor to decide how to instantiate
    try:
        init_sig = inspect.signature(cls.__init__)
        params = list(init_sig.parameters.values())[1:]  # skip self
        kwargs = {}
        requires_name = any(p.name == "name" and p.default is p.empty for p in params)
        if requires_name:
            kwargs["name"] = cls.__name__
        return cls(**kwargs)
    except Exception:
        # Fallbacks
        try:
            return cls()  # type: ignore[misc]
        except Exception:
            return cls(cls.__name__)  # type: ignore[misc]
