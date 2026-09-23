# 开发者文档

这里集中记录部署运维、贡献开发和技术契约。阅读产品操作请使用[用户文档](../user/index.md)。

## 部署与运维

- [部署与备份](deployment.md)：源码构建、反向代理、升级、备份与恢复。
- [认证与会话](authentication.md)：所有者初始化、密码维护、会话撤销及安全边界。

## 参与开发

- [开发者指南](developer-guide.md)：了解项目结构、质量检查和契约事实来源。
- [参与开发](development.md)：配置本地环境、启动前后端并构建文档站。
- [前端测试方案](frontend-testing-plan.md)：查看浏览器矩阵、运行策略和失败诊断方法。
- [主题契约](frontend-theme.md)：了解应用配色 token、主题模式和无障碍约束。

## 规则与接口

- [业务规则](business-rules.md)：交易、账户、分类、退款和统计的业务语义。
- [数据模型](data-models.md)：数据库表、字段和表间关系。
- [HTTP 模型](http-models.md)：API 读写模型与数据库字段映射。
- [接口契约](api-status.md)：设计契约与当前后端实现状态。
- [API 参考](api-reference/)：浏览 PocketTally OpenAPI 3.1 接口定义。

当前文档为 v0.2.0 发布预览，历史发布边界见 [v0.1.0 发行说明](../releases/v0.1.0.md)。
