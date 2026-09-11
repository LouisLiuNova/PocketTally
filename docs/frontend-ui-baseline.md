# Nuxt UI 接入基线与组件映射

本文记录 Issue #33 建立的 Nuxt UI 技术基础、组件采用边界和可重复的量化基线。
它服务于后续 Issue #25 的渐进式页面迁移，不代表所有业务页面已经完成重构。

## Issue #40 布局复用决策

Issue #40 统一的是页面容器、页面流和网格约束，不改变业务组件迁移边界。当前决策如下：

| 场景 | 复用能力 | 保留的自有实现与原因 |
| --- | --- | --- |
| 应用内容入口与宽度 | `UMain`、`UContainer`，通过 `ui.base` 固定内容最大宽度和响应式内边距 | 侧栏保留现有语义导航和移动端底部导航；其交互已经由当前浏览器验收覆盖，不为布局重构引入 `UDashboardSidebar` 的持久化/折叠状态 |
| 页面流与业务网格 | `UPageGrid` 或等价的 `page-grid` 作为语义化 Grid 入口，Tailwind/CSS 使用 `minmax(0, 1fr)`、`min-width: 0` 和命名 `grid-template-areas` | 每个页面的区域比例属于业务信息架构：总览的趋势/分类/近期流水和统计的趋势/分类/日历不能抽象成相同列数；分类页让分类树与详情组成主工作区，标签作为右侧次级资源区并与详情底边对齐，避免卡片漂移 |
| 交易筛选和账户卡 | Nuxt UI 按钮与现有输入控件，统一网格容器和断点 | 筛选项的 URL query 提交语义、账户卡操作语义属于 #31 与后续业务页面 Issue，不在本 Issue 重写为完整表单组件 |
| 分类树、现金流趋势、统计日历 | Nuxt UI 主题 token 与基础控件 | 分类树键盘导航、层级保护、异常节点表达和服务端统计降级文本是业务专属交互，保留自有布局避免组件替换造成语义回归 |
| 设置页 | 共享页面流与表单控件 | 保持工具页视觉，不套用业务 `panel` 卡片容器 |

六个路由页面都放在同一个 `UMain`/`UContainer` 内容约束内；页面内部统一使用 `page-flow` 间距，业务网格通过命名区域组织，并在中小视口回退为单列或双列。空态、加载态、错误态和长文本仍作为页面流子项参与相同的最小宽度约束。该布局重构不新增 CSS/UI/布局依赖，也不改变 API、URL query、金额、时区或退款语义。

## 技术边界

- UI 主体系固定为 `@nuxt/ui 4.11.1`、Nuxt 4、Tailwind CSS 4、TypeScript 和 Bun。
- 不引入 `shadcn-vue`、`shadcn-nuxt` 或其他职责重叠的完整组件库。
- 账务 API、请求体、金额单位、Asia/Shanghai 时区、退款规则和 SQLite 工作流不属于 UI 迁移范围。
- 八套配色和 Light/Dark/System 的运行时选择由 `data-palette`、`data-theme`、Nuxt UI color mode class 和本地偏好共同保持一致；完整角色、对比度与扩展规则见[前端语义主题与配色契约](frontend-theme.md)。

Nuxt UI 的全局主题应优先通过 `app.config.ts`、`--ui-*` token、Tailwind theme、组件 variant、slot、`ui` 和 `class` 扩展。页面只在业务布局或专属数据可视化无法由组件合理表达时保留局部 CSS。

## 组件映射

| 当前能力或自有实现 | Nuxt UI 目标 | 采用时机与边界 | 关联任务 |
| --- | --- | --- | --- |
| `UApp`、`UButton`、`UModal`、`UIcon` | 继续使用并统一语义色、variant 和默认尺寸 | 主操作使用 `primary`，次要操作使用 `neutral`，破坏性操作使用 `error` | #33、#25 |
| 原生表单、`.composer` 字段样式 | `UForm`、`UFormField`、`UInput`、`USelect`、`UTextarea`、`UCheckbox` | Issue #33 先迁移 `ResourceEditor`；业务校验仍由现有服务逻辑负责 | #33、#34、#35 |
| `.panel`、指标卡和资源卡片 | `UCard` | 后续页面迁移时使用；业务图表内部布局可继续局部实现 | #34、#35、#36 |
| 自有用途 Tab 和筛选 Tab | `UTabs` | #31 已确定信息架构和 URL query；控件迁移按业务页面任务实施 | #31、#35、#36 |
| 自有分页按钮 | `UPagination` | 交易列表迁移时替换，保留服务端分页语义 | #34 |
| 自有侧边导航、Header、Breadcrumb | `USidebar`/`UDashboardSidebar`、`UHeader`、`UBreadcrumb` | 应用壳层统一改造，不在 #33 提前重写 | #30 |
| 自有确认弹窗和详情弹层 | `UModal`、`USlideover`、`UPopover`、`UTooltip` | 已有 `UModal` 保留；详情抽屉和提示由业务页面任务决定 | #32、#34、#35 |
| `.error-box`、`.info-strip`、成功提示 | `UAlert`、`useToast` | 表单和服务端错误使用 `UAlert`；全局操作反馈由 #32 统一 | #32、#33 |
| 分类树 | 自有树交互 + Nuxt UI 基础控件 | 保留树的层级保护、键盘导航和异常节点表达；不得复制通用 Dialog/Button 行为 | #19、#35 |
| 现金流趋势、统计图表、日历布局 | 自有业务可视化 + 主题 token | 保留服务端统计语义和可访问文本降级，不引入重复图表组件库 | #28、#36 |

## Issue #31 路由与页面边界

工作台使用 Nuxt 文件路由提供 `/`、`/transactions`、`/accounts`、
`/categories`、`/statistics` 和 `/settings`。导航选中态、页面标题和后续
Breadcrumb 标签由同一份路由元数据生成；不再使用组件内部状态模拟页面。

总览只承担当前余额、当前月摘要、简短趋势、Top 分类、近期流水和首次使用引导；
统计分析承担时间筛选、比较、趋势、分类、Tag、日历和明细下钻。页面按需读取数据，
访问交易页不会同时请求六类统计接口。

交易筛选通过 `q`、`page`、`start`、`end`、`type`、`accountId`、
`categoryId`、`tagId` 和 `status` 保存；统计筛选通过 `preset`、`start`、
`end`、`granularity`、`month` 和 `parentCategoryId` 保存。默认值省略，非法或
重复参数回退并从地址中移除；弹窗、消息和表单草稿不写入 URL。完整浏览器验收见
[通用前端测试方案与指示](frontend-testing-plan.md)。

## Issue #33 代表性迁移

`frontend/app/components/ResourceEditor.vue` 现已使用：

- `UForm` 作为提交容器，保留名称为空和分类子树移动确认等现有业务校验；
- `UFormField` 提供统一 label、required 和字段关联；
- `UInput`、`USelect`、`UTextarea`、`UCheckbox` 替代原生字段控件；
- `UAlert` 表达保存失败，`UButton` 表达关闭和保存操作。

该迁移没有新增校验依赖，没有改变 POST/PATCH 路径或请求体，也没有迁移 `TransactionEditor.vue`。交易表单仍保留原实现，待后续业务页面组件化任务处理。

## 量化基线

测量对象为源码 CSS 和 Nuxt 生产构建客户端入口 CSS。构建命令必须在 `frontend` 目录使用 Bun 执行。

| 指标 | 迁移前 | Issue #33 后 | 说明 |
| --- | ---: | ---: | --- |
| `main.css` | 36,297 B / 86 行 | 36,421 B / 90 行 | 增加 Nuxt UI theme token 和字体 token |
| `mvp.css` | 8,971 B / 10 行 | 8,971 B / 10 行 | 未清理后续 #37 负责的历史样式 |
| 源码 CSS 合计 | 45,268 B / 96 行 | 45,392 B / 100 行 | 本 Issue 不以机械删除 CSS 为目标 |
| 生产客户端 CSS | 259.31 KB | 259.23 KB | `bun run build` 输出 |
| 生产客户端 CSS gzip | 37.30 KB | 37.29 KB | `bun run build` 输出 |
| 直接 UI 依赖 | `@nuxt/ui ^4.11.1` | `@nuxt/ui ^4.11.1` | 未新增组件库，`bun.lock` 未改动 |

可重复测量命令：

```bash
cd frontend
wc -c -l app/assets/css/main.css app/assets/css/mvp.css
bun run build
```

生产构建输出中的 `entry.*.css` 是客户端 CSS 体积依据。后续 #37 应在删除遗留通用 CSS 后再次记录同一组指标，不能把本次代表性迁移误报为全量 CSS 清理。

## 验收命令

```bash
cd frontend
bun run typecheck
bun run test
bun run build
bun run test:e2e --project=chromium-1280 keyboard-accessibility.spec.ts
bun run test:e2e:matrix
```

此外，文档改动需要串行执行 `make docs-check`、`make docs-build`，提交前执行根目录 `git diff --check`。完整 Chromium 矩阵必须三个 viewport 全部完成；单独重跑某个测试不能替代完整矩阵证据。
