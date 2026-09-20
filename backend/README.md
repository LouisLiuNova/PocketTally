# PocketTally 后端

这是使用 `uv` 管理、基于 Python 3.14 的 FastAPI 服务。

## 启动

```bash
uv sync
uv run pocket-tally-backend
```

API 文档位于 <http://127.0.0.1:8000/docs>，健康检查端点为
`GET /api/v1/health`。

生产环境会关闭 `/docs`、`/redoc` 和 `/openapi.json`。账本资源默认需要单所有者会话；
首次启动后使用 `pocket-tally-auth init --username <用户名>` 初始化，忘记密码使用
`pocket-tally-auth reset-password`，这两个命令都只操作独立的鉴权 SQLite 文件。

当前运行时已提供账户、树状分类和标签的创建、列表、详情、更新与删除接口，
交易 CRUD、退款摘要、组合筛选分页和六类服务端统计接口。交易列表返回
`{items,total,page,pageSize}`，使用 `status=active|voided|all` 控制作废状态；统计和
消费下钻使用整数分字段。请求模型使用 camelCase；校验失败、不存在和冲突分别返回
`422`、`404` 和 `409`，错误体统一为 `{code, message, details?}`。基础资源仅在未被
历史交易、子分类或关联表引用时允许物理删除。

所有写入时间与交易查询时间必须包含 `Z` 或 UTC 偏移，服务端统一按 UTC 保存和输出；
统计日期边界固定为 `Asia/Shanghai` 的左闭右开自然日。

如需覆盖配置，将 `.env.example` 复制为 `.env`。所有环境变量均使用
`POCKET_TALLY_` 前缀。数据库默认创建于启动工作目录下的
`data/pocket-tally.sqlite3`，可通过 `POCKET_TALLY_DATABASE_PATH` 指定其他
绝对或相对路径。应用会自动创建父目录和数据表，为每个 SQLite 连接启用外键，并为
已有账本幂等补建不改变数据的必要统计索引。全新数据库会在同一个初始化事务中创建
5 个收入分类和 12 个支出分类；已经存在 PocketTally 业务表的数据库不会自动补种，
即使其中的分类为空也保持不变。

生产鉴权必须同时设置 `POCKET_TALLY_PUBLIC_ORIGIN=https://<实际域名>`，并让 FastAPI
只接受可信反向代理的内部转发；账本备份工具不会包含鉴权库。

当前开发阶段不自动升级旧数据库。如果启动时报出旧余额触发器，请切换到新的
开发数据库；应用不会删除或改写旧数据。

## 测试

```bash
uv run pytest
uv run pytest -q -s benchmarks/test_statistics_performance.py
```

默认 pytest 包含 100,000 笔账本的单轮正确性回归；独立性能命令在预热后对八个接口
各测量 20 次，并以 p95 不超过 1 秒为通过条件。测量环境和最近结果记录在
`docs/statistics-performance.md`。

Engine 在 `lifespan.py` 中初始化并保存到 `app.state.resources`。路由通过
`dependencies.py` 中的 `SessionDep` 获得请求独占 Session：处理成功时提交，
发生异常或提交失败时回滚。账本服务只执行写入与 `flush`，不自行提交事务。

## Pydantic 兼容范围

当前后端支持 Pydantic `>=2.0,<3.0`；锁定环境当前使用 Pydantic 2.13.4。
HTTP 模型使用 Pydantic 2 的 `field_serializer` 序列化时间，避免使用已弃用的
`json_encoders`，并保持 UTC `Z` 时间、Decimal 金额 JSON number 和 camelCase
字段别名不变。

升级到 Pydantic 3 前仍需确认 FastAPI、pydantic-settings 及其生态依赖的正式兼容
版本，并重新运行完整 pytest、运行时/静态 OpenAPI 对照和 JSON Schema 检查；在这些
依赖发布兼容版本前，`<3.0` 上限是有意保留的阻断项。
