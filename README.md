# PocketTally

> 你的钱，清清楚楚。

PocketTally 是一款轻量、私有的个人记账应用，帮助你记录每笔收支、核对账户余额，并看清钱花在了哪里。适合希望自行管理个人账本的单个使用者。

![使用演示数据的 PocketTally 总览页面](docs/assets/issue-43/after/overview-ruri.png)

## 主要能力

- 管理账户、收支分类和标签，记录收入、支出、转账及余额调整。
- 搜索交易，查看收支趋势、分类构成和日历统计。
- 编辑或作废错误记录，从原支出发起退款。
- 通过受支持的备份流程保护账本数据。

## 开始使用

PocketTally 面向单个账本所有者，需要自行部署。开始保存真实数据前，请先阅读[部署与备份指南](docs/developer/deployment.md)并完成安全配置与备份校验。部署完成后，按[用户文档](docs/user/index.md)创建账户、录入当前余额，再记录第一笔交易。

> [!NOTE]
> 本分支展示 **v0.2.0 发布预览**，可阅读[发行说明草稿](docs/releases/v0.2.0.md)；当前公开发行版仍为 [v0.1.0](https://github.com/LouisLiuNova/PocketTally/releases/tag/v0.1.0)。请勿将预览文档中的流程用于 v0.1.0 镜像。当前发行版的能力与部署限制以[其发行说明](https://louisliunova.github.io/PocketTally/releases/v0.1.0/)为准。

## 文档与参与开发

- [文档站](https://louisliunova.github.io/PocketTally/)：从使用或开发者入口开始。
- [用户文档](docs/user/index.md)：日常记账、查询、纠错和常见问题。
- [开发者文档](docs/developer/index.md)：部署运维、开发流程、测试和 API 契约。
- [参与开发](docs/development.md)：本地环境、质量检查和文档维护。

欢迎通过 [GitHub Issues](https://github.com/LouisLiuNova/PocketTally/issues) 反馈问题或提出建议。

## 许可

PocketTally 使用 [MIT License](LICENSE)。
