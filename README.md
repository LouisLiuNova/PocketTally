# PocketTally

> 你的钱，清清楚楚。

PocketTally 是一款轻量、私有的个人记账应用。数据保存在你自己的 SQLite 账本中，适合在本机或可信内网使用。

## 主要功能

- 管理账户、分类和标签
- 记录收入、支出、转账、调账与退款
- 搜索和筛选交易，查看多维度收支统计
- 创建、校验和恢复账本备份

> [!WARNING]
> 当前版本没有登录功能，请勿将服务暴露到公网，也不要让其他程序直接修改数据库。

## 快速开始

需要预先安装 [Docker](https://docs.docker.com/get-docker/)。在项目目录运行：

```bash
cp .env.example .env
mkdir -p data backups
docker compose pull frontend backend
docker compose up -d --no-build
```

然后访问 `http://localhost:54425`。

首次使用建议依次完成：

1. 创建账户
2. 通过调账录入当前余额
3. 创建收入和支出分类
4. 开始记账

在保存真实数据前，请先按照[部署指南](https://louisliunova.github.io/PocketTally/deployment/)创建并校验备份。

## 文档

- [完整文档](https://louisliunova.github.io/PocketTally/)：使用边界、业务规则和技术参考
- [部署与备份](https://louisliunova.github.io/PocketTally/deployment/)：内网部署、升级、备份和恢复
- [发行说明](https://louisliunova.github.io/PocketTally/releases/v0.1.0/)：版本能力与已知限制
- [参与开发](https://louisliunova.github.io/PocketTally/development/)：本地开发、测试和文档维护

## 许可

PocketTally 使用 [MIT License](LICENSE)。
