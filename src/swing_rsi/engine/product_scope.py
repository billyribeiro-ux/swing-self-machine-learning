from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import pandas as pd

from swing_rsi.engine.gates import configuration_hash
from swing_rsi.engine.universe import UniverseConfig, symbol_metadata

PRODUCT_CLASS_SCHEMA_VERSION = "product_class_specialist_v1"

ProductClassScope = Literal["POOLED", "ORDINARY", "LEVERAGED_INVERSE"]

PRODUCT_CLASS_SCOPE_POOLED: ProductClassScope = "POOLED"
PRODUCT_CLASS_SCOPE_ORDINARY: ProductClassScope = "ORDINARY"
PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE: ProductClassScope = "LEVERAGED_INVERSE"
PRODUCT_CLASS_SCOPES: tuple[ProductClassScope, ...] = (
    PRODUCT_CLASS_SCOPE_POOLED,
    PRODUCT_CLASS_SCOPE_ORDINARY,
    PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE,
)

PRODUCT_CLASS_SCOPE_MISMATCH_REASON = "product_class_scope_mismatch"

ORDINARY_PRODUCT_ROLES = (
    "stock",
    "broad_market_etf",
    "sector_etf",
    "ordinary_etf",
)
LEVERAGED_INVERSE_PRODUCT_ROLES = (
    "inverse_etf",
    "leveraged_inverse_etf",
    "leveraged_long_etf",
)


def canonical_role_scope_mapping() -> dict[str, ProductClassScope]:
    return {
        **{role: PRODUCT_CLASS_SCOPE_ORDINARY for role in ORDINARY_PRODUCT_ROLES},
        **{role: PRODUCT_CLASS_SCOPE_LEVERAGED_INVERSE for role in LEVERAGED_INVERSE_PRODUCT_ROLES},
    }


@dataclass(frozen=True)
class ProductClassScopeDefinition:
    schema_version: str
    scope: ProductClassScope
    eligible_roles: tuple[str, ...]
    eligible_symbols: tuple[str, ...]
    roles_by_symbol: dict[str, str]
    role_scope_mapping: dict[str, ProductClassScope]
    role_scope_mapping_hash: str
    scope_configuration_hash: str
    universe_scope_hash: str

    def to_jsonable(self) -> dict[str, object]:
        return asdict(self)


def _normalize_role(role: object) -> str:
    return str(role or "").strip().lower()


def normalize_product_class_scope(scope: object) -> ProductClassScope:
    normalized = str(scope or "").strip().upper()
    if normalized not in PRODUCT_CLASS_SCOPES:
        raise ValueError(f"Unknown product-class scope: {scope}")
    return normalized


def role_scope_mapping_hash(mapping: dict[str, ProductClassScope] | None = None) -> str:
    return configuration_hash(
        {
            "schema_version": PRODUCT_CLASS_SCHEMA_VERSION,
            "role_scope_mapping": mapping or canonical_role_scope_mapping(),
        }
    )


def validate_role_scope_mapping(mapping: dict[str, ProductClassScope] | None = None) -> None:
    role_mapping = mapping or canonical_role_scope_mapping()
    seen: dict[str, ProductClassScope] = {}
    for raw_role, raw_scope in role_mapping.items():
        role = _normalize_role(raw_role)
        scope = normalize_product_class_scope(raw_scope)
        if scope == PRODUCT_CLASS_SCOPE_POOLED:
            raise ValueError("POOLED is a derived scope and cannot be assigned to a role")
        if role in seen and seen[role] != scope:
            raise ValueError(f"Ambiguous product-class role mapping: {role}")
        seen[role] = scope


def product_class_scope_for_role(
    role: object,
    *,
    mapping: dict[str, ProductClassScope] | None = None,
) -> ProductClassScope:
    role_mapping = mapping or canonical_role_scope_mapping()
    validate_role_scope_mapping(role_mapping)
    normalized = _normalize_role(role)
    if normalized not in role_mapping:
        raise ValueError(f"Unknown product-class universe role: {role}")
    return role_mapping[normalized]


def validate_universe_product_class_roles(
    universe: UniverseConfig,
    *,
    mapping: dict[str, ProductClassScope] | None = None,
) -> None:
    role_mapping = mapping or canonical_role_scope_mapping()
    validate_role_scope_mapping(role_mapping)
    unknown = sorted(
        {
            _normalize_role(symbol.role)
            for symbol in universe.symbols
            if _normalize_role(symbol.role) not in role_mapping
        }
    )
    if unknown:
        raise ValueError(
            "Unknown product-class universe role(s): " + ", ".join(role for role in unknown if role)
        )


def build_product_class_scope_definition(
    universe: UniverseConfig,
    scope: ProductClassScope,
    *,
    mapping: dict[str, ProductClassScope] | None = None,
) -> ProductClassScopeDefinition:
    scope = normalize_product_class_scope(scope)
    role_mapping = mapping or canonical_role_scope_mapping()
    validate_universe_product_class_roles(universe, mapping=role_mapping)
    enabled = tuple(symbol for symbol in universe.symbols if symbol.enabled)
    roles_by_symbol = {symbol.symbol: _normalize_role(symbol.role) for symbol in enabled}
    if scope == PRODUCT_CLASS_SCOPE_POOLED:
        eligible_roles = tuple(sorted(set(roles_by_symbol.values())))
        eligible_symbols = tuple(sorted(roles_by_symbol))
    else:
        eligible_roles = tuple(
            sorted(role for role, mapped_scope in role_mapping.items() if mapped_scope == scope)
        )
        eligible_symbols = tuple(
            sorted(
                symbol.symbol
                for symbol in enabled
                if role_mapping[_normalize_role(symbol.role)] == scope
            )
        )
    mapping_hash = role_scope_mapping_hash(role_mapping)
    scope_config: dict[str, object] = {
        "schema_version": PRODUCT_CLASS_SCHEMA_VERSION,
        "scope": scope,
        "eligible_roles": eligible_roles,
        "role_scope_mapping_hash": mapping_hash,
    }
    scope_configuration_hash = configuration_hash(scope_config)
    universe_scope_hash = configuration_hash(
        {
            **scope_config,
            "universe_snapshot_id": universe.snapshot_id,
            "eligible_symbols": eligible_symbols,
            "roles_by_symbol": roles_by_symbol,
        }
    )
    return ProductClassScopeDefinition(
        schema_version=PRODUCT_CLASS_SCHEMA_VERSION,
        scope=scope,
        eligible_roles=eligible_roles,
        eligible_symbols=eligible_symbols,
        roles_by_symbol=roles_by_symbol,
        role_scope_mapping=role_mapping,
        role_scope_mapping_hash=mapping_hash,
        scope_configuration_hash=scope_configuration_hash,
        universe_scope_hash=universe_scope_hash,
    )


def build_product_class_scope_definitions(
    universe: UniverseConfig,
    *,
    scopes: tuple[ProductClassScope, ...] = PRODUCT_CLASS_SCOPES,
    mapping: dict[str, ProductClassScope] | None = None,
) -> dict[ProductClassScope, ProductClassScopeDefinition]:
    normalized_scopes = tuple(normalize_product_class_scope(scope) for scope in scopes)
    return {
        scope: build_product_class_scope_definition(universe, scope, mapping=mapping)
        for scope in normalized_scopes
    }


def product_class_scope_for_symbol(
    universe: UniverseConfig,
    symbol: object,
    *,
    mapping: dict[str, ProductClassScope] | None = None,
) -> ProductClassScope:
    metadata = symbol_metadata(universe)
    ticker = str(symbol or "").strip().upper()
    if ticker not in metadata:
        raise ValueError(f"Symbol is not present in the governed universe: {symbol}")
    return product_class_scope_for_role(metadata[ticker].role, mapping=mapping)


def product_scope_definition_from_frame(
    frame: pd.DataFrame,
    scope: ProductClassScope = PRODUCT_CLASS_SCOPE_POOLED,
    *,
    mapping: dict[str, ProductClassScope] | None = None,
) -> ProductClassScopeDefinition:
    scope = normalize_product_class_scope(scope)
    if scope != PRODUCT_CLASS_SCOPE_POOLED:
        raise ValueError("Specialist product-class scopes require governed universe metadata")
    role_mapping = mapping or canonical_role_scope_mapping()
    validate_role_scope_mapping(role_mapping)
    symbols = tuple(
        sorted(str(symbol) for symbol in frame.get("symbol", pd.Series()).dropna().unique())
    )
    roles_by_symbol: dict[str, str] = {}
    if "role" in frame.columns and "symbol" in frame.columns:
        role_rows = (
            frame[["symbol", "role"]]
            .dropna(subset=["symbol"])
            .drop_duplicates(subset=["symbol"], keep="last")
        )
        roles_by_symbol = {
            str(row.symbol): _normalize_role(row.role) for row in role_rows.itertuples()
        }
        for role in roles_by_symbol.values():
            product_class_scope_for_role(role, mapping=role_mapping)
    else:
        roles_by_symbol = {symbol: "unknown" for symbol in symbols}
    eligible_roles = tuple(sorted(set(roles_by_symbol.values())))
    mapping_hash = role_scope_mapping_hash(role_mapping)
    scope_config: dict[str, object] = {
        "schema_version": PRODUCT_CLASS_SCHEMA_VERSION,
        "scope": scope,
        "eligible_roles": eligible_roles,
        "role_scope_mapping_hash": mapping_hash,
        "fallback_source": "frame",
    }
    return ProductClassScopeDefinition(
        schema_version=PRODUCT_CLASS_SCHEMA_VERSION,
        scope=scope,
        eligible_roles=eligible_roles,
        eligible_symbols=symbols,
        roles_by_symbol=roles_by_symbol,
        role_scope_mapping=role_mapping,
        role_scope_mapping_hash=mapping_hash,
        scope_configuration_hash=configuration_hash(scope_config),
        universe_scope_hash=configuration_hash(
            {
                **scope_config,
                "eligible_symbols": symbols,
                "roles_by_symbol": roles_by_symbol,
            }
        ),
    )


def filter_frame_for_product_class_scope(
    frame: pd.DataFrame,
    definition: ProductClassScopeDefinition,
) -> pd.DataFrame:
    if definition.scope == PRODUCT_CLASS_SCOPE_POOLED:
        return frame.copy()
    symbols = set(definition.eligible_symbols)
    return frame.loc[frame["symbol"].astype(str).isin(symbols)].copy()


def row_product_class_scope(row: dict[str, object]) -> ProductClassScope | None:
    role = row.get("role")
    if role in {None, ""}:
        return None
    return product_class_scope_for_role(role)


def scope_allows_symbol(
    model_scope: object,
    row_scope: object | None,
) -> bool:
    scope = normalize_product_class_scope(model_scope or PRODUCT_CLASS_SCOPE_POOLED)
    if scope == PRODUCT_CLASS_SCOPE_POOLED:
        return True
    if row_scope is None:
        return False
    return normalize_product_class_scope(row_scope) == scope
