"""HTTP Pydantic 模型的公共配置和标量约束。"""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator


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
