"""分类树完整性服务与 SQLite 集成测试。"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import Session

from app.categories import (
    CategoryHierarchyError,
    CategoryHierarchyErrorCode,
    create_category,
    update_category,
    validate_category_hierarchy,
)
from app.database import create_database_engine, initialize_database
from app.models import (
    Account,
    AccountType,
    Category,
    CategoryPurpose,
    Transaction,
    TransactionType,
)


def make_engine(database_path: Path):
    """创建分类测试使用的临时运行时数据库。"""

    engine = create_database_engine(database_path)
    initialize_database(engine)
    return engine


def assert_error_code(
    error: pytest.ExceptionInfo[CategoryHierarchyError],
    code: CategoryHierarchyErrorCode,
) -> None:
    """断言分类服务返回预期的稳定业务错误码。"""

    assert error.value.code is code


def test_create_category_rejects_self_parent(tmp_path: Path) -> None:
    """验证创建分类时不能将自身指定为父分类。"""

    engine = make_engine(tmp_path / "self-parent.sqlite3")
    category = Category(
        id="category-1",
        name="餐饮",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id="category-1",
    )
    with Session(engine) as session:
        with pytest.raises(CategoryHierarchyError) as error, session.begin():
            create_category(session, category)

        assert_error_code(error, CategoryHierarchyErrorCode.SELF_PARENT)
        assert session.get(Category, category.id) is None


def test_update_category_rejects_descendant_as_parent(tmp_path: Path) -> None:
    """验证多层分类不能移动到自己的后代节点下。"""

    engine = make_engine(tmp_path / "descendant-parent.sqlite3")
    root = Category(name="生活", purpose=CategoryPurpose.EXPENSE)
    child = Category(
        name="餐饮",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id=root.id,
    )
    grandchild = Category(
        name="工作餐",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id=child.id,
    )
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            create_category(session, root)
            create_category(session, child)
            create_category(session, grandchild)

        with pytest.raises(CategoryHierarchyError) as error, session.begin():
            update_category(session, root, parent_category_id=grandchild.id)

        assert_error_code(error, CategoryHierarchyErrorCode.CYCLE_DETECTED)
        assert root.parent_category_id is None


def test_update_category_rejects_self_parent(tmp_path: Path) -> None:
    """验证已有分类不能在更新时将自身指定为父分类。"""

    engine = make_engine(tmp_path / "update-self-parent.sqlite3")
    category = Category(name="餐饮", purpose=CategoryPurpose.EXPENSE)
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            create_category(session, category)

        with pytest.raises(CategoryHierarchyError) as error, session.begin():
            update_category(session, category, parent_category_id=category.id)

        assert_error_code(error, CategoryHierarchyErrorCode.SELF_PARENT)
        assert category.parent_category_id is None


def test_update_category_allows_legal_cross_level_move(tmp_path: Path) -> None:
    """验证分类可以合法地跨层级移动到另一条分支。"""

    engine = make_engine(tmp_path / "legal-move.sqlite3")
    root = Category(name="生活", purpose=CategoryPurpose.EXPENSE)
    destination = Category(name="固定支出", purpose=CategoryPurpose.EXPENSE)
    child = Category(
        name="餐饮",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id=root.id,
    )
    grandchild = Category(
        name="工作餐",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id=child.id,
    )
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            for category in (root, destination, child, grandchild):
                create_category(session, category)

        with session.begin():
            update_category(
                session,
                child,
                parent_category_id=destination.id,
            )

        assert child.parent_category_id == destination.id
        assert grandchild.parent_category_id == child.id


def test_category_service_rejects_missing_parent(tmp_path: Path) -> None:
    """验证创建和更新统一拒绝不存在的父分类。"""

    engine = make_engine(tmp_path / "missing-parent.sqlite3")
    category = Category(
        name="餐饮",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id="missing",
    )
    with Session(engine, expire_on_commit=False) as session:
        with pytest.raises(CategoryHierarchyError) as create_error, session.begin():
            create_category(session, category)
        assert_error_code(
            create_error,
            CategoryHierarchyErrorCode.PARENT_NOT_FOUND,
        )

        category.parent_category_id = None
        with session.begin():
            create_category(session, category)

        with pytest.raises(CategoryHierarchyError) as update_error, session.begin():
            update_category(session, category, parent_category_id="missing")
        assert_error_code(
            update_error,
            CategoryHierarchyErrorCode.PARENT_NOT_FOUND,
        )
        assert category.parent_category_id is None


def test_existing_dirty_cycle_terminates_with_stable_error(tmp_path: Path) -> None:
    """验证遇到直接 SQL 留下的异常环时校验可以终止并返回业务错误。"""

    engine = make_engine(tmp_path / "dirty-cycle.sqlite3")
    first = Category(name="分类 A", purpose=CategoryPurpose.EXPENSE)
    second = Category(
        name="分类 B",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id=first.id,
    )
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            create_category(session, first)
            create_category(session, second)

        with engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE categories SET parent_category_id = ? WHERE id = ?",
                (second.id, first.id),
            )
        session.expire_all()

        with pytest.raises(CategoryHierarchyError) as error:
            validate_category_hierarchy(
                session,
                category_id="new-category",
                parent_category_id=first.id,
            )

        assert_error_code(error, CategoryHierarchyErrorCode.CYCLE_DETECTED)


def test_category_writes_require_transaction(tmp_path: Path) -> None:
    """验证分类写入不会在缺少事务边界时产生半成品。"""

    engine = make_engine(tmp_path / "transaction-required.sqlite3")
    with Session(engine) as session:
        with pytest.raises(CategoryHierarchyError) as error:
            create_category(
                session,
                Category(name="餐饮", purpose=CategoryPurpose.EXPENSE),
            )

        assert_error_code(
            error,
            CategoryHierarchyErrorCode.TRANSACTION_REQUIRED,
        )


def test_category_parent_and_child_purpose_must_match(tmp_path: Path) -> None:
    """验证创建和移动分类时父子用途必须一致。"""

    engine = make_engine(tmp_path / "purpose-match.sqlite3")
    expense_root = Category(name="支出", purpose=CategoryPurpose.EXPENSE)
    income_root = Category(name="收入", purpose=CategoryPurpose.INCOME)
    child = Category(
        name="工资",
        purpose=CategoryPurpose.INCOME,
        parent_category_id=expense_root.id,
    )
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            create_category(session, expense_root)
            create_category(session, income_root)

        with pytest.raises(CategoryHierarchyError) as create_error, session.begin():
            create_category(session, child)
        assert_error_code(create_error, CategoryHierarchyErrorCode.PURPOSE_MISMATCH)

        child.parent_category_id = income_root.id
        session.rollback()
        with session.begin():
            create_category(session, child)
        with pytest.raises(CategoryHierarchyError) as move_error, session.begin():
            update_category(session, child, parent_category_id=expense_root.id)
        assert_error_code(move_error, CategoryHierarchyErrorCode.PURPOSE_MISMATCH)


def test_category_purpose_is_immutable(tmp_path: Path) -> None:
    """验证分类创建后不能通过服务修改用途。"""

    engine = make_engine(tmp_path / "immutable-purpose.sqlite3")
    category = Category(name="餐饮", purpose=CategoryPurpose.EXPENSE)
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            create_category(session, category)

        with pytest.raises(CategoryHierarchyError) as error, session.begin():
            update_category(session, category, purpose=CategoryPurpose.INCOME)

        assert_error_code(error, CategoryHierarchyErrorCode.PURPOSE_IMMUTABLE)
        assert category.purpose is CategoryPurpose.EXPENSE


def test_backend_moves_subtree_without_confirmation_field(tmp_path: Path) -> None:
    """验证后端不接收前端确认字段，并安全移动整棵子树。"""

    engine = make_engine(tmp_path / "subtree-move.sqlite3")
    source = Category(name="生活", purpose=CategoryPurpose.EXPENSE)
    destination = Category(name="固定支出", purpose=CategoryPurpose.EXPENSE)
    child = Category(
        name="餐饮",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id=source.id,
    )
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            for category in (source, destination, child):
                create_category(session, category)

        with session.begin():
            update_category(
                session,
                source,
                parent_category_id=destination.id,
            )
        assert source.parent_category_id == destination.id
        assert child.parent_category_id == source.id


def test_referenced_category_allows_safe_display_updates(tmp_path: Path) -> None:
    """验证被交易引用的分类仍可修改安全展示属性。"""

    engine = make_engine(tmp_path / "safe-display-update.sqlite3")
    account = Account(type=AccountType.CREDIT, name="引用账户")
    category = Category(name="原名称", purpose=CategoryPurpose.EXPENSE)
    transaction = Transaction(
        type=TransactionType.EXPENSE,
        src_account_id=account.id,
        amount_minor=100,
        category=category.id,
        occurred_at=datetime.now(UTC),
    )
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            session.add(account)
            create_category(session, category)
            session.add(transaction)

        with session.begin():
            update_category(
                session,
                category,
                name="新名称",
                description="更新后的展示说明",
                icon_color="#00ff00",
                icon_name="meal",
            )

        assert category.name == "新名称"
        assert transaction.category == category.id


def test_subtree_move_rejects_existing_purpose_mismatch(tmp_path: Path) -> None:
    """验证移动前会拒绝现有子树内部的异常用途。"""

    engine = make_engine(tmp_path / "dirty-subtree-purpose.sqlite3")
    source = Category(name="生活", purpose=CategoryPurpose.EXPENSE)
    destination = Category(name="固定支出", purpose=CategoryPurpose.EXPENSE)
    child = Category(
        name="餐饮",
        purpose=CategoryPurpose.EXPENSE,
        parent_category_id=source.id,
    )
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            for category in (source, destination, child):
                create_category(session, category)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE categories SET purpose = 'income' WHERE id = ?",
                (child.id,),
            )
        session.expire_all()

        with pytest.raises(CategoryHierarchyError) as error, session.begin():
            update_category(
                session,
                source,
                parent_category_id=destination.id,
            )

        assert_error_code(
            error,
            CategoryHierarchyErrorCode.SUBTREE_PURPOSE_MISMATCH,
        )
