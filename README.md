# PocketTally

Your money, clearly counted.

PocketTally 是一个面向个人、单用户和本地 SQLite 的小型记账应用。

当前 MVP 只支持由 PocketTally 应用写入数据库，不把手工 SQL、第三方数据库写入、多用户和企业级会计工作流作为当前设计目标。金额、余额、事务和作废记录的正确性仍是必须保留的核心约束。

## Documentation

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
