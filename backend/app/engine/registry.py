"""Engine tool registry + @engine_tool decorator.

Tools are async functions that take a session and parameters, and return
an EngineResult. The decorator wraps the underlying function with:
- content-addressed id derivation
- ledger cache lookup (return cached envelope if present)
- timing and error capture
- ledger persistence on success or error

The chat orchestrator reads the catalog by `module` filter and exposes
each tool's signature to the LLM in its provider-native tool-call schema.
"""

from __future__ import annotations

import inspect
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ParamSpec, TypeVar, get_type_hints

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import logger
from app.engine import ledger as ledger_mod
from app.engine.envelope import EngineResult, hash_call_id

P = ParamSpec("P")
R = TypeVar("R", bound=BaseModel)


CostClass = str  # "cheap" | "moderate" | "expensive"


@dataclass(frozen=True)
class EngineToolSpec:
    name: str
    module: str
    description: str
    cost_class: CostClass
    callable: Callable[..., Awaitable[EngineResult[Any]]]
    signature: inspect.Signature
    type_hints: dict[str, Any]
    params_model: type[BaseModel] | None = None
    returns_model: type[BaseModel] | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


_REGISTRY: dict[str, EngineToolSpec] = {}


def engine_tool(
    *,
    name: str,
    module: str,
    description: str,
    cost_class: CostClass = "cheap",
    params_model: type[BaseModel] | None = None,
    returns_model: type[BaseModel] | None = None,
    tags: tuple[str, ...] = (),
) -> Callable[
    [Callable[..., Awaitable[EngineResult[Any]]]],
    Callable[..., Awaitable[EngineResult[Any]]],
]:
    """Register a function as an Engine tool.

    The wrapped function MUST accept a session as its first parameter and
    must return an EngineResult. The wrapper handles ledger lookup + persist.
    """

    def deco(
        fn: Callable[..., Awaitable[EngineResult[Any]]],
    ) -> Callable[..., Awaitable[EngineResult[Any]]]:
        if name in _REGISTRY:
            raise ValueError(f"engine tool already registered: {name}")
        sig = inspect.signature(fn)
        params_excluding_session = [
            p for p in sig.parameters.values() if p.name != "session"
        ]
        # Optional resolution of param types for catalog introspection
        try:
            hints = get_type_hints(fn)
        except Exception:
            hints = {}

        async def wrapper(*args: Any, **kwargs: Any) -> EngineResult[Any]:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            session: AsyncSession = bound.arguments["session"]
            tool_params = {
                k: _to_jsonable(v) for k, v in bound.arguments.items() if k != "session"
            }
            call_id = hash_call_id(tool_name=name, params=tool_params)

            cached = await ledger_mod.get_cached(session, call_id)
            if cached is not None and cached.status == "ok":
                returns = returns_model
                data_obj: Any
                if returns is not None:
                    data_obj = returns.model_validate(cached.result)
                else:
                    data_obj = cached.result
                return EngineResult(
                    engine_call_id=cached.id,
                    tool_name=cached.tool_name,
                    module=cached.module,
                    params=cached.params,
                    data=data_obj,
                    sources=[],
                    computed_at=cached.called_at,
                    engine_version=cached.engine_version,
                    latency_ms=cached.latency_ms,
                )

            t0 = time.perf_counter()
            try:
                result = await fn(*args, **kwargs)
                # Stamp the call id and runtime fields onto the result.
                stamped = result.model_copy(
                    update={
                        "engine_call_id": call_id,
                        "tool_name": name,
                        "module": module,
                        "params": tool_params,
                        "computed_at": datetime.now(UTC),
                        "engine_version": get_settings().engine_version,
                        "latency_ms": int((time.perf_counter() - t0) * 1000),
                    }
                )
                await ledger_mod.persist(session, stamped)
                return stamped
            except Exception as e:
                latency_ms = int((time.perf_counter() - t0) * 1000)
                await ledger_mod.persist_error(
                    session,
                    engine_call_id=call_id,
                    tool_name=name,
                    module=module,
                    params=tool_params,
                    error=str(e),
                    latency_ms=latency_ms,
                )
                logger.exception(
                    "engine_tool_error", tool=name, params=tool_params, error=str(e)
                )
                raise

        spec = EngineToolSpec(
            name=name,
            module=module,
            description=description,
            cost_class=cost_class,
            callable=wrapper,
            signature=sig,
            type_hints=hints,
            params_model=params_model,
            returns_model=returns_model,
            tags=tags,
        )
        _REGISTRY[name] = spec
        wrapper.__engine_tool_spec__ = spec  # type: ignore[attr-defined]
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        # Keep type hints accessible for catalog rendering
        wrapper.__annotations__ = dict(hints)
        # Reference unused locals so type checkers don't strip them
        _ = params_excluding_session
        return wrapper

    return deco


def get(name: str) -> EngineToolSpec:
    if name not in _REGISTRY:
        raise KeyError(f"unknown engine tool: {name}")
    return _REGISTRY[name]


def all_specs() -> list[EngineToolSpec]:
    return sorted(_REGISTRY.values(), key=lambda s: (s.module, s.name))


def specs_for_modules(modules: list[str]) -> list[EngineToolSpec]:
    wanted = set(modules)
    return [s for s in all_specs() if s.module in wanted]


def _to_jsonable(v: Any) -> Any:
    if isinstance(v, BaseModel):
        return v.model_dump(mode="json")
    if isinstance(v, datetime):
        return v.isoformat()
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v
