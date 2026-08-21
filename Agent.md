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

- 所有 Python 模块、类、函数和方法都应使用 Google 风格的 docstring。
- docstring 应说明用途、参数、返回值以及可能抛出的异常；没有对应内容时可以省略相应小节。
- Python 代码中的注释必须使用简体中文，注释应解释必要的背景、原因或非显而易见的逻辑。

## 提交前检查

- 提交代码前，必须使用 Ruff 对 Python 代码进行扫描和 lint：

  ```bash
  cd backend
  ruff check .
  ```

- `ruff check .` 未通过时，不得提交代码；应先修复问题并重新执行检查。
