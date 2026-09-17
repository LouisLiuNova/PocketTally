# 开发者指南

本指南面向需要修改 PocketTally、维护契约或发布文档站的开发者。

## 快速开始

准备 Bun 1.3.13、Python 3.14 和 uv。前后端本地启动、环境变量与开发账本说明见[参与开发](development.md)。

## 项目结构

| 目录 | 职责 |
| --- | --- |
| `frontend/` | Nuxt 4 主产品前端和浏览器验收 |
| `backend/` | FastAPI、SQLite、业务服务和后端测试 |
| `docs/` | 中文文档、业务规则和契约事实来源 |
| `docs-site/` | Fumadocs 静态文档应用 |
| `scripts/docs.py` | 契约检查、派生页面和文档构建输入生成 |

## 质量检查

- 前端：`bun run typecheck`、`bun run test`、`bun run build`。
- 后端：`uv run pytest -q`、`uvx ruff check .`。
- 文档：`make docs-check`、`make docs-build`、`git diff --check`。

前端浏览器矩阵和失败诊断见[通用前端测试方案与指示](frontend-testing-plan.md)。

## 契约与事实来源

业务语义以 `docs/business-rules.md` 为准，数据库结构以 `docs/contracts/db.dbml` 和 `backend/db/schema.sql` 为准，HTTP 模型以 `docs/contracts/models/*.schema.json` 为准，设计接口以 `docs/contracts/apis/openapi.yaml` 为准。跨层字段变更必须同步运行时模型、静态契约、生成页面和测试。

构建时会自动生成数据库模型、HTTP 模型、接口实现状态、API 参考和版本信息；不要手工编辑 `docs-site/.generated-content/`。

## 发布文档站

本地预览使用 `make docs-serve`，生产构建使用 `make docs-build`。Pull Request 只执行检查，`main` 推送后由 GitHub Actions 生成静态产物并部署到 GitHub Pages。
