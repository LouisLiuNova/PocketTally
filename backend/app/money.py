"""PocketTally 的 CNY 定点金额转换工具。"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated

from pydantic import PlainSerializer, WithJsonSchema

DEFAULT_CURRENCY = "CNY"
"""系统固定使用的币种；该值不作为账户或交易字段暴露。"""

MONEY_QUANTUM = Decimal("0.01")
"""CNY 元转换为分时使用的精度。"""

MoneyAmount = Annotated[
    Decimal,
    PlainSerializer(float, return_type=float, when_used="json"),
    WithJsonSchema(
        {
            "type": "number",
            "description": "CNY 金额；服务端接收后按 ROUND_HALF_UP 舍入到分。",
            "examples": [12.34],
        }
    ),
]
"""HTTP 层使用的金额类型，内部转换为 Decimal 后再处理。"""


def parse_amount(value: object) -> Decimal:
    """解析并按 CNY 两位小数使用 ``ROUND_HALF_UP`` 舍入金额。

    Args:
        value: HTTP 或内部调用方提供的金额。JSON 浮点数会先通过其十进制
            文本表现形式转换为 Decimal；整数和 Decimal 也可以安全转换。

    Returns:
        已按分精度舍入的 Decimal 金额。

    Raises:
        TypeError: 金额类型不受支持时抛出。
        ValueError: 金额格式非法或不是有限数时抛出。
    """

    if isinstance(value, bool) or not isinstance(value, (float, int, Decimal)):
        raise TypeError("金额必须使用数字")
    try:
        # str(float) 保留 JSON 解码后的十进制短表示，避免 Decimal 直接接收
        # float 时把二进制尾数带入舍入计算。
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("金额必须是有效数字") from error
    if not amount.is_finite():
        raise ValueError("金额必须是有限十进制数")
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def amount_to_minor(value: Decimal) -> int:
    """将已舍入的 CNY 元金额转换为整数分。

    Args:
        value: 已按 ``MONEY_QUANTUM`` 舍入的 Decimal 金额。

    Returns:
        CNY 最小单位整数。
    """

    return int(value * 100)


def minor_to_amount(value: int) -> Decimal:
    """将整数分转换为两位小数的 CNY 元金额。

    Args:
        value: CNY 最小单位整数。

    Returns:
        两位小数的 Decimal 金额。
    """

    return (Decimal(value) / 100).quantize(MONEY_QUANTUM)


__all__ = (
    "DEFAULT_CURRENCY",
    "MONEY_QUANTUM",
    "MoneyAmount",
    "amount_to_minor",
    "minor_to_amount",
    "parse_amount",
)
