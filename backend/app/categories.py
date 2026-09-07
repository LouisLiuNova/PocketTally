"""分类树完整性校验和写入服务。"""

from enum import StrEnum

from sqlmodel import Session, select

from app.models import Category, CategoryPurpose


class CategoryHierarchyErrorCode(StrEnum):
    """分类层级业务错误码。"""

    PARENT_NOT_FOUND = "category_parent_not_found"
    SELF_PARENT = "category_self_parent"
    CYCLE_DETECTED = "category_cycle_detected"
    PURPOSE_IMMUTABLE = "category_purpose_immutable"
    PURPOSE_MISMATCH = "category_purpose_mismatch"
    SUBTREE_PURPOSE_MISMATCH = "category_subtree_purpose_mismatch"
    UNSUPPORTED_FIELD = "category_unsupported_field"
    TRANSACTION_REQUIRED = "category_transaction_required"


class CategoryHierarchyError(ValueError):
    """分类写入不符合树结构或用途约束。"""

    def __init__(self, code: CategoryHierarchyErrorCode, message: str) -> None:
        """初始化带稳定错误码的分类层级异常。

        Args:
            code: 可供接口层稳定映射的业务错误码。
            message: 面向开发者的简体中文错误说明。
        """

        super().__init__(message)
        self.code = code


_UPDATABLE_FIELDS = frozenset(
    {
        "name",
        "description",
        "parent_category_id",
        "icon_color",
        "icon_name",
    }
)


def _require_transaction(session: Session) -> None:
    """确保分类写入由调用方的显式事务包裹。

    Args:
        session: 当前数据库会话。

    Raises:
        CategoryHierarchyError: 会话未处于数据库事务中时抛出。
    """

    if not session.in_transaction():
        raise CategoryHierarchyError(
            CategoryHierarchyErrorCode.TRANSACTION_REQUIRED,
            "分类写入必须在显式数据库事务中执行",
        )


def validate_category_hierarchy(
    session: Session,
    *,
    category_id: str,
    parent_category_id: str | None,
) -> None:
    """验证分类的候选父节点能形成可终止的树结构。

    校验从候选父节点沿祖先链迭代上行，因此不依赖递归深度。访问过的
    节点会被记录，既能阻止把分类移动到自己的后代，也能发现候选祖先链
    中已经存在的异常循环。创建、更新和未来批量导入应统一调用本函数。

    Args:
        session: 当前数据库会话。
        category_id: 待创建或更新的分类 ID。
        parent_category_id: 候选父分类 ID；``None`` 表示顶级分类。

    Raises:
        CategoryHierarchyError: 父节点不存在、指向自身或祖先链存在循环时抛出。
    """

    if parent_category_id is None:
        return
    if parent_category_id == category_id:
        raise CategoryHierarchyError(
            CategoryHierarchyErrorCode.SELF_PARENT,
            "分类不能将自身设为父分类",
        )

    visited_ids: set[str] = set()
    current_id: str | None = parent_category_id
    while current_id is not None:
        if current_id == category_id:
            raise CategoryHierarchyError(
                CategoryHierarchyErrorCode.CYCLE_DETECTED,
                "不能将分类移动到自身的后代节点下",
            )
        if current_id in visited_ids:
            raise CategoryHierarchyError(
                CategoryHierarchyErrorCode.CYCLE_DETECTED,
                "现有分类祖先链包含循环引用",
            )
        visited_ids.add(current_id)

        current = session.get(Category, current_id)
        if current is None:
            raise CategoryHierarchyError(
                CategoryHierarchyErrorCode.PARENT_NOT_FOUND,
                f"父分类不存在: {current_id}",
            )
        current_id = current.parent_category_id


def _validate_parent_purpose(
    session: Session,
    *,
    purpose: CategoryPurpose,
    parent_category_id: str | None,
) -> None:
    """验证父分类存在且用途与当前分类一致。

    Args:
        session: 当前数据库会话。
        purpose: 当前分类的不可变用途。
        parent_category_id: 候选父分类 ID。

    Raises:
        CategoryHierarchyError: 父分类不存在或用途不一致时抛出。
    """

    if parent_category_id is None:
        return
    parent = session.get(Category, parent_category_id)
    if parent is None:
        raise CategoryHierarchyError(
            CategoryHierarchyErrorCode.PARENT_NOT_FOUND,
            f"父分类不存在: {parent_category_id}",
        )
    if parent.purpose != purpose:
        raise CategoryHierarchyError(
            CategoryHierarchyErrorCode.PURPOSE_MISMATCH,
            "父分类和子分类的用途必须相同",
        )


def _validate_subtree_purpose(session: Session, category: Category) -> None:
    """验证分类子树用途一致。

    Args:
        session: 当前数据库会话。
        category: 待检查子树的根分类。

    Raises:
        CategoryHierarchyError: 子树包含循环或用途不一致时抛出。
    """

    visited_ids = {category.id}
    pending_ids = [category.id]
    while pending_ids:
        parent_id = pending_ids.pop()
        children = list(
            session.exec(
                select(Category).where(Category.parent_category_id == parent_id)
            )
        )
        for child in children:
            if child.id in visited_ids:
                raise CategoryHierarchyError(
                    CategoryHierarchyErrorCode.CYCLE_DETECTED,
                    "现有分类子树包含循环引用",
                )
            visited_ids.add(child.id)
            if child.purpose != category.purpose:
                raise CategoryHierarchyError(
                    CategoryHierarchyErrorCode.SUBTREE_PURPOSE_MISMATCH,
                    "现有分类子树内部用途不一致",
                )
            pending_ids.append(child.id)


def create_category(session: Session, category: Category) -> Category:
    """校验并写入一个分类。

    调用方负责提交或回滚事务；本函数只刷新当前写入，以便后续同事务操作
    可以引用该分类。

    Args:
        session: 当前数据库会话。
        category: 待创建的分类实例。

    Returns:
        已写入并刷新的分类实例。

    Raises:
        CategoryHierarchyError: 缺少事务或分类父子关系不合法时抛出。
    """

    _require_transaction(session)
    validate_category_hierarchy(
        session,
        category_id=category.id,
        parent_category_id=category.parent_category_id,
    )
    _validate_parent_purpose(
        session,
        purpose=category.purpose,
        parent_category_id=category.parent_category_id,
    )
    session.add(category)
    session.flush()
    return category


def update_category(
    session: Session,
    category: Category,
    **changes: object,
) -> Category:
    """校验分类的完整候选状态并更新分类。

    即使本次没有修改父节点，也会重新验证当前祖先链，以便已有异常关系
    返回稳定业务错误，而不是在后续读取或递归聚合时无限循环。

    Args:
        session: 当前数据库会话。
        category: 已加载的待更新分类。
        **changes: 要更新的分类字段。

    Returns:
        已更新并刷新的分类实例。

    Raises:
        CategoryHierarchyError: 缺少事务、用途变更或候选层级不合法时抛出。
    """

    _require_transaction(session)
    if "purpose" in changes:
        raise CategoryHierarchyError(
            CategoryHierarchyErrorCode.PURPOSE_IMMUTABLE,
            "分类用途创建后不可修改",
        )
    unsupported_fields = changes.keys() - _UPDATABLE_FIELDS
    if unsupported_fields:
        names = ", ".join(sorted(unsupported_fields))
        raise CategoryHierarchyError(
            CategoryHierarchyErrorCode.UNSUPPORTED_FIELD,
            f"不支持更新分类字段: {names}",
        )

    parent_category_id = changes.get(
        "parent_category_id",
        category.parent_category_id,
    )
    if parent_category_id is not None and not isinstance(parent_category_id, str):
        raise CategoryHierarchyError(
            CategoryHierarchyErrorCode.PARENT_NOT_FOUND,
            "父分类 ID 必须是字符串或 null",
        )
    validate_category_hierarchy(
        session,
        category_id=category.id,
        parent_category_id=parent_category_id,
    )
    _validate_parent_purpose(
        session,
        purpose=category.purpose,
        parent_category_id=parent_category_id,
    )

    is_move = (
        "parent_category_id" in changes
        and parent_category_id != category.parent_category_id
    )
    if is_move:
        _validate_subtree_purpose(session, category)

    for field_name, value in changes.items():
        setattr(category, field_name, value)
    session.add(category)
    session.flush()
    return category


__all__ = (
    "CategoryHierarchyError",
    "CategoryHierarchyErrorCode",
    "create_category",
    "update_category",
    "validate_category_hierarchy",
)
