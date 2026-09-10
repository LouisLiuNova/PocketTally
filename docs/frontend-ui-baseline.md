# Nuxt UI 接入基线与组件映射

本文记录 Issue #33 建立的 Nuxt UI 技术基础、组件采用边界和可重复的量化基线。
它服务于后续 Issue #25 的渐进式页面迁移，不代表所有业务页面已经完成重构。

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
| 自有用途 Tab 和筛选 Tab | `UTabs` | 信息架构和 URL query 先由 #31 确定 | #31、#35、#36 |
| 自有分页按钮 | `UPagination` | 交易列表迁移时替换，保留服务端分页语义 | #34 |
| 自有侧边导航、Header、Breadcrumb | `USidebar`/`UDashboardSidebar`、`UHeader`、`UBreadcrumb` | 应用壳层统一改造，不在 #33 提前重写 | #30 |
| 自有确认弹窗和详情弹层 | `UModal`、`USlideover`、`UPopover`、`UTooltip` | 已有 `UModal` 保留；详情抽屉和提示由业务页面任务决定 | #32、#34、#35 |
| `.error-box`、`.info-strip`、成功提示 | `UAlert`、`useToast` | 表单和服务端错误使用 `UAlert`；全局操作反馈由 #32 统一 | #32、#33 |
| 分类树 | 自有树交互 + Nuxt UI 基础控件 | 保留树的层级保护、键盘导航和异常节点表达；不得复制通用 Dialog/Button 行为 | #19、#35 |
| 现金流趋势、统计图表、日历布局 | 自有业务可视化 + 主题 token | 保留服务端统计语义和可访问文本降级，不引入重复图表组件库 | #28、#36 |

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
