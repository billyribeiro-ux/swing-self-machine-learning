from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from swing_rsi.application.datasets import normalize_ticker
from swing_rsi.config import load_yaml


@dataclass(frozen=True)
class UniverseSymbol:
    symbol: str
    enabled: bool = True
    role: str = "stock"
    sector: str | None = None
    sector_proxy: str | None = None
    benchmark: bool = False
    relationship_group: str | None = None
    metadata: dict[str, str] | None = None


@dataclass(frozen=True)
class UniverseConfig:
    name: str
    provider: str
    default_start: str
    symbols: tuple[UniverseSymbol, ...]
    relationships: dict[str, tuple[str, ...]]
    source_path: Path | None = None

    @property
    def enabled_symbols(self) -> tuple[str, ...]:
        return tuple(symbol.symbol for symbol in self.symbols if symbol.enabled)

    @property
    def benchmark_symbols(self) -> tuple[str, ...]:
        return tuple(
            symbol.symbol for symbol in self.symbols if symbol.enabled and symbol.benchmark
        )

    @property
    def snapshot_id(self) -> str:
        payload = json.dumps(
            {
                "name": self.name,
                "provider": self.provider,
                "default_start": self.default_start,
                "symbols": [asdict(symbol) for symbol in self.symbols],
                "relationships": self.relationships,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _symbol_from_mapping(raw: dict[str, Any]) -> UniverseSymbol:
    symbol = normalize_ticker(str(raw.get("symbol", "")))
    metadata = {
        str(key): str(value)
        for key, value in raw.items()
        if key
        not in {
            "symbol",
            "enabled",
            "role",
            "sector",
            "sector_proxy",
            "benchmark",
            "relationship_group",
        }
    }
    sector_proxy = raw.get("sector_proxy")
    return UniverseSymbol(
        symbol=symbol,
        enabled=bool(raw.get("enabled", True)),
        role=str(raw.get("role", "stock")),
        sector=str(raw["sector"]) if raw.get("sector") is not None else None,
        sector_proxy=normalize_ticker(str(sector_proxy)) if sector_proxy else None,
        benchmark=bool(raw.get("benchmark", False)),
        relationship_group=str(raw["relationship_group"])
        if raw.get("relationship_group") is not None
        else None,
        metadata=metadata or None,
    )


def _load_csv_symbols(path: Path) -> list[UniverseSymbol]:
    rows: list[UniverseSymbol] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(_symbol_from_mapping(dict(raw)))
    return rows


def _relationships(raw: object) -> dict[str, tuple[str, ...]]:
    relationships: dict[str, tuple[str, ...]] = {}
    if not isinstance(raw, list):
        return relationships
    for item in raw:
        if not isinstance(item, dict):
            continue
        source = normalize_ticker(str(item.get("source", "")))
        related = item.get("related", [])
        if not isinstance(related, list):
            continue
        relationships[source] = tuple(normalize_ticker(str(value)) for value in related)
    return relationships


def load_universe_config(path: str | Path) -> UniverseConfig:
    source = Path(path)
    config = load_yaml(source)
    raw_symbols = config.get("symbols", [])
    if not isinstance(raw_symbols, list):
        raise ValueError("Universe config must contain a symbols list")

    symbols: list[UniverseSymbol] = []
    for raw in raw_symbols:
        if not isinstance(raw, dict):
            raise ValueError("Every configured symbol must be a mapping")
        symbols.append(_symbol_from_mapping(raw))

    for import_path in config.get("csv_imports", []) or []:
        csv_path = Path(import_path)
        if not csv_path.is_absolute():
            csv_path = source.parent / csv_path
        symbols.extend(_load_csv_symbols(csv_path))

    by_symbol: dict[str, UniverseSymbol] = {}
    for symbol in symbols:
        by_symbol[symbol.symbol] = symbol
    if not by_symbol:
        raise ValueError("Universe config must contain at least one symbol")

    return UniverseConfig(
        name=str(config.get("name", source.stem)),
        provider=str(config.get("provider", "fmp")).lower(),
        default_start=str(config.get("default_start", "2016-01-01")),
        symbols=tuple(sorted(by_symbol.values(), key=lambda value: value.symbol)),
        relationships=_relationships(config.get("relationships")),
        source_path=source,
    )


def symbol_metadata(universe: UniverseConfig) -> dict[str, UniverseSymbol]:
    return {symbol.symbol: symbol for symbol in universe.symbols}


def universe_to_frame_rows(universe: UniverseConfig) -> list[dict[str, object]]:
    return [asdict(symbol) | {"snapshot_id": universe.snapshot_id} for symbol in universe.symbols]
