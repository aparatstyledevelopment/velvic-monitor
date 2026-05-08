"""Tool dispatcher: bridges LLM tool calls to Engine tool registry.

The chat orchestrator builds `ToolSpec` JSON-Schemas from the registry,
hands them to the provider, then dispatches each `ToolCall` the model
emits back through the registry's `@engine_tool`-wrapped callable.

Argument coercion uses Pydantic v2 to translate the JSON dict the LLM
emits (where dates are strings, decimals are floats) into the typed
kwargs the engine tool expects.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError, create_model
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.providers.base import ToolCall, ToolSpec
from app.engine import registry as engine_registry
from app.engine.envelope import EngineResult
from app.engine.registry import EngineToolSpec


class UnknownToolError(Exception):
    """Raised when the LLM asks for a tool that isn't registered."""


class ToolArgumentError(Exception):
    """Raised when tool arguments fail Pydantic validation."""


@dataclass(frozen=True)
class ToolDispatchResult:
    tool_call_id: str
    tool_name: str
    engine_call_id: str
    envelope_json: str
    source_refs: list[dict[str, Any]]


def tool_specs_for_chat(modules: list[str] | None = None) -> list[ToolSpec]:
    """Catalog of LLM-callable tools as ToolSpec(name, description, input_schema).

    Defaults to the drivers + shared modules (everything the chat orchestrator
    needs for the v1 module). Pass an explicit list to narrow.
    """
    specs = (
        engine_registry.specs_for_modules(modules)
        if modules is not None
        else engine_registry.all_specs()
    )
    return [
        ToolSpec(
            name=spec.name,
            description=spec.description,
            input_schema=_build_input_schema(spec),
        )
        for spec in specs
    ]


async def dispatch(call: ToolCall, *, session: AsyncSession) -> ToolDispatchResult:
    """Route an LLM-emitted ToolCall into the engine registry and return result."""
    try:
        spec = engine_registry.get(call.name)
    except KeyError as e:
        raise UnknownToolError(str(e)) from e

    try:
        kwargs = _coerce_arguments(spec, call.arguments)
    except ValidationError as e:
        raise ToolArgumentError(_format_validation_error(call.name, e)) from e

    result: EngineResult[Any] = await spec.callable(session=session, **kwargs)
    envelope = {
        "engine_call_id": result.engine_call_id,
        "data": result.data.model_dump(mode="json"),
        "sources": [s.model_dump(mode="json") for s in result.sources],
    }
    return ToolDispatchResult(
        tool_call_id=call.id,
        tool_name=spec.name,
        engine_call_id=result.engine_call_id,
        envelope_json=json.dumps(envelope, default=_jsonable_default),
        source_refs=envelope["sources"],
    )


def _build_input_schema(spec: EngineToolSpec) -> dict[str, Any]:
    if spec.params_model is not None:
        schema: dict[str, Any] = spec.params_model.model_json_schema()
        return _strip_titles(schema)
    model = _model_from_signature(spec)
    return _strip_titles(model.model_json_schema())


def _coerce_arguments(
    spec: EngineToolSpec, arguments: dict[str, Any]
) -> dict[str, Any]:
    if spec.params_model is not None:
        validated: BaseModel = spec.params_model.model_validate(arguments)
        return validated.model_dump()
    model = _model_from_signature(spec)
    instance = model.model_validate(arguments)
    return instance.model_dump()


def _model_from_signature(spec: EngineToolSpec) -> type[BaseModel]:
    """Build a Pydantic model from the tool's original signature (sans session)."""
    fields: dict[str, Any] = {}
    for name, param in spec.signature.parameters.items():
        if name == "session":
            continue
        annotation = spec.type_hints.get(name, param.annotation)
        if annotation is inspect.Parameter.empty:
            annotation = Any
        default = param.default if param.default is not inspect.Parameter.empty else ...
        fields[name] = (annotation, default)
    return create_model(f"{spec.name}_Args", **fields)


def _strip_titles(schema: dict[str, Any]) -> dict[str, Any]:
    """Drop Pydantic-injected `title` fields; LLMs ignore them and they bloat."""
    if isinstance(schema, dict):
        return {
            k: _strip_titles(v)
            for k, v in schema.items()
            if not (k == "title" and isinstance(v, str))
        }
    return schema


def _format_validation_error(tool_name: str, e: ValidationError) -> str:
    msgs = [
        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()
    ]
    return f"invalid arguments for {tool_name}: " + "; ".join(msgs)


def _jsonable_default(o: Any) -> Any:
    if hasattr(o, "isoformat"):
        return o.isoformat()
    if isinstance(o, BaseModel):
        return o.model_dump(mode="json")
    return str(o)
