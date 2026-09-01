"""HTTP Pydantic 模型与 SQLModel ORM 对接测试。"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.models import (
    Account,
    Category,
    Tag,
    Transaction,
    TransactionTag,
    TransactionType,
)
from app.schemas import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    TagRead,
    TagUpdate,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)


def test_create_models_use_camel_case_and_reject_unknown_fields() -> None:
    """验证请求模型的别名、默认值、去空白和未知字段策略。"""

    account = AccountCreate.model_validate(
        {"type": "  现金 ", "name": " 钱包 ", "cardNumber": None}
    )

    assert account.type == "现金"
    assert account.name == "钱包"
    assert account.amount == 0.0
    assert set(account.model_dump(by_alias=True)) == {
        "type",
        "name",
        "cardNumber",
        "description",
        "amount",
    }

    with pytest.raises(ValidationError):
        AccountCreate.model_validate(
            {"type": "现金", "name": "钱包", "serverOwned": "no"}
        )


def test_update_models_require_a_field_and_preserve_explicit_null() -> None:
    """验证 PATCH 的空请求拒绝以及显式 null 清除语义。"""

    with pytest.raises(ValidationError, match="至少需要提供一个"):
        AccountUpdate.model_validate({})

    update = AccountUpdate.model_validate({"description": None})
    assert update.to_orm_kwargs() == {"description": None}

    category_update = CategoryUpdate.model_validate({"parentCategoryId": None})
    assert category_update.to_orm_kwargs() == {"parent_category_id": None}

    tag_update = TagUpdate.model_validate({"color": "#ABCDEF"})
    assert tag_update.to_orm_kwargs() == {"color": "#ABCDEF"}

    transaction_update = TransactionUpdate.model_validate(
        {"destinationAccountId": None, "tagIds": []}
    )
    assert transaction_update.to_orm_kwargs() == {
        "dest_account_id": None,
    }
    assert transaction_update.tag_ids_for_relation() == []

    with pytest.raises(ValidationError):
        AccountUpdate.model_validate({"name": None})
    with pytest.raises(ValidationError):
        AccountUpdate.model_validate({"amount": 100})
    with pytest.raises(ValidationError):
        TransactionUpdate.model_validate({"amount": None})


def test_generated_json_schema_keeps_contract_object_and_array_constraints() -> None:
    """验证 JSON Schema 暴露契约要求的 PATCH 和数组约束。"""

    account_update_schema = AccountUpdate.model_json_schema()
    transaction_create_schema = TransactionCreate.model_json_schema()
    transaction_read_schema = TransactionRead.model_json_schema()

    assert account_update_schema["minProperties"] == 1
    assert account_update_schema["additionalProperties"] is False
    assert account_update_schema["properties"]["type"]["type"] == "string"
    assert "anyOf" in account_update_schema["properties"]["description"]
    assert transaction_create_schema["properties"]["tagIds"]["uniqueItems"] is True
    assert transaction_create_schema["properties"]["amount"]["exclusiveMinimum"] == 0
    assert transaction_create_schema["$defs"]["TransactionType"]["enum"] == [
        "income",
        "expense",
        "transfer",
        "balance_adjustment",
    ]
    assert transaction_read_schema["properties"]["tags"]["uniqueItems"] is True
    assert "occurredAt" in transaction_create_schema["required"]
    assert "occurredAt" in transaction_read_schema["required"]


def test_write_models_convert_relationship_ids_to_orm_columns() -> None:
    """验证写入模型的 UUID 和关系字段转换为数据库格式。"""

    source_id = uuid4()
    category_id = uuid4()
    tag_id = uuid4()
    occurred_at = datetime.now(UTC)
    transaction = TransactionCreate.model_validate(
        {
            "type": "expense",
            "sourceAccountId": str(source_id),
            "amount": 12.5,
            "categoryId": str(category_id),
            "tagIds": [str(tag_id)],
            "occurredAt": occurred_at.isoformat(),
        }
    )

    assert transaction.to_orm_kwargs() == {
        "type": "expense",
        "src_account_id": str(source_id),
        "dest_account_id": None,
        "amount": 12.5,
        "description": None,
        "category": str(category_id),
        "is_refund": False,
        "related_transaction_id": None,
        "occurred_at": occurred_at,
    }
    assert transaction.tag_ids_for_relation() == [str(tag_id)]

    category = CategoryCreate.model_validate({"name": "餐饮"})
    assert category.to_orm_kwargs()["parent_category_id"] is None

    with pytest.raises(ValidationError):
        TransactionCreate.model_validate(
            {
                "type": "expense",
                "sourceAccountId": str(source_id),
                "amount": 1,
                "categoryId": str(category_id),
                "tagIds": [str(tag_id), str(tag_id)],
                "occurredAt": occurred_at.isoformat(),
            }
        )


def test_transaction_type_and_amount_constraints() -> None:
    """验证交易类型枚举和有限正金额约束。"""

    payload = {
        "type": TransactionType.BALANCE_ADJUSTMENT,
        "sourceAccountId": str(uuid4()),
        "amount": 1,
        "categoryId": str(uuid4()),
        "occurredAt": datetime.now(UTC).isoformat(),
    }

    adjustment = TransactionCreate.model_validate(payload)
    assert adjustment.type is TransactionType.BALANCE_ADJUSTMENT
    assert Transaction.__table__.c.type.type.enums == [
        "income",
        "expense",
        "transfer",
        "balance_adjustment",
    ]

    with pytest.raises(ValidationError):
        TransactionCreate.model_validate({**payload, "type": "未知类型"})
    with pytest.raises(ValidationError, match="有限正数"):
        TransactionCreate.model_validate({**payload, "amount": 0})
    with pytest.raises(ValidationError, match="有限正数"):
        TransactionCreate.model_validate({**payload, "amount": -1})
    with pytest.raises(ValidationError, match="有限正数"):
        TransactionCreate.model_validate({**payload, "amount": float("inf")})
    with pytest.raises(ValidationError, match="有限正数"):
        TransactionUpdate.model_validate({"amount": 0})


def test_read_models_map_orm_fields_and_nested_relationships() -> None:
    """验证读取模型可从 ORM 读取，并将关系限制为契约摘要。"""

    now = datetime.now(UTC)
    account = Account(
        id=str(uuid4()),
        type="现金",
        name="钱包",
        card_number=None,
        description=None,
        amount=100.0,
        created_at=now,
        updated_at=now,
    )
    category = Category(
        id=str(uuid4()),
        name="餐饮",
        description=None,
        icon_color="#ff0000",
        icon_name="default_icon",
        created_at=now,
        updated_at=now,
    )
    tag = Tag(
        id=str(uuid4()),
        name="外卖",
        description=None,
        color="#00ff00",
        created_at=now,
        updated_at=now,
    )
    transaction = Transaction(
        id=str(uuid4()),
        type="expense",
        src_account_id=account.id,
        dest_account_id=None,
        amount=20.0,
        description="午餐",
        category=category.id,
        is_refund=False,
        related_transaction_id=None,
        occurred_at=now,
        created_at=now,
        updated_at=now,
    )
    transaction.source_account = account
    transaction.destination_account = None
    transaction.category_record = category
    transaction.related_transaction = None
    transaction.tags = [tag]

    account_response = AccountRead.from_orm_model(account)
    category_response = CategoryRead.from_orm_model(category)
    tag_response = TagRead.from_orm_model(tag)
    transaction_response = TransactionRead.from_orm_model(transaction)

    assert isinstance(account_response.id, UUID)
    assert account_response.model_dump(mode="json", by_alias=True)["createdAt"]
    assert category_response.parent_category is None
    assert tag_response.color == "#00ff00"
    assert transaction_response.category.id == UUID(category.id)
    assert transaction_response.tags[0].id == UUID(tag.id)
    assert transaction_response.occurred_at == now
    assert transaction_response.model_dump(mode="json", by_alias=True)[
        "sourceAccount"
    ] == {
        "id": account.id,
        "type": "现金",
        "name": "钱包",
    }


def test_transaction_tag_link_model_uses_composite_identity() -> None:
    """验证标签关联模型以交易和标签 ID 共同标识一条关联。"""

    link = TransactionTag(transaction_id=str(uuid4()), tag_id=str(uuid4()))

    assert link.transaction_id
    assert link.tag_id
