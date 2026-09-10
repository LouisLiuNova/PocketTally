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

## 前端组件与样式

- 前端应深度接入 Nuxt UI 生态，优先使用 `@nuxt/ui` 已有组件、composable、主题系统和官方推荐的 Nuxt 集成方式，不重复实现组件库已经提供的通用界面能力。
- 开发或修改界面前，必须先检查 Nuxt UI 是否已有合适的组件及扩展点。按钮、卡片、表单控件、对话框、抽屉、导航、分页、提示、空状态和加载状态等通用能力，原则上不得使用自有组件或大段手写 CSS 重新实现。
- 视觉定制优先依次使用 Nuxt UI 语义颜色和设计 token、`app.config.ts` 全局主题、组件 variant/slot、组件 `ui`/`class` 属性以及 Tailwind CSS 工具类；不得以全局硬编码 CSS 覆盖作为默认方案。
- 只有在 Nuxt UI 不具备所需能力，且通过组合现有组件、扩展 slot/variant 或使用 Tailwind 工具类仍无法合理实现时，才允许增加自有组件或 CSS。此类实现必须限定作用域，并在代码或任务说明中记录无法复用现有能力的原因。
- 业务专属的数据可视化、分类树交互和确有必要的复杂布局可以保留自有实现，但应复用 Nuxt UI 的主题 token、交互状态和无障碍基础，不复制 Button、Dialog、Card 等通用组件行为。
- 不得同时引入与 Nuxt UI 职责重叠的完整 UI 组件库。新增前端依赖前，应先确认 Nuxt UI、Nuxt、自有现有依赖或浏览器原生能力不能满足需求。

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
