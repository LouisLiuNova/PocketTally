# Issue #36 前端重构验收记录

本次改造只调整 Nuxt 前端呈现与状态管理，不改变后端接口、数据库、OpenAPI、金额单位、时区或退款/作废语义。

## Nuxt UI 组件采用清单

- 总览：`UPageCard`、`UCard`、`UTable`、`UButton`、`UEmpty`、`UAlert`。
- 统计筛选：手动激活的 `UTabs`、`UFormField`、`UInput[type=date]`、`USelect`、`UButton`。
- 统计分析：`UCard`、`UTable`、`UEmpty`、`USkeleton`、`UAlert`。
- 下钻：`StatisticsDrillover` 使用右侧 `USlideover`，关闭后再打开交易详情，避免嵌套模态焦点陷阱。
- 指标：`MetricSummaryCard` 统一金额、同比文案、强调态和可访问结构。

## 业务 CSS 保留边界

仅保留现金流图表、日历热度、图表交互和主题 token 所需的业务局部 CSS；已移除两页旧统计网格、旧统计指标条、旧下钻面板和分类按钮布局。全仓 CSS 清理仍属于 Issue #37，不在本次范围内。

## 状态与兼容性证据

- 统计六个请求并发执行，全部成功后一次性提交快照；失败时保留上一完整快照并标明旧日期范围。
- 自定义日期草稿不写入 URL；规范化 query 支持刷新、前进/后退和直接访问。
- 无账户总览只显示首次使用引导；有账户无交易时保留工作区并按区域显示空状态。
- 交易详情、现金流日期下钻和分类交易 query 保持原有边界（开始日期包含、结束日期不含）。

详细命令结果以检查点提交及 PR 验证记录为准；#48 的生产 chunk 优化不在本提交处理。
