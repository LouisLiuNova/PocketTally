"""HTTP Pydantic 模型的公共配置和标量约束。"""

from datetime import UTC, datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    field_serializer,
    model_validator,
)


def to_camel(value: str) -> str:
    """将 Python 的 snake_case 字段名转换为 HTTP 使用的 camelCase。

    Args:
        value: Python 风格的字段名。

    Returns:
        camelCase 格式的字段名。
    """

    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


HexColor = Annotated[
    str,
    StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"),
]
"""契约规定的六位十六进制颜色值。"""


class ContractModel(BaseModel):
    """所有 HTTP 模型共用的 Pydantic 配置。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @field_serializer(
        "created_at",
        "updated_at",
        "occurred_at",
        "voided_at",
        when_used="json",
        check_fields=False,
    )
    def serialize_datetime(self, value: object) -> object:
        """将 HTTP 响应中的时间统一序列化为带 ``Z`` 的 UTC 字符串。

        Pydantic 2 的字段序列化器只在 JSON 模式生效，因此普通
        ``model_dump()`` 仍保留 datetime 对象，HTTP
        输出和嵌套响应则统一使用当前契约要求的 UTC 表示。
        """

        if not isinstance(value, datetime):
            return value
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


class UpdateModel(ContractModel):
    """要求至少包含一个属性的部分更新模型基类。"""

    model_config = ConfigDict(json_schema_extra={"minProperties": 1})

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        """拒绝空的 PATCH 请求，同时保留显式 null 的语义。

        Returns:
            当前已校验的模型。

        Raises:
            ValueError: 请求体没有提供任何属性时抛出。
        """

        if not self.model_fields_set:
            raise ValueError("至少需要提供一个可更新属性")
        return self


__all__ = ("ContractModel", "HexColor", "UpdateModel", "to_camel")
