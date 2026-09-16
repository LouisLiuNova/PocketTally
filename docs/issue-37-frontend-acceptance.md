# Issue #37 前端 CSS 收敛与 Nuxt UI 验收

> [!NOTE]
> 本文记录 2026-09-16 的实现和验证快照。它用于复核 Issue #37，不替代实时 GitHub Issue、PR、CI 或生产运行状态。

## 目标与边界

Issue #37 的目标是清理前端遗留的通用原型 CSS，完成 Nuxt UI 深度接入验收，同时保留业务专属布局和数据表达。此次变更不修改 API、数据库、金额、时区、分类语义、退款语义或持久化结构。

通用界面能力统一由 `@nuxt/ui` 提供：按钮、卡片、表单控件、导航、分页、弹窗、抽屉、Popover、Toast、Alert、空态、加载态和 Dashboard shell。业务专属的现金流图表、分类树、七列日历、颜色输入和交易表格布局仍保留局部 CSS，因为这些规则表达的是业务信息架构、数据密度或交互状态，而不是重复实现组件库能力。

## 组件采用与保留边界

| 能力 | 当前实现 | 验收结论 |
| --- | --- | --- |
| 应用壳层、侧栏、Panel、Navbar | `UApp`、`UDashboardGroup`、`UDashboardSidebar`、`UDashboardPanel`、`UDashboardNavbar` | 使用 Nuxt UI shell，CSS 只保留品牌、状态和布局 token |
| 通用表面 | `UCard`、`UEmpty`、`USkeleton`、`UAlert` | 移除旧 `.panel`、`.metric-card` 等原型表面；交易页容器已改为 `UCard` |
| 表单与选择控件 | `UForm`、`UFormField`、`UInput`、`UTextarea`、`USelect`、`UCheckbox`、`URadioGroup` | 不保留通用输入或选择器的手写组件行为 |
| 弹层与反馈 | `UModal`、`USlideover`、`UPopover`、`UTooltip`、`useToast` | 共享编辑器只保留业务表单布局，不复制 Dialog/Slideover 行为 |
| 导航与数据容器 | `UNavigationMenu`、`UBreadcrumb`、`UTable`、`UCollapsible` | 页面导航和折叠行为由 Nuxt UI 负责 |
| 交易页 | `UCard` + 交易筛选、表格、摘要和分页局部样式 | 局部样式只表达交易数据密度和响应式布局 |
| 现金流图表 | `CashFlowTrend.client.vue`、`@unovis` | 保留图表尺寸、图例和数据状态等业务规则 |
| 分类树 | `CategoryTree.vue` | 保留树缩进、连线、roving tabindex、方向键和异常链隔离 |
| 日历与颜色输入 | 统计日历、`ColorInput.vue` | 保留七列日期关系、容器内滚动和原生颜色输入外观 |

已移除的遗留原型选择器由 `frontend/tests/css-contract.test.ts` 固定检查，包括 `.metric-card`、`.composer`、`.mvp-transaction`、`.resource-row`、`.modal-backdrop`、`.category-picker`、`.cash-calendar`、`.segmented`、`.period-tabs`、`.filter-chip`、`.ledger-row`、`.workspace-view`、`.topbar`、`.nav-item`、`.donut`、`.sparkline` 和 `.chart-wrap` 等。

## CSS 分层与量化结果

| 文件 | 收敛后职责 |
| --- | --- |
| `frontend/app/assets/css/main.css` | Tailwind/Nuxt UI 入口、字体与品牌 token、全局排版、焦点状态和应用壳层 |
| `frontend/app/assets/css/theme.css` | 语义 palette、Light/Dark token、按钮主题接入和 reduced-motion 规则 |
| `frontend/app/assets/css/layout.css` | 页面流、命名业务网格、设置页、分类工作区和侧栏响应式布局 |
| `frontend/app/assets/css/mvp.css` | 交易筛选/表格/详情、统计日历、分类树业务边界、共享编辑器布局及可读性例外 |
| `frontend/app/assets/css/resource-editor.css` | 原生颜色输入控制的局部规则 |

源码 CSS 以 Issue #37 分支创建前的 `83e8de8` 为基线；当前行数因重排和格式化不具备机械可比性，因此以字节数作为主要源文件指标。

| 指标 | 基线 | 收敛后（2026-09-16） | 变化 |
| --- | ---: | ---: | ---: |
| 五个源码 CSS 合计 | 82,977 B / 1,169 行 | 43,904 B / 1,532 行 | -39,073 B / -47.1%；行数因格式化增加，不作为优化指标 |
| Nuxt 客户端入口 CSS | 259.23 KB | 231,499 B（231.50 KB） | -10.7% |
| Nuxt 客户端入口 CSS gzip | 37.29 KB | 32,914 B（32.91 KB） | -11.7% |
| 直接 UI 依赖 | `@nuxt/ui ^4.11.1` | `@nuxt/ui ^4.11.1` | 未新增重叠 UI 组件库 |
| shadcn 依赖 | 无 | 无 | `package.json` 与 `bun.lock` 均无匹配 |

可重复测量：

```bash
cd frontend
wc -c -l app/assets/css/main.css app/assets/css/mvp.css app/assets/css/theme.css app/assets/css/layout.css app/assets/css/resource-editor.css
bun run build
```

## 验收记录

| 检查项 | 命令/范围 | 结果 |
| --- | --- | --- |
| Nuxt UI CSS 契约、遗留选择器和重叠依赖 | `bun run test`，含 `tests/css-contract.test.ts` | 通过，30/30，122 assertions |
| TypeScript/Nuxt 类型检查 | `bun run typecheck` | 通过 |
| 单元测试 | `bun run test` | 通过，30/30 |
| 生产构建 | `bun run build` | 通过；客户端入口 231,499 B，gzip 32,914 B |
| #67 窄屏排版定向回归 | 三个 Chromium 项目，`issue-67.spec.ts` | 通过，9/9 |
| 完整浏览器验收 | `bun run test:e2e:matrix`，Chromium 1280/1440/1920 | 通过，141/141，9.6 分钟 |
| #17 键盘与 axe | 完整矩阵中的 `keyboard-accessibility.spec.ts` | 通过 |
| reduced-motion | 完整矩阵中的主题与动画回归用例 | 通过 |
| Python lint | `cd backend && uvx ruff check .` | 待提交前复核 |
| Python 测试 | `cd backend && uv run pytest -q` | 待提交前复核 |
| 文档契约与文档构建 | `make docs-check`、`make docs-build` | 待提交前复核 |

## 交付边界

Issue #37 的直接阻塞 Issue 已关闭，本次 PR 使用 `Closes #37` 关联关闭本 Issue。Issue #25 仍需以其自身剩余子任务和关系图为准；本次不将独立的 #46 或其它未完成事项误报为已完成。
