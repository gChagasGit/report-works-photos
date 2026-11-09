"""Conversão de erros do Pydantic em mensagens em português."""

from pydantic import ValidationError

from report_works.i18n import pt_br


def _reason(error_type: str, message: str, context: dict[str, object] | None) -> str:
    ctx = context or {}
    match error_type:
        case "missing":
            return pt_br.REASON_MISSING
        case "string_pattern_mismatch":
            return pt_br.REASON_PATTERN
        case "too_short" | "string_too_short":
            return pt_br.REASON_TOO_SHORT
        case "greater_than_equal":
            return pt_br.REASON_GREATER_OR_EQUAL.format(limit=ctx.get("ge"))
        case "greater_than":
            return pt_br.REASON_GREATER_THAN.format(limit=ctx.get("gt"))
        case "extra_forbidden":
            return pt_br.REASON_UNKNOWN_FIELD
        case "value_error":
            return str(ctx.get("error", message)).removeprefix("Value error, ")
        case "int_parsing" | "float_parsing" | "bool_parsing" | "string_type" | "list_type":
            return pt_br.REASON_TYPE
        case _:
            return pt_br.REASON_INVALID


def describe_validation_errors(error: ValidationError) -> list[str]:
    """Uma mensagem em português por problema, no formato `campo: motivo`."""
    messages: list[str] = []
    for item in error.errors():
        field = ".".join(str(part) for part in item["loc"])
        reason = _reason(item["type"], item["msg"], item.get("ctx"))
        messages.append(pt_br.FIELD_ERROR.format(field=field, reason=reason) if field else reason)
    return messages
