# PocketTally 开发文档

这里集中展示 PocketTally 当前的数据结构、HTTP 模型、接口契约和业务规则。页面由仓库中的契约文件自动构建，页尾版本信息可用于确认文档对应的代码提交。

v0.1.0 是首个发布版本和首个已发布的 SQLite 数据库基线，只支持个人单用户、本地或
可信内网使用。正式部署、备份和已知限制见 [v0.1.0 发行说明](releases/v0.1.0.md)。

> [!IMPORTANT]
> [接口实现状态](api-status.md)由契约与 FastAPI 当前路由自动比对生成，可用于确认每个接口的实现情况。

## 快速入口

| 内容 | 用途 |
| --- | --- |
| [参与开发](development.md) | 查看本地启动、构建、质量检查和文档维护流程。 |
| [业务规则](business-rules.md) | 查看已生效、部分落地和待决策的账本规则。 |
| [通用前端测试方案与指示](frontend-testing-plan.md) | 查看前端基础检查、E2E、Chromium 桌面矩阵和验收标准。 |
| [Nuxt UI 接入基线与组件映射](frontend-ui-baseline.md) | 查看 Issue #33 的组件映射、主题边界和 CSS/构建体积基线。 |
| [前端语义主题与配色契约](frontend-theme.md) | 查看八套配色、亮暗模式、语义 token、对比度和扩展规则。 |
| [Docker Compose 内网部署](deployment.md) | 查看内网启动、镜像发布、升级及 SQLite 备份恢复。 |
| [v0.1.0 发行说明](releases/v0.1.0.md) | 查看版本支持边界、已知限制、固定镜像部署和备份要求。 |
| [数据库模型](data-models.md) | 查看表、字段、约束说明和 ER 关系图。 |
| [HTTP 模型](http-models.md) | 按请求和响应模型查询字段。 |
| [接口实现状态](api-status.md) | 对照设计契约与 FastAPI 当前路由。 |
| [API 参考](api-reference.html) | 使用 Redoc 浏览完整 OpenAPI 契约。 |

## 事实来源

- 业务语义以 `docs/business-rules.md` 中已确认的规则为准。
- 数据库结构以 `docs/contracts/db.dbml` 展示；SQLite 专属约束以 `backend/db/schema.sql` 为准。
- HTTP 模型以 `docs/contracts/models/*.schema.json` 为准。
- 设计接口以 `docs/contracts/apis/openapi.yaml` 为准。
- 已实现接口以 FastAPI 应用动态生成的 OpenAPI 为准。

--8<-- "generated/version.md"
