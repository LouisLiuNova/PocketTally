# PocketTally 后端

这是使用 `uv` 管理、基于 Python 3.14 的 FastAPI 服务。

## 启动

```bash
uv sync
uv run pocket-tally-backend
```

API 文档位于 <http://127.0.0.1:8000/docs>，健康检查端点为
`GET /api/v1/health`。

如需覆盖配置，将 `.env.example` 复制为 `.env`。所有环境变量均使用
`POCKET_TALLY_` 前缀。数据库默认创建于启动工作目录下的
`data/pocket-tally.sqlite3`，可通过 `POCKET_TALLY_DATABASE_PATH` 指定其他
绝对或相对路径。应用会自动创建父目录和数据表，并为每个 SQLite 连接启用外键。

当前开发阶段不自动升级旧数据库。如果启动时报出旧余额触发器，请切换到新的
开发数据库；应用不会删除或改写旧数据。

## 测试

```bash
uv run pytest
```

Engine 在 `lifespan.py` 中初始化并保存到 `app.state.resources`。路由通过
`dependencies.py` 中的 `SessionDep` 获得请求独占 Session：处理成功时提交，
发生异常或提交失败时回滚。账本服务只执行写入与 `flush`，不自行提交事务。
