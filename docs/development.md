# 参与开发

本页记录 PocketTally 的本地开发、构建和质量检查流程。普通使用者只需阅读
[Docker Compose 内网部署](deployment.md)。

## 环境要求

- 前端：[Bun](https://bun.sh/) 1.3.13
- 后端：[Python](https://www.python.org/) 3.14 与 [uv](https://docs.astral.sh/uv/)

## 本地启动

分别打开两个终端。

启动后端：

```bash
cd backend
uv sync
uv run pocket-tally-backend
```

启动前端：

```bash
cd frontend
bun install --frozen-lockfile
bun run dev
```

访问 `http://localhost:3000`。前端默认通过同源 `/api/v1` 代理访问
`http://127.0.0.1:8000`；后端地址不同时，通过 `NUXT_API_BASE` 覆盖。
`bun run dev` 会显式使用 Bun runtime 启动 Nuxt 开发服务器，确保本地开发与浏览器验收
使用与项目锁定版本一致的 Bun 运行时。

后端默认将数据保存到 `backend/data/pocket-tally.sqlite3`。需要使用其他开发账本时，
设置 `POCKET_TALLY_DATABASE_PATH`。请勿使用个人正式账本进行开发或测试。

## 构建前端

后端服务保持运行时，执行：

```bash
cd frontend
bun run build
bun run preview
```

## 质量检查

前端基础检查：

```bash
cd frontend
bun run typecheck
bun run test
```

后端测试、代码检查与契约检查：

```bash
cd backend
uv run pytest -q
uvx ruff check .
uv run --group docs python ../scripts/docs.py check
```

提交到 `main` 的 Pull Request 或向 `main` push 时，`containers.yml` 会分别运行
`backend-quality`、`frontend-quality` 和 `development-smoke`，之后才运行两个平台的
Compose smoke。前端 `typecheck`、单元测试和生产构建不会与后端检查混在同一个 job 中。
`e2e.yml` 另行运行 `Chromium E2E`，使用隔离 SQLite 账本执行 1280、1440、1920 三档
完整矩阵；它不在版本 tag 上运行。CI 的 required checks 是否已配置，需在实际 PR 上以仓库
分支保护设置为准。

提交前还应在项目根目录执行：

```bash
git diff --check
```

完整的 Chromium 桌面测试矩阵、隔离账本机制、调试命令和验收标准见
[通用前端测试方案与指示](frontend-testing-plan.md)。十万笔账本的统计性能门禁见
[十万笔统计性能验收](statistics-performance.md)。

## 文档

文档站使用独立的 Fumadocs 应用，从仓库内的业务规则、数据模型和接口契约构建。安装依赖后，可以在项目根目录执行：

```bash
make docs-install
make docs-check
make docs-build
make docs-serve
```

本地预览地址为 `http://127.0.0.1:8001/`。生成内容位于 `docs-site/.generated-content/` 和
`docs-site/out/`，不提交到仓库。Next.js 静态构建使用 Node.js 20.9 或更高版本，JavaScript
依赖仍由 Bun 安装和锁定。

不同信息的事实来源与同步要求见[文档首页](index.md)和[业务规则](business-rules.md)。
