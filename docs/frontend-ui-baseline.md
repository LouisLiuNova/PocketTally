# Nuxt UI 接入基线与组件映射

本文记录 Issue #33 建立的 Nuxt UI 技术基础、组件采用边界和可重复的量化基线。
它服务于后续 Issue #25 的渐进式页面迁移，不代表所有业务页面已经完成重构。

## Issue #35 资源管理组件化

账户页使用 `UCard` 表达余额摘要和账户资源，使用 `UPageGrid` 保留响应式业务网格；流水和调账作为高频 `UButton` 直接展示，编辑与删除收纳到带资源名称的 `UDropdownMenu`。分类与标签页使用页面级 `UTabs` 切换支出分类、收入分类和标签，数量通过 badge 呈现且不写入 URL；标签集中在一个紧凑 `UCard` 列表中。已加载的空账户、空标签和空分类统一使用 `UEmpty`，分类异常链使用 `UAlert`。

`CategoryTree` 只接收显式的 `expense` 或 `income` 用途，不再自行维护用途 Tab。通用表面、输入、按钮和菜单分别由 `UCard`、`UInput`、`UButton` 与 `UDropdownMenu` 承担；自有 CSS 仅保留树缩进和连线、选中与异常节点、响应式“树 + 详情”布局，以及 roving tabindex、方向键、搜索祖先展开和异常链隔离所需的业务状态。窄屏回退为树在前、详情在后的单列，但不隐藏创建、编辑或删除能力。

资源编辑和删除仍复用既有 `ResourceEditor`、`ColorInput`、`UModal`、请求体及全局消息机制。创建分类由活动 Tab 注入固定用途，编辑时用途不可变；子树移动确认、非法父级过滤、删除冲突保留弹窗和服务端错误等规则没有改变。本次没有新增依赖，也没有修改 API、数据库、金额、时区、颜色字段或持久化语义；全局遗留 CSS 清理仍归 Issue #37。

## Issue #40 布局复用决策

Issue #40 统一的是页面容器、页面流和网格约束，不改变业务组件迁移边界。当前决策如下：

| 场景 | 复用能力 | 保留的自有实现与原因 |
| --- | --- | --- |
| 应用内容入口与宽度 | `UDashboardGroup`、`UDashboardSidebar`、`UDashboardPanel`、`UDashboardNavbar` 和 `UContainer` | #30 负责应用壳层、侧栏折叠与窄屏 Slideover；#40 只约束面板内部的内容宽度、页面流和业务网格 |
| 页面流与业务网格 | `UPageGrid` 或等价的 `page-grid` 作为语义化 Grid 入口，Tailwind/CSS 使用 `minmax(0, 1fr)`、`min-width: 0` 和命名 `grid-template-areas` | 每个页面的区域比例属于业务信息架构：总览的趋势/分类/近期流水和统计的趋势/分类/日历不能抽象成相同列数；分类页让分类树与详情组成主工作区，标签作为右侧次级资源区并与详情底边对齐，避免卡片漂移 |
| 交易筛选和账户卡 | Nuxt UI 按钮与现有输入控件，统一网格容器和断点 | 筛选项的 URL query 提交语义、账户卡操作语义属于 #31 与后续业务页面 Issue，不在本 Issue 重写为完整表单组件 |
| 分类树、现金流趋势、统计日历 | Nuxt UI 主题 token 与基础控件 | 分类树键盘导航、层级保护、异常节点表达和服务端统计降级文本是业务专属交互，保留自有布局避免组件替换造成语义回归 |
| 设置页 | `UCard`、`URadioGroup`、`UButton` 与共享页面流 | 外观设置使用独立卡片分组；八套配色按钮属于色板预览这一业务专属交互，保留局部布局和选中态 |

六个路由页面都放在同一个 `UDashboardPanel`/`UContainer` 内容约束内；页面内部统一使用 `page-flow` 间距，业务网格通过命名区域组织，并在中小视口回退为单列或双列。空态、加载态、错误态和长文本仍作为页面流子项参与相同的最小宽度约束。该布局重构不新增 CSS/UI/布局依赖，也不改变 API、URL query、金额、时区或退款语义。

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
| `.panel`、指标卡和资源卡片 | `UCard` | #35 已迁移账户、分类详情和标签资源；业务图表内部布局可继续局部实现 | #34、#35、#36 |
| 自有用途 Tab 和筛选 Tab | `UTabs` | #35 已迁移分类与标签页面级 Tab；其临时状态不写 URL，其他筛选仍按页面契约实施 | #31、#35、#36 |
| 自有分页按钮 | `UPagination` | 交易列表迁移时替换，保留服务端分页语义 | #34 |
| 应用壳层、侧边导航、Header、Breadcrumb | `UDashboardGroup`、`UDashboardSidebar`、`UDashboardPanel`、`UDashboardNavbar`、`UNavigationMenu`、`UBreadcrumb`、`UTooltip` | #30 已完成；页面标题、Breadcrumb 和选中态统一来自路由元数据，窄屏导航由 Sidebar 的 Slideover 模式提供 | #30 |
| 自有确认弹窗和详情弹层 | `UModal`、`USlideover`、`UPopover`、`UTooltip` | 已有 `UModal` 保留；详情抽屉和提示由业务页面任务决定 | #32、#34、#35 |
| `.error-box`、`.info-strip`、成功提示 | `UAlert`、`useToast` | 表单和服务端错误使用 `UAlert`；全局操作反馈由 #32 统一 | #32、#33 |
| 分类树 | 自有树交互 + `UCard`、`UInput`、`UButton`、`UDropdownMenu`、`UAlert`、`UEmpty` | #35 已迁移通用 UI；保留树的层级保护、键盘导航、搜索展开和异常节点表达 | #19、#35 |
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

## Issue #30 应用壳层

应用根节点使用 Nuxt UI Dashboard 组件组合，不再用自有 Sidebar/Header 网格和移动端底部导航模拟壳层：

- `UDashboardSidebar` 在宽屏提供可调整宽度和折叠的侧栏，折叠后由 `UNavigationMenu` 保留固定 Lucide 图标、可访问名称和 Tooltip；
- 小于 Nuxt UI `lg` 断点时，`UDashboardSidebar` 使用内建 Slideover，打开后约束焦点，并在真实路由切换后自动关闭；
- `UDashboardNavbar` 同时承载页面标题、由路由元数据生成的 `UBreadcrumb`，以及刷新和记账主操作；
- `UApp` 显式使用简体中文 locale，抽屉开关、关闭和折叠控件不会暴露英文或内部翻译键；
- 侧栏导航主体底部通过三档滑动轨道提供带系统、太阳、月亮图标的主题选择；控件位于账本状态分割线之前，切换会复用统一的外观偏好和本地持久化逻辑，并在侧栏收起后保留图标和可操作性；
- 侧栏与主要页面共享当前主题的页面背景、文字和边框 token，不再使用固定的反色导航表面；折叠按钮也使用主题 token 保持在明暗模式下可见。
- 侧栏底部通过 `UTooltip` 和 `UButton` 状态指示器展示“个人账本”“货币：CNY”“统计边界：Asia/Shanghai”；折叠时只保留图标，但鼠标、键盘和屏幕阅读器仍可取得完整语义。

## Issue #26 设置页

设置页是外观配置的唯一页面入口，顶栏不再提供重复的外观按钮。主题模式由 `URadioGroup` 提供“跟随系统”“亮色”“暗色”三个可访问选项；配色由 `APPEARANCE_PALETTES` registry 直接生成八个带名称、描述和双色色板预览的按钮，当前项同时使用 `aria-pressed`、描边、背景和勾选图标表达。

侧栏三档主题开关直接表示并修改 `system`、`light`、`dark` 偏好，用户可以在同一控件中恢复“跟随系统”；系统模式继续响应系统主题变化。所有变更即时更新 `data-theme`、`data-palette`、Nuxt UI class、`color-scheme` 和 `pockettally-appearance`，不新增后端接口或数据库字段。

壳层只消费 `APP_ROUTES` 的路径、标题、Breadcrumb 和 Lucide 图标映射，不接管交易或统计 query，也不改动页面业务请求。业务页面组件化、全局消息系统与遗留 CSS 全量清理由各自后续 Issue 负责。

## Issue #33 代表性迁移

`frontend/app/components/ResourceEditor.vue` 现已使用：

- `UForm` 作为提交容器，保留名称为空和分类子树移动确认等现有业务校验；
- `UFormField` 提供统一 label、required 和字段关联；
- `UInput`、`USelect`、`UTextarea`、`UCheckbox` 替代原生字段控件；
- `UAlert` 表达保存失败，`UButton` 表达关闭和保存操作。

该迁移没有新增校验依赖，没有改变 POST/PATCH 路径或请求体，也没有迁移 `TransactionEditor.vue`。交易表单仍保留原实现，待后续业务页面组件化任务处理。

## Issue #67 排版契约

Issue #67 在现有 Nuxt UI 与语义主题之上建立排版契约，不引入 Web Font、配色体系或新的 UI 框架。系统字体栈为 `ui-sans-serif`、平台无衬线字体、中文系统字体和 `system-ui` 回退；`Inter` 未在应用中加载，因此不再作为首选字体。

### 字阶与语义角色

字阶在 `frontend/app/assets/css/main.css` 的 Tailwind `@theme` 中定义，均使用 `rem`，并为每级配对无单位行高。`text-sm` 是 14px/约 22px 的业务正文初值；`text-xs` 是 12px/18px 的可读次级信息。页面标题、区块标题、指标数值和强调指标分别消费 `text-2xl` 至 `text-4xl`。金额、统计值和纵向比较日期保留 `tabular-nums`。

| 语义角色 | token | 用途 | 例外 |
| --- | --- | --- | --- |
| 正文 | `text-sm` | 页面说明、表格内容、表单反馈 | 无 |
| 次级信息 | `text-xs` | 标签、状态、元数据、辅助说明 | 不承担唯一业务含义 |
| 页面标题 | `text-2xl` | 应用壳层和设置页标题 | 仅按视口调整布局，不降级到任意字号 |
| 区块标题 | `text-xl` | 卡片、抽屉和工作区标题 | 保持现有语义标题层级 |
| 指标数值 | `text-3xl` / `text-4xl` | 金额、净额和详情金额 | 使用 `tabular-nums`，允许自然换行 |
| 图表刻度 | `--pt-type-chart` | 坐标轴刻度等非业务上下文 | 唯一允许的 11px 视觉例外，并必须有图例或数值上下文 |

### 页面与组件清单

- 应用壳层：日期、页面标题、Breadcrumb、导航、主题模式和账本状态统一消费字阶；静态账本状态不设置虚假 Tab 焦点。
- 总览、账户、交易和分类页：正文与次级信息最低为 12px；账户描述、分类名称、交易说明和错误反馈使用自然换行，不依赖固定高度或过早省略。
- 统计页：现金流图表仅将坐标轴刻度登记为小字例外；趋势明细、分类/Tag 表格、统计抽屉和日历说明使用可读次级信息。七列日历在 320px 下保留日期关系，横向滚动仅发生在日历容器内。
- 设置页：主题、配色、消息预览和选中状态使用相同字阶；配色名称可换行，八套 palette 与 Light/Dark/System 继续读取现有颜色 token。
- 通用交互：按钮、导航、Tab、表单、弹层、Toast、空态、加载态和错误态不改变原有语义；自定义交互目标至少为 24×24 CSS px，并在 `focus-visible`、disabled、loading 和错误态提供非颜色线索。

### 旧声明替换与边界

原有 13–14px 内容声明归入 `text-sm` 正文角色；12px 声明归入 `text-xs` 次级信息角色；18–28px 标题和指标声明分别收敛到 `text-lg` 至 `text-4xl`。原有负字距不再用于业务金额、标题或品牌文字。坐标轴刻度保留 `--pt-type-chart`，日历、交易、分类树、统计详情、表单反馈和错误信息不使用该例外。

遗留原型选择器和通用 CSS 的全量移除已在 Issue #37 完成；#67 负责排版以及由排版直接引发的换行、滚动和可读性布局问题。Issue #37 的组件边界、CSS 体积、依赖和完整矩阵证据见 [`docs/issue-37-frontend-acceptance.md`](issue-37-frontend-acceptance.md)。

### #67 浏览器验收

新增 `frontend/e2e/issue-67.spec.ts` 覆盖六个路由、320px 无页面级横向溢出、日历区域滚动边界、长分类名称、200% 缩放压力和排版 token；现有 `theme.spec.ts` 继续覆盖八套 palette 与 Light/Dark/System。完整 Chromium 三视口矩阵仍需与现有主题、壳层、键盘、业务和回归用例一起执行；自动化结果与真实浏览器观察分开报告。

## 量化基线

测量对象为源码 CSS 和 Nuxt 生产构建客户端入口 CSS。构建命令必须在 `frontend` 目录使用 Bun 执行。

| 指标 | 迁移前 | Issue #33 后 | 说明 |
| --- | ---: | ---: | --- |
| `main.css` | 36,297 B / 86 行 | 36,421 B / 90 行 | 增加 Nuxt UI theme token 和字体 token |
| `mvp.css` | 8,971 B / 10 行 | 8,971 B / 10 行 | Issue #33 时尚未清理的历史样式，当前 #37 结果见验收记录 |
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

生产构建输出中的 `entry.*.css` 是客户端 CSS 体积依据。Issue #37 已按同一口径重新测量，具体结果和日期快照见 [`docs/issue-37-frontend-acceptance.md`](issue-37-frontend-acceptance.md)。

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
