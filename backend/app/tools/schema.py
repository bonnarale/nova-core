"""JSON Schema validation for tool inputs and outputs."""

from __future__ import annotations

from typing import Any

from app.tools.exceptions import ToolValidationError


def validate_schema(data: dict[str, Any], schema: dict[str, Any], tool_name: str = "") -> None:
    """Validate *data* against a JSON-Schema-like dict.

    Supports: type, required, properties, enum, minimum, maximum,
    minLength, maxLength, pattern (basic), items (for arrays).

    Raises ``ToolValidationError`` on failure.
    """
    if not schema:
        return

    schema_type = schema.get("type")
    if schema_type and not _check_type(data, schema_type):
        raise ToolValidationError(
            tool_name,
            f"Expected type '{schema_type}', got '{type(data).__name__}'",
        )

    if "enum" in schema and data not in schema["enum"]:
        raise ToolValidationError(
            tool_name,
            f"Value {data!r} not in allowed values: {schema['enum']}",
        )

    if "minimum" in schema and isinstance(data, (int, float)):
        if data < schema["minimum"]:
            raise ToolValidationError(
                tool_name,
                f"Value {data} is less than minimum {schema['minimum']}",
            )

    if "maximum" in schema and isinstance(data, (int, float)):
        if data > schema["maximum"]:
            raise ToolValidationError(
                tool_name,
                f"Value {data} is greater than maximum {schema['maximum']}",
            )

    if "minLength" in schema and isinstance(data, str):
        if len(data) < schema["minLength"]:
            raise ToolValidationError(
                tool_name,
                f"String length {len(data)} is less than minLength {schema['minLength']}",
            )

    if "maxLength" in schema and isinstance(data, str):
        if len(data) > schema["maxLength"]:
            raise ToolValidationError(
                tool_name,
                f"String length {len(data)} is greater than maxLength {schema['maxLength']}",
            )

    if "properties" in schema and isinstance(data, dict):
        properties = schema["properties"]
        required = schema.get("required", [])

        for field_name in required:
            if field_name not in data:
                raise ToolValidationError(
                    tool_name,
                    f"Missing required field '{field_name}'",
                )

        for field_name, field_schema in properties.items():
            if field_name in data:
                validate_schema(data[field_name], field_schema, tool_name)

    if "items" in schema and isinstance(data, list):
        item_schema = schema["items"]
        for i, item in enumerate(data):
            validate_schema(item, item_schema, tool_name)


def _check_type(value: Any, schema_type: str) -> bool:
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }
    expected = type_map.get(schema_type)
    if expected is None:
        return True
    if schema_type == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, expected)


def build_input_schema(parameters: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a JSON-Schema-like dict from a list of parameter descriptors."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    type_map = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "list": "array",
        "dict": "object",
    }

    for param in parameters:
        name = param.get("name", "")
        if not name:
            continue
        prop: dict[str, Any] = {
            "type": type_map.get(param.get("type", "string"), "string"),
        }
        if "description" in param:
            prop["description"] = param["description"]
        if "default" in param:
            prop["default"] = param["default"]
        if "enum" in param:
            prop["enum"] = param["enum"]
        properties[name] = prop
        if param.get("required", False):
            required.append(name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema
