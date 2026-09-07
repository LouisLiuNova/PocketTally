"""分类树完整性服务与 SQLite 集成测试。"""

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
from app.models import Category


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
    category = Category(id="category-1", name="餐饮", parent_category_id="category-1")
    with Session(engine) as session:
        with pytest.raises(CategoryHierarchyError) as error, session.begin():
            create_category(session, category)

        assert_error_code(error, CategoryHierarchyErrorCode.SELF_PARENT)
        assert session.get(Category, category.id) is None


def test_update_category_rejects_descendant_as_parent(tmp_path: Path) -> None:
    """验证多层分类不能移动到自己的后代节点下。"""

    engine = make_engine(tmp_path / "descendant-parent.sqlite3")
    root = Category(name="生活")
    child = Category(name="餐饮", parent_category_id=root.id)
    grandchild = Category(name="工作餐", parent_category_id=child.id)
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
    category = Category(name="餐饮")
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
    root = Category(name="生活")
    destination = Category(name="固定支出")
    child = Category(name="餐饮", parent_category_id=root.id)
    grandchild = Category(name="工作餐", parent_category_id=child.id)
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            for category in (root, destination, child, grandchild):
                create_category(session, category)

        with session.begin():
            update_category(session, child, parent_category_id=destination.id)

        assert child.parent_category_id == destination.id
        assert grandchild.parent_category_id == child.id


def test_category_service_rejects_missing_parent(tmp_path: Path) -> None:
    """验证创建和更新统一拒绝不存在的父分类。"""

    engine = make_engine(tmp_path / "missing-parent.sqlite3")
    category = Category(name="餐饮", parent_category_id="missing")
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
    first = Category(name="分类 A")
    second = Category(name="分类 B", parent_category_id=first.id)
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
            create_category(session, Category(name="餐饮"))

        assert_error_code(
            error,
            CategoryHierarchyErrorCode.TRANSACTION_REQUIRED,
        )
