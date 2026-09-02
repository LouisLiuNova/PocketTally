# HTTP 模型契约

这些契约使用 [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/schema)，属性名采用 camelCase 格式。

## 模型变体

- `*.read.schema.json`：完整的服务器响应。关系以有界摘要的形式嵌入，使客户端无需处理递归负载即可渲染常见视图。
- `*.create.schema.json`：创建请求体。关系使用 `...Id` 或 `...Ids`；不接受由服务器维护的 `id`、`createdAt` 和 `updatedAt` 字段。
- `*.update.schema.json`：部分更新请求体。至少需要提供一个属性；显式传入 `null` 会清除可为空的值。
- `common.schema.json`：共享的标量约束和有界关系摘要。

所有对象模型都会拒绝未知属性。数据库中可为空的列在读取模型中是必需的，并且明确标记为可为空，从而让响应保持稳定的结构。写入模型中的可选属性表示“保持未设置”；在数据库允许的情况下，`null` 表示“清除此值”。

## DB 到 HTTP 的关系映射

| 数据库列 | 读取模型 | 写入模型 |
| --- | --- | --- |
| `src_account_id` | `sourceAccount` | `sourceAccountId` |
| `dest_account_id` | `destinationAccount` | `destinationAccountId` |
| `amount_minor` | `amount`（CNY 元） | `amount`（CNY 元） |
| `category` | `category` | `categoryId` |
| `transaction_tags` 关联表 | `tags` | `tagIds` |
| `related_transaction_id` | `relatedTransaction` | `relatedTransactionId` |
| `parent_category_id` | `parentCategory` | `parentCategoryId` |

交易类型使用 `income`、`expense`、`transfer` 和 `balance_adjustment` 枚举；余额变更必须通过交易记录表达，账户更新接口不接受 `amount`。交易金额必须为有限正数，资金方向由应用层按交易类型处理。账户类型仅允许 `debit` 和 `credit`；`debit` 账户余额不得小于 0，`credit` 账户允许负余额。

`occurredAt` 表示交易实际发生时间，`createdAt` 表示服务器录入时间。金额使用 JSON 数字传输，服务端收到后立即转换为 `Decimal`，统一按 `ROUND_HALF_UP` 舍入到 CNY 分，并以 `INTEGER` 最小单位存储。系统固定使用 CNY，不在账户、交易或 HTTP 契约中保留 `currency` 字段；金额不会以 Python `float` 参与持久化或账务计算。

账户、分类和标签名称在单个账本内按 SQLite `NOCASE` 规则全局唯一；重复名称由数据库拒绝。`updatedAt` 由 DDL 触发器在业务字段或交易标签关系变化时维护。
