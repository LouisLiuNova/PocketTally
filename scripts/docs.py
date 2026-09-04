"""构建并校验 PocketTally 静态文档站。"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DOCS = ROOT / "docs"
BUILD_DOCS = ROOT / ".docs-build"
HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}


class DocumentationError(ValueError):
    """表示文档契约或生成输入无效。"""


@dataclass(frozen=True)
class Operation:
    """表示用于设计和实现对照的 HTTP 操作。"""

    method: str
    path: str
    operation_id: str
    summary: str

    @property
    def key(self) -> tuple[str, str]:
        """返回忽略 operationId 的接口匹配键。"""

        return self.method, self.path


@dataclass(frozen=True)
class DbmlColumn:
    """表示 DBML 表中的一列。"""

    name: str
    data_type: str
    attributes: str
    note: str


@dataclass
class DbmlTable:
    """表示 DBML 数据表及其字段。"""

    name: str
    columns: list[DbmlColumn]


def load_yaml(path: Path) -> dict[str, Any]:
    """读取 YAML 对象并验证顶层类型。"""

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DocumentationError(f"无法解析 YAML：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DocumentationError(f"YAML 顶层必须是对象：{path}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    """读取 JSON 对象并验证顶层类型。"""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DocumentationError(f"无法解析 JSON：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DocumentationError(f"JSON 顶层必须是对象：{path}")
    return data


def normalize_path(path: str, prefixes: tuple[str, ...] = ("/api/v1",)) -> str:
    """移除运行时 API 前缀并规范化路径。"""

    normalized = "/" + path.strip("/")
    for prefix in prefixes:
        clean_prefix = "/" + prefix.strip("/")
        if normalized == clean_prefix:
            return "/"
        if normalized.startswith(f"{clean_prefix}/"):
            normalized = normalized[len(clean_prefix) :]
            break
    return normalized or "/"


def extract_operations(
    spec: dict[str, Any], *, prefixes: tuple[str, ...] = ()
) -> list[Operation]:
    """从 OpenAPI 文档提取操作并拒绝重复 operationId。"""

    paths = spec.get("paths")
    if not isinstance(paths, dict):
        raise DocumentationError("OpenAPI 缺少 paths 对象")
    operations: list[Operation] = []
    seen_ids: set[str] = set()
    for raw_path, path_item in paths.items():
        if not isinstance(raw_path, str) or not isinstance(path_item, dict):
            raise DocumentationError("OpenAPI path 必须映射到对象")
        for method, operation in path_item.items():
            if str(method).lower() not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                raise DocumentationError(f"无效操作：{method} {raw_path}")
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise DocumentationError(f"操作缺少 operationId：{method} {raw_path}")
            if operation_id in seen_ids:
                raise DocumentationError(f"重复 operationId：{operation_id}")
            seen_ids.add(operation_id)
            operations.append(
                Operation(
                    method=str(method).upper(),
                    path=normalize_path(raw_path, prefixes),
                    operation_id=operation_id,
                    summary=str(operation.get("summary", "")),
                )
            )
    return sorted(operations, key=lambda item: (item.path, item.method))


def compare_operations(
    design: list[Operation], actual: list[Operation]
) -> list[tuple[str, Operation]]:
    """按方法与路径比较设计接口和实际接口。"""

    design_by_key = {item.key: item for item in design}
    actual_by_key = {item.key: item for item in actual}
    rows: list[tuple[str, Operation]] = []
    for key in sorted(
        design_by_key.keys() | actual_by_key.keys(), key=lambda item: (item[1], item[0])
    ):
        if key in design_by_key and key in actual_by_key:
            rows.append(("已实现", design_by_key[key]))
        elif key in design_by_key:
            rows.append(("设计中", design_by_key[key]))
        else:
            rows.append(("仅实现", actual_by_key[key]))
    return rows


def walk_refs(value: Any) -> Iterator[str]:
    """递归返回 JSON 或 YAML 对象中的所有引用。"""

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                yield child
            else:
                yield from walk_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(child)


def resolve_pointer(document: Any, fragment: str) -> Any:
    """解析 JSON Pointer，找不到目标时抛出文档错误。"""

    current = document
    if not fragment:
        return current
    if not fragment.startswith("/"):
        raise DocumentationError(f"不支持的引用片段：#{fragment}")
    for part in fragment[1:].split("/"):
        key = unquote(part).replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            raise DocumentationError(f"引用目标不存在：#{fragment}")
        current = current[key]
    return current


def validate_references(path: Path, document: dict[str, Any]) -> None:
    """验证文档中的全部本地文件引用和 JSON Pointer。"""

    for reference in walk_refs(document):
        if reference.startswith(("http://", "https://")):
            raise DocumentationError(f"$ref 必须指向仓库内契约：{reference}")
        file_part, separator, fragment = reference.partition("#")
        target_path = (path.parent / file_part).resolve() if file_part else path.resolve()
        try:
            target_path.relative_to(ROOT)
        except ValueError as exc:
            raise DocumentationError(f"$ref 超出仓库范围：{reference}") from exc
        if not target_path.is_file():
            raise DocumentationError(f"$ref 文件不存在：{path}: {reference}")
        target = load_json(target_path) if target_path.suffix == ".json" else load_yaml(target_path)
        if separator:
            resolve_pointer(target, fragment)


def validate_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    """验证 OpenAPI、JSON Schema 以及 Apidog 操作的一致性。"""

    openapi_path = SOURCE_DOCS / "contracts/apis/openapi.yaml"
    apidog_path = SOURCE_DOCS / "contracts/apis/openapi.apidog.yaml"
    openapi = load_yaml(openapi_path)
    apidog = load_yaml(apidog_path)
    if not str(openapi.get("openapi", "")).startswith("3.1"):
        raise DocumentationError("设计 OpenAPI 必须使用 3.1 版本")
    validate_references(openapi_path, openapi)
    validate_references(apidog_path, apidog)

    model_titles: set[str] = set()
    for path in sorted((SOURCE_DOCS / "contracts/models").glob("*.schema.json")):
        schema = load_json(path)
        validator_for(schema).check_schema(schema)
        validate_references(path, schema)
        title = schema.get("title")
        if path.name != "common.schema.json" and isinstance(title, str):
            model_titles.add(title)

    design_operations = extract_operations(openapi)
    apidog_operations = extract_operations(apidog)
    design_signature = {(item.key, item.operation_id) for item in design_operations}
    apidog_signature = {(item.key, item.operation_id) for item in apidog_operations}
    if design_signature != apidog_signature:
        raise DocumentationError("openapi.yaml 与 openapi.apidog.yaml 的接口清单不一致")
    embedded_titles = {
        value.get("title")
        for value in apidog.get("components", {}).get("schemas", {}).values()
        if isinstance(value, dict) and isinstance(value.get("title"), str)
    }
    missing_titles = model_titles - embedded_titles
    if missing_titles:
        names = ", ".join(sorted(missing_titles))
        raise DocumentationError(f"Apidog 契约缺少 HTTP 模型：{names}")
    return openapi, apidog


def actual_openapi() -> dict[str, Any]:
    """从 FastAPI 应用生成当前实现接口，不启动生命周期资源。"""

    backend = ROOT / "backend"
    sys.path.insert(0, str(backend))
    try:
        from app.config import Settings
        from app.main import create_app

        application = create_app(Settings(environment="test"))
        return application.openapi()
    finally:
        sys.path.remove(str(backend))


def split_dbml_attributes(value: str) -> list[str]:
    """按逗号拆分 DBML 属性，同时保留引号内的逗号。"""

    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for character in value:
        if character in {"'", '"'}:
            quote = None if quote == character else character if quote is None else quote
        if character == "," and quote is None:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    if current:
        parts.append("".join(current).strip())
    return parts


def parse_dbml(text: str) -> tuple[list[DbmlTable], list[tuple[str, str, str, str]]]:
    """解析项目使用的 DBML 表、列和外键语法。"""

    tables: list[DbmlTable] = []
    relations: list[tuple[str, str, str, str]] = []
    current: DbmlTable | None = None
    nested_depth = 0
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        table_match = re.fullmatch(r"Table\s+([A-Za-z_][\w]*)\s*\{", line)
        if table_match:
            if current is not None:
                raise DocumentationError(f"DBML 表发生嵌套：第 {line_number} 行")
            current = DbmlTable(table_match.group(1), [])
            tables.append(current)
            continue
        if nested_depth:
            if line.endswith("{"):
                nested_depth += 1
            elif line == "}":
                nested_depth -= 1
            continue
        if current is not None and line.endswith("{"):
            nested_depth = 1
            continue
        if line == "}":
            current = None
            continue
        if current is None:
            continue
        foreign_key = re.fullmatch(
            r"FOREIGN KEY\s*\((\w+)\)\s+REFERENCES\s+(\w+)\((\w+)\)", line
        )
        if foreign_key:
            relations.append((current.name, foreign_key.group(1), foreign_key.group(2), foreign_key.group(3)))
            continue
        column_match = re.fullmatch(r"(\w+)\s+([\w()]+)(?:\s+\[(.*)\])?", line)
        if not column_match:
            raise DocumentationError(f"无法解析 DBML 第 {line_number} 行：{line}")
        attributes = column_match.group(3) or ""
        parts = split_dbml_attributes(attributes)
        note = ""
        for part in parts:
            note_match = re.fullmatch(r"note\s*:\s*(['\"])(.*)\1", part)
            if note_match:
                note = note_match.group(2)
        current.columns.append(
            DbmlColumn(column_match.group(1), column_match.group(2), attributes, note)
        )
    if not tables or any(not table.columns for table in tables):
        raise DocumentationError("DBML 必须包含至少一个非空数据表")
    columns_by_table = {
        table.name: {column.name for column in table.columns} for table in tables
    }
    for source, source_column, target, target_column in relations:
        if source_column not in columns_by_table[source]:
            raise DocumentationError(f"DBML 外键字段不存在：{source}.{source_column}")
        if target not in columns_by_table or target_column not in columns_by_table[target]:
            raise DocumentationError(f"DBML 外键目标不存在：{target}.{target_column}")
    return tables, relations


def dbml_markdown(tables: list[DbmlTable], relations: list[tuple[str, str, str, str]]) -> str:
    """生成数据库模型与 Mermaid ER 图页面。"""

    lines = [
        "# 数据库模型",
        "",
        "本页由 `docs/contracts/db.dbml` 自动生成。DBML 负责表、列、主键和外键；SQLite 的 `CHECK`、`COLLATE`、索引、触发器及连接级 `PRAGMA` 仍以 `backend/db/schema.sql` 为准。",
        "",
        "## 实体关系",
        "",
        "```mermaid",
        "erDiagram",
    ]
    for source, source_column, target, target_column in relations:
        lines.append(f"    {target} ||--o{{ {source} : \"{source_column} → {target_column}\"")
    for table in tables:
        lines.append(f"    {table.name} {{")
        for column in table.columns:
            markers = " PK" if re.search(r"(^|,)\s*pk\s*(,|$)", column.attributes) else ""
            lines.append(f"        {column.data_type} {column.name}{markers}")
        lines.append("    }")
    lines.extend(["```", ""])
    for table in tables:
        lines.extend([f"## `{table.name}`", "", "| 字段 | 类型 | 约束 | 说明 |", "| --- | --- | --- | --- |"])
        for column in table.columns:
            attributes = re.sub(r",?\s*note\s*:\s*(['\"]).*?\1", "", column.attributes).strip(" ,")
            lines.append(
                f"| `{column.name}` | `{column.data_type}` | {attributes or '—'} | {column.note or '—'} |"
            )
        lines.append("")
    return "\n".join(lines)


def schema_type(schema: dict[str, Any]) -> str:
    """返回适合模型索引显示的简短字段类型。"""

    reference = schema.get("$ref")
    if isinstance(reference, str):
        return f"`{reference.rsplit('/', maxsplit=1)[-1].removesuffix('.schema.json')}`"
    raw_type = schema.get("type")
    if isinstance(raw_type, list):
        return " / ".join(f"`{item}`" for item in raw_type)
    if isinstance(raw_type, str):
        if raw_type == "array" and isinstance(schema.get("items"), dict):
            return f"数组：{schema_type(schema['items'])}"
        return f"`{raw_type}`"
    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        return " / ".join(schema_type(item) for item in one_of if isinstance(item, dict))
    return "—"


def http_models_markdown() -> str:
    """从 JSON Schema 生成 HTTP 请求和响应模型索引。"""

    lines = [
        "# HTTP 模型",
        "",
        "本页由 `docs/contracts/models/*.schema.json` 自动生成。请求属性采用 camelCase，未知属性会被拒绝。",
        "",
    ]
    for path in sorted((SOURCE_DOCS / "contracts/models").glob("*.schema.json")):
        schema = load_json(path)
        title = str(schema.get("title", path.stem))
        description = str(schema.get("description", ""))
        required = set(schema.get("required", []))
        properties = schema.get("properties", {})
        lines.extend([f"## `{title}`", "", description, ""])
        if isinstance(properties, dict) and properties:
            lines.extend(["| 字段 | 类型 | 必填 | 说明 |", "| --- | --- | --- | --- |"])
            for name, value in properties.items():
                if not isinstance(value, dict):
                    continue
                field_description = str(value.get("description", "—")).replace("|", "\\|")
                lines.append(
                    f"| `{name}` | {schema_type(value)} | {'是' if name in required else '否'} | {field_description} |"
                )
            lines.append("")
        lines.append(f"[查看原始 JSON Schema](contracts/models/{path.name})")
        lines.append("")
    return "\n".join(lines)


def api_status_markdown(rows: list[tuple[str, Operation]]) -> str:
    """生成设计与实际接口的状态对照页面。"""

    counts = {status: sum(1 for row_status, _ in rows if row_status == status) for status in ("已实现", "设计中", "仅实现")}
    lines = [
        "# 接口实现状态",
        "",
        "本页在构建时对照设计 OpenAPI 与 FastAPI 动态 OpenAPI。匹配依据为规范化后的 HTTP 方法和路径。",
        "",
        f"- **已实现：{counts['已实现']}**",
        f"- **设计中：{counts['设计中']}**",
        f"- **仅实现：{counts['仅实现']}**",
        "",
        "| 状态 | 方法 | 路径 | operationId | 摘要 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for status, operation in rows:
        lines.append(
            f"| {status} | `{operation.method}` | `{operation.path}` | `{operation.operation_id}` | {operation.summary or '—'} |"
        )
    lines.extend(
        [
            "",
            "> [!NOTE]",
            "> “设计中”表示契约已经存在，但 FastAPI 尚未注册同方法、同路径的路由；“仅实现”表示运行时代码已有路由，但设计契约尚未收录。",
        ]
    )
    return "\n".join(lines)


def api_reference_html() -> str:
    """生成使用固定版本 Redoc 的独立 API 参考页面。"""

    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PocketTally API 参考</title>
  <style>body{margin:0;padding:0} .back{position:fixed;right:1rem;top:.5rem;z-index:10;background:#fff;padding:.45rem .7rem;border:1px solid #ddd;border-radius:.25rem;font:14px sans-serif}</style>
</head>
<body>
  <a class="back" href="api-status/">返回文档站</a>
  <redoc spec-url="contracts/apis/openapi.yaml" hide-download-button="false"></redoc>
  <script src="https://cdn.jsdelivr.net/npm/redoc@2.5.3/bundles/redoc.standalone.js"></script>
</body>
</html>
"""


def git_version() -> tuple[str, str]:
    """读取当前提交短 SHA 和构建时间。"""

    result = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return result.stdout.strip(), generated_at


def prepare() -> list[tuple[str, Operation]]:
    """校验事实来源并生成临时 MkDocs 输入目录。"""

    openapi, _ = validate_contracts()
    actual = actual_openapi()
    design_operations = extract_operations(openapi)
    actual_operations = extract_operations(actual, prefixes=("/api/v1",))
    rows = compare_operations(design_operations, actual_operations)
    tables, relations = parse_dbml((SOURCE_DOCS / "contracts/db.dbml").read_text(encoding="utf-8"))

    if BUILD_DOCS.exists():
        shutil.rmtree(BUILD_DOCS)
    shutil.copytree(SOURCE_DOCS, BUILD_DOCS, ignore=shutil.ignore_patterns("requirements.lock"))
    shutil.copy2(ROOT / "TODO.md", BUILD_DOCS / "TODO.md")
    shutil.copy2(ROOT / "TODO-IMP.md", BUILD_DOCS / "TODO-IMP.md")
    business_rules = BUILD_DOCS / "business-rules.md"
    business_rules.write_text(
        business_rules.read_text(encoding="utf-8").replace("(../TODO.md)", "(TODO.md)"),
        encoding="utf-8",
    )
    todo = BUILD_DOCS / "TODO.md"
    todo.write_text(
        todo.read_text(encoding="utf-8").replace(
            "(docs/business-rules.md)", "(business-rules.md)"
        ),
        encoding="utf-8",
    )
    (BUILD_DOCS / "data-models.md").write_text(dbml_markdown(tables, relations), encoding="utf-8")
    (BUILD_DOCS / "http-models.md").write_text(http_models_markdown(), encoding="utf-8")
    (BUILD_DOCS / "api-status.md").write_text(api_status_markdown(rows), encoding="utf-8")
    (BUILD_DOCS / "api-reference.html").write_text(api_reference_html(), encoding="utf-8")
    generated = BUILD_DOCS / "generated"
    generated.mkdir()
    sha, generated_at = git_version()
    generated.joinpath("version.md").write_text(
        f"\n---\n\n文档版本：[`{sha}`](https://github.com/LouisLiuNova/PocketTally/commit/{sha}) · 生成时间：{generated_at}\n",
        encoding="utf-8",
    )
    return rows


def run_mkdocs(command: str) -> None:
    """准备文档输入并调用 MkDocs。"""

    prepare()
    arguments = [sys.executable, "-m", "mkdocs", command, "--config-file", str(ROOT / "mkdocs.yml"), "--strict"]
    if command == "serve":
        arguments.extend(["--dev-addr", "127.0.0.1:8001"])
    subprocess.run(arguments, cwd=ROOT, check=True)


def main() -> None:
    """解析命令行参数并执行文档检查、构建或预览。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "build", "serve"))
    arguments = parser.parse_args()
    try:
        if arguments.command == "check":
            rows = prepare()
            counts = {status: sum(1 for item_status, _ in rows if item_status == status) for status in ("已实现", "设计中", "仅实现")}
            print(f"文档契约有效：已实现 {counts['已实现']}，设计中 {counts['设计中']}，仅实现 {counts['仅实现']}")
        else:
            run_mkdocs(arguments.command)
    except (DocumentationError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"文档构建失败：{exc}\n")


if __name__ == "__main__":
    main()
