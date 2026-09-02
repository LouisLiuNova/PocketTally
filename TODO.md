# PocketTally 待办事项

> [!NOTE]
> 本文件是待办事项的唯一清单。`TODO-IMP.md` 仅保留历史讨论和实施背景；同一问题以本文件的描述为准。

## 已完成

- [x] 将交易类型限制为 `income`、`expense`、`transfer` 和 `balance_adjustment`，并要求交易金额为有限正数。
- [x] 要求创建交易提供 `occurred_at`，并在交易读取结果中返回；文档区分 `occurredAt`、`createdAt` 和 `updatedAt`。
- [x] 将交易标签从 `transactions.tags` JSON 字段规范化为 `transaction_tags` 关联表，使用复合主键和外键约束。
- [x] 在 ORM 与 SQLite DDL 中统一账户、分类和标签名称的 `NOCASE` 唯一性。
- [x] 在 ORM 和 SQLite DDL 中统一服务器默认值，并通过更新触发器维护 `updated_at`。
- [x] 禁止账户 PATCH 直接修改余额；余额调整使用 `balance_adjustment` 交易类型表达。

## P1：核心账本规则

- [x] 在 HTTP Schema、ORM 和数据库约束中统一交易类型枚举，并要求交易金额为有限正数。
- [x] 在交易创建和读取契约中支持 `occurred_at`，区分实际发生时间与录入、更新时间。
- [x] 在账户更新 Schema 中禁止修改 `amount`，并保留通过 `balance_adjustment` 交易表达调账的约束。
- [x] 确定账户类型为 `debit`、`credit`，并在 HTTP Schema、ORM 和数据库约束中统一校验；`debit` 账户余额不得小于 0。
- [ ] 统一交易路由和分类约束：收入、支出、转账与 `balance_adjustment` 必须具有合法的来源账户、目标账户和分类组合；转账账户不得相同且不得计入收支分类。创建、部分更新、导入和直接数据库写入应遵守同一组规则。
- [ ] 确定分类用途是否严格区分 `income` 与 `expense`，以及父子分类是否必须用途一致；随后同步 HTTP Schema、ORM、数据库约束和报表口径。
- [ ] 完成退款、冲正和交易修订规则：退款必须关联有效原交易，不得自引用或形成关系循环，累计有效退款不得超过原金额，并沿原资金路径退回；同时确定收入退款范围、退款与冲正关系字段、已入账交易能否原地修改。
- [ ] 确定余额的长期权威来源，并在交易创建、修改、作废、退款、冲正和转账时原子维护余额；`balance_adjustment` 必须保留可审计记录。

## P1：数据与迁移

- [x] 将交易标签从 JSON 字段规范化为 `transaction_tags` 关联表，并在 ORM 与 SQLite DDL 中统一名称唯一性、默认值和 `updated_at` 自动维护。
- [x] 将金额从 SQLite `REAL` 和浮点数迁移为 CNY 最小单位整数；HTTP 数字在服务端转换为 `Decimal`，统一使用 `ROUND_HALF_UP` 舍入，不显式指定或保存币种字段。
- [ ] 建立版本化数据库迁移和回滚机制；迁移前覆盖历史标签拆分、非法或重复标签、缺失标签、历史 `occurred_at` 回填及旧交易字段组合清理，并保证每个运行时连接启用外键约束。

## P2：生命周期与报表

- [ ] 定义交易生命周期和时间语义：区分发生、录入、入账、修改、作废与冲正时间，并明确各状态允许修改的字段。
- [ ] 定义拆分交易、分类树聚合和退款抵减后的报表归属；转账不得计入收入或支出。

## MVP 后续功能

- [ ] 增加用户鉴权、资源所有权与数据隔离；该功能不属于当前 MVP 范围。

> [!IMPORTANT]
> 账户余额不可通过账户 PATCH 直接修改。调账必须创建 `balance_adjustment` 类型交易，以保留完整审计轨迹。
