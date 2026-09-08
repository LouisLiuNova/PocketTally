# PocketTally

Your money, clearly counted.

PocketTally 是一个面向个人、单用户和本地 SQLite 的小型记账应用。

当前 MVP 只支持由 PocketTally 应用写入数据库，不把手工 SQL、第三方数据库写入、多用户和企业级会计工作流作为当前设计目标。金额、余额、事务和作废记录的正确性仍是必须保留的核心约束。

## 启动端到端 MVP

前端使用 Bun 1.3.13，后端使用 Python 3.14 和 uv。分别打开两个终端：

```bash
cd backend
uv sync
uv run pocket-tally-backend
```

```bash
cd frontend
bun install --frozen-lockfile
bun run dev
```

访问 `http://localhost:3000`。前端通过同源 `/api/v1` 代理访问 `http://127.0.0.1:8000`；后端地址不同时，在启动前端时设置 `NUXT_API_BASE`。后端默认持久化到 `backend/data/pocket-tally.sqlite3`，可通过 `POCKET_TALLY_DATABASE_PATH` 指定其他账本。

首次使用：创建账户 → 使用调账录入现有余额 → 创建收入/支出分类 → 记账。前端支持资源增删改、交易搜索筛选、收支/转账/调账、编辑、退款和作废；统计按服务端 `Asia/Shanghai` 日期边界归属月份，退款抵减支出，转账和调账不参与收支统计。

生产构建和启动同样使用 Bun（需保持后端服务运行）：

```bash
cd frontend
bun run build
bun run preview
```

当前适用于单用户本地运行，未加入登录鉴权。交易列表、退款摘要和统计均由后端按条件分页/聚合；`GET /api/v1/transactions` 已升级为 `{items,total,page,pageSize}`，前端接入请按 Issue #14 切换，不能继续依赖旧的全量数组或 `includeVoided`。

## 验证

```bash
cd frontend
bun run typecheck
bun run test
# 首次执行需安装浏览器；Linux 还需 Chromium 系统依赖。
bun --bun playwright install chromium
bun run test:e2e
```

端到端测试自动在 8012/3012 端口启动真实后端和 Bun 前端，使用 `frontend/.data/e2e.sqlite3` 独立测试账本，不使用默认个人账本。每次使用唯一资源名称，可重复执行。测试覆盖资源创建、调账、收支、编辑、退款限额、作废退款、转账、余额持久化、引用资源删除保护和移动端布局。

```bash
cd backend
uv run pytest -q
uvx ruff check .
uv run --group docs python ../scripts/docs.py check
```

## 文档

- [在线开发文档](https://louisliunova.github.io/PocketTally/)
- [业务规则](docs/business-rules.md)
- [待办事项](TODO.md)
- [历史方案与决策背景](TODO-IMP.md)

文档站集中展示数据库模型、HTTP 模型、接口契约及当前实现状态。安装固定版本的文档依赖后，可以在本地检查、构建或预览：

```bash
make docs-install
make docs-check
make docs-build
make docs-serve
```

本地预览地址为 `http://127.0.0.1:8001/`。发布到 GitHub Pages 后使用 `/PocketTally/` 项目路径。生成文件位于 `.docs-build/` 和 `site/`，不会提交到仓库。
