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
| `category` | `category` | `categoryId` |
| `tags` JSON IDs | `tags` | `tagIds` |
| `related_transaction_id` | `relatedTransaction` | `relatedTransactionId` |
| `parent_category_id` | `parentCategory` | `parentCategoryId` |

DBML 没有为账户类型或交易类型定义封闭集合，因此这些模式有意将它们校验为非空字符串，而不是臆造枚举。货币值仍保持为 JSON 数字，以匹配当前 SQLite 的 `REAL` 列；如果需要精确的十进制定点运算，应同时迁移存储方式和契约。
