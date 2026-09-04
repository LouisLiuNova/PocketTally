# PocketTally 开发文档

这里集中展示 PocketTally 当前的数据结构、HTTP 模型、接口契约和业务规则。页面由仓库中的契约文件自动构建，页尾版本信息可用于确认文档对应的代码提交。

> [!IMPORTANT]
> 接口契约包含尚未实现的设计。请先查看[接口实现状态](api-status.md)，再判断接口当前是否可以调用。

## 快速入口

| 内容 | 用途 |
| --- | --- |
| [业务规则](business-rules.md) | 查看已生效、部分落地和待决策的账本规则。 |
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
