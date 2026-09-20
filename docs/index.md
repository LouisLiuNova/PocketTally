# PocketTally 文档

这里集中展示 PocketTally 的用户指南、开发者指南、数据结构、HTTP 模型、接口契约和业务规则。当前主线支持单所有者登录；页面由仓库中的契约文件自动构建，页尾版本信息可用于确认文档对应的代码提交。

v0.1.0 是首个发布版本和首个已发布的 SQLite 数据库基线，只支持个人单用户、本地或
可信内网使用。正式部署、备份和已知限制见 [v0.1.0 发行说明](releases/v0.1.0.md)。

> [!IMPORTANT]
> [接口实现状态](api-status.md)由契约与 FastAPI 当前路由自动比对生成，可用于确认每个接口的实现情况。

## 快速入口

| 内容 | 用途 |
| --- | --- |
| [用户指南](user-guide.md) | 从登录初始化、首笔记账到账本日常使用、退款、作废、备份和升级。 |
| [开发者指南](developer-guide.md) | 查看项目结构、开发环境、质量检查、契约和文档发布。 |
| [参与开发](development.md) | 查看本地启动、构建、质量检查和文档维护流程。 |
| [业务规则](business-rules.md) | 查看已生效、部分落地和待决策的账本规则。 |
| [通用前端测试方案与指示](frontend-testing-plan.md) | 查看前端基础检查、E2E、Chromium 桌面矩阵和验收标准。 |
| [前端语义主题与配色契约](frontend-theme.md) | 查看八套配色、亮暗模式、语义 token、对比度和扩展规则。 |
| [Docker Compose 部署](deployment.md) | 查看启动、HTTPS 反向代理、升级及 SQLite 备份恢复。 |
| [认证与会话](authentication.md) | 查看单所有者登录、会话边界、CSRF 和 CLI 恢复流程。 |
| [v0.1.0 发行说明](releases/v0.1.0.md) | 查看版本支持边界、已知限制、固定镜像部署和备份要求。 |
| [数据库模型](data-models.md) | 查看表、字段、约束说明和 ER 关系图。 |
| [HTTP 模型](http-models.md) | 按请求和响应模型查询字段。 |
| [接口实现状态](api-status.md) | 对照设计契约与 FastAPI 当前路由。 |
| [API 参考](api-reference/) | 浏览完整 OpenAPI 契约。 |

## 事实来源

- 业务语义以 `docs/business-rules.md` 中已确认的规则为准。
- 数据库结构以 `docs/contracts/db.dbml` 展示；SQLite 专属约束以 `backend/db/schema.sql` 为准。
- HTTP 模型以 `docs/contracts/models/*.schema.json` 为准。
- 设计接口以 `docs/contracts/apis/openapi.yaml` 为准。
- 已实现接口以 FastAPI 应用动态生成的 OpenAPI 为准。

文档版本信息会在构建时追加到页面底部；构建目录中的 `generated/version.md` 记录对应的 Git SHA 和生成时间。
