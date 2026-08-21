# Agent 开发约定

## 通用文档规范

- 项目文档必须使用 Markdown 编写。
- 项目文档必须使用简体中文；代码、命令、路径、配置键和专有名词可保留其原文形式。
- 根据内容语义灵活使用 GitHub 风格的提示块(GitHub Flavored Markdown Alert)，突出警告、注意事项、重要信息、成功结果或失败结果。例如：

  ```markdown
  > [!WARNING]
  > 该操作可能影响已有数据，请先确认备份和回滚方案。
  ```

- 提示块应服务于信息传达，避免为了格式而滥用；提示块标签统一使用大写形式，如 `NOTE`、`TIP`、`IMPORTANT`、`WARNING` 和 `CAUTION`。

## Python 代码

- 类型注解必须遵循 Python 3.14 风格，不为旧版本 Python 添加向前兼容写法。
- 优先使用内置泛型（如 `list[str]`、`dict[str, int]`）和联合类型运算符（如 `str | None`）；禁止使用 `typing.List`、`typing.Dict`、`typing.Optional` 和 `typing.Union` 等旧式写法。
- 前向引用直接使用目标类型（如 `list[Transaction]`），禁止使用带引号的字符串类型注解；不得通过 `from __future__ import annotations` 保留旧版本兼容写法。
- 所有 Python 模块、类、函数和方法都应使用 Google 风格的 docstring。
- docstring 的说明文字必须使用简体中文；`Args`、`Returns`、`Yields`、`Raises` 等 Google 风格保留字保持英文。
- docstring 应说明用途、参数、返回值以及可能抛出的异常；没有对应内容时可以省略相应小节。
- Python 代码中的注释必须使用简体中文，注释应解释必要的背景、原因或非显而易见的逻辑。

## 任务交付与提交前检查

- 每个任务完成前，都必须运行一次 Ruff 对 Python 代码进行扫描和 lint；即使任务没有修改 Python 文件，也要执行该检查并在交付说明中报告结果。
- Ruff 检查未通过时，不得将任务标记为完成；应先修复问题并重新执行检查。

- 提交代码前，必须使用 Ruff 对 Python 代码进行扫描和 lint：

  ```bash
  cd backend
  ruff check .
  ```

- `ruff check .` 未通过时，不得提交代码；应先修复问题并重新执行检查。
