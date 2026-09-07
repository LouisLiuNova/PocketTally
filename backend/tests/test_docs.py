"""文档站生成器测试。"""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def load_docs_module() -> ModuleType:
    """从仓库脚本路径加载文档生成器。"""

    path = Path(__file__).resolve().parents[2] / "scripts/docs.py"
    spec = importlib.util.spec_from_file_location("pockettally_docs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


docs = load_docs_module()


def operation(method: str, path: str, operation_id: str) -> object:
    """构造用于状态对照的操作。"""

    return docs.Operation(method, path, operation_id, operation_id)


def test_compare_operations_covers_all_statuses() -> None:
    """验证已实现、设计中和仅实现三种状态。"""

    design = [operation("GET", "/accounts", "listAccounts"), operation("POST", "/accounts", "createAccount")]
    actual = [operation("GET", "/accounts", "runtimeList"), operation("GET", "/health", "health")]

    rows = docs.compare_operations(design, actual)

    assert {(status, item.key) for status, item in rows} == {
        ("已实现", ("GET", "/accounts")),
        ("设计中", ("POST", "/accounts")),
        ("仅实现", ("GET", "/health")),
    }


def test_extract_operations_normalizes_prefix() -> None:
    """验证 FastAPI 的版本前缀不参与接口匹配。"""

    spec = {"paths": {"/api/v1/health": {"get": {"operationId": "health"}}}}

    operations = docs.extract_operations(spec, prefixes=("/api/v1",))

    assert operations[0].path == "/health"


def test_extract_operations_rejects_duplicate_operation_id() -> None:
    """验证重复 operationId 会中止构建。"""

    spec = {
        "paths": {
            "/one": {"get": {"operationId": "duplicate"}},
            "/two": {"post": {"operationId": "duplicate"}},
        }
    }

    with pytest.raises(docs.DocumentationError, match="重复 operationId"):
        docs.extract_operations(spec)


def test_extract_operations_rejects_invalid_contract() -> None:
    """验证缺少 paths 的契约会中止构建。"""

    with pytest.raises(docs.DocumentationError, match="缺少 paths"):
        docs.extract_operations({"openapi": "3.1.0"})


def test_implemented_api_status_codes_match_static_openapi() -> None:
    """验证 Issue #4/#12 路由与静态 OpenAPI 的响应状态完全一致。"""

    design, _ = docs.validate_contracts()
    actual = docs.actual_openapi()
    implemented = {
        ("get", "/accounts"),
        ("post", "/accounts"),
        ("get", "/accounts/{accountId}"),
        ("patch", "/accounts/{accountId}"),
        ("delete", "/accounts/{accountId}"),
        ("get", "/categories"),
        ("post", "/categories"),
        ("get", "/categories/{categoryId}"),
        ("patch", "/categories/{categoryId}"),
        ("delete", "/categories/{categoryId}"),
        ("get", "/tags"),
        ("post", "/tags"),
        ("get", "/tags/{tagId}"),
        ("patch", "/tags/{tagId}"),
        ("delete", "/tags/{tagId}"),
        ("get", "/transactions"),
        ("post", "/transactions"),
        ("post", "/transactions/refunds"),
        ("get", "/transactions/{transactionId}"),
        ("patch", "/transactions/{transactionId}"),
        ("post", "/transactions/{transactionId}/void"),
    }
    actual_paths = {
        docs.normalize_path(path, ("/api/v1",)): value
        for path, value in actual["paths"].items()
    }

    for method, path in implemented:
        design_statuses = set(design["paths"][path][method]["responses"])
        actual_statuses = set(actual_paths[path][method]["responses"])
        assert actual_statuses == design_statuses, f"{method.upper()} {path}"

    error_properties = set(actual["components"]["schemas"]["ErrorResponse"]["properties"])
    assert error_properties == {"code", "message", "details"}
    assert "delete" not in design["paths"]["/transactions/{transactionId}"]
    assert "delete" not in actual_paths["/transactions/{transactionId}"]


def test_parse_dbml_generates_table_and_relation() -> None:
    """验证 DBML 字段、备注和外键会进入模型。"""

    tables, relations = docs.parse_dbml(
        """Table parents{\n id TEXT [pk,note:'主键']\n}\nTable children{\n parent_id TEXT [notnull]\n indexes {\n  (parent_id)\n }\n FOREIGN KEY (parent_id) REFERENCES parents(id)\n}\n"""
    )

    assert [table.name for table in tables] == ["parents", "children"]
    assert tables[0].columns[0].note == "主键"
    assert relations == [("children", "parent_id", "parents", "id")]
