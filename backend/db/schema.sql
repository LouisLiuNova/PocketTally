-- SQLite reference DDL corresponding to the runtime SQLModel schema.
-- Default categories are runtime initialization data and are intentionally not
-- represented by this structural reference DDL.
-- Foreign-key enforcement must be enabled per SQLite connection:
--   PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = ON;

CREATE TABLE categories (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT COLLATE NOCASE NOT NULL UNIQUE,
    purpose TEXT NOT NULL CHECK (purpose IN ('income', 'expense')),
    description TEXT,
    parent_category_id TEXT,
    icon_color TEXT NOT NULL DEFAULT '#ff0000',
    icon_name TEXT NOT NULL DEFAULT 'default_icon',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES categories (id)
);

CREATE TABLE accounts (
    id TEXT PRIMARY KEY NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('debit', 'credit')),
    name TEXT COLLATE NOCASE NOT NULL UNIQUE,
    card_number TEXT,
    description TEXT,
    amount_minor INTEGER NOT NULL DEFAULT 0
        CONSTRAINT ck_accounts_debit_amount_nonnegative
        CHECK (type = 'credit' OR amount_minor >= 0)
        CONSTRAINT ck_accounts_amount_minor_integer
        CHECK (typeof(amount_minor) = 'integer'),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT COLLATE NOCASE NOT NULL UNIQUE,
    description TEXT,
    color TEXT NOT NULL DEFAULT '#ff0000',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    id TEXT PRIMARY KEY NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer', 'balance_adjustment', 'expense_refund')),
    src_account_id TEXT,
    dest_account_id TEXT,
    amount_minor INTEGER NOT NULL
        CONSTRAINT ck_transactions_amount_positive CHECK (amount_minor > 0)
        CONSTRAINT ck_transactions_amount_minor_integer
        CHECK (typeof(amount_minor) = 'integer'),
    description TEXT,
    category TEXT,
    refund_of_transaction_id TEXT,
    balance_adjustment_direction TEXT
        CHECK (balance_adjustment_direction IN ('increase', 'decrease')),
    is_void BOOLEAN NOT NULL DEFAULT 0,
    voided_at DATETIME,
    occurred_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_transactions_balance_adjustment_direction CHECK (
        (type = 'balance_adjustment'
            AND balance_adjustment_direction IS NOT NULL
            AND balance_adjustment_direction IN ('increase', 'decrease'))
        OR
        (type <> 'balance_adjustment'
            AND balance_adjustment_direction IS NULL)
    ),
    CONSTRAINT ck_transactions_route CHECK (
        (type = 'income' AND src_account_id IS NULL
            AND dest_account_id IS NOT NULL AND category IS NOT NULL)
        OR (type IN ('expense', 'expense_refund') AND src_account_id IS NOT NULL
            AND dest_account_id IS NULL AND category IS NOT NULL)
        OR (type = 'transfer' AND src_account_id IS NOT NULL
            AND dest_account_id IS NOT NULL AND src_account_id <> dest_account_id
            AND category IS NULL)
        OR (type = 'balance_adjustment' AND src_account_id IS NOT NULL
            AND dest_account_id IS NULL AND category IS NULL)
    ),
    CONSTRAINT ck_transactions_refund_reference CHECK (
        (type = 'expense_refund' AND refund_of_transaction_id IS NOT NULL
            AND refund_of_transaction_id <> id)
        OR (type <> 'expense_refund' AND refund_of_transaction_id IS NULL)
    ),
    CONSTRAINT ck_transactions_void_state CHECK (
        (is_void = 0 AND voided_at IS NULL)
        OR (is_void = 1 AND voided_at IS NOT NULL)
    ),
    FOREIGN KEY (src_account_id) REFERENCES accounts (id),
    FOREIGN KEY (dest_account_id) REFERENCES accounts (id),
    FOREIGN KEY (refund_of_transaction_id) REFERENCES transactions (id),
    FOREIGN KEY (category) REFERENCES categories (id)
);

CREATE TABLE transaction_tags (
    transaction_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    PRIMARY KEY (transaction_id, tag_id),
    FOREIGN KEY (transaction_id) REFERENCES transactions (id),
    FOREIGN KEY (tag_id) REFERENCES tags (id)
);

CREATE INDEX ix_transactions_src_account_id
    ON transactions (src_account_id);
CREATE INDEX ix_transactions_dest_account_id
    ON transactions (dest_account_id);
CREATE INDEX ix_transactions_refund_of_transaction_id
    ON transactions (refund_of_transaction_id);
CREATE INDEX ix_transactions_occurred_at
    ON transactions (occurred_at);
CREATE INDEX ix_transactions_status_occurred_at
    ON transactions (is_void, occurred_at);
CREATE INDEX ix_transactions_src_occurred_at
    ON transactions (src_account_id, occurred_at);
CREATE INDEX ix_transactions_dest_occurred_at
    ON transactions (dest_account_id, occurred_at);
CREATE INDEX ix_transactions_category
    ON transactions (category);
CREATE INDEX ix_transactions_category_occurred_at
    ON transactions (category, occurred_at);
CREATE INDEX ix_transactions_type_status_refund_of
    ON transactions (type, is_void, refund_of_transaction_id);
CREATE INDEX ix_categories_parent_category_id
    ON categories (parent_category_id);
CREATE INDEX ix_transaction_tags_tag_id
    ON transaction_tags (tag_id);

-- SQLite has no ON UPDATE clause for column defaults. Keep response/audit
-- timestamps authoritative even when data is changed outside the ORM.
CREATE TRIGGER tr_accounts_updated_at
AFTER UPDATE OF type, name, card_number, description, amount_minor ON accounts
FOR EACH ROW
BEGIN
    UPDATE accounts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER tr_categories_updated_at
AFTER UPDATE OF name, purpose, description, parent_category_id, icon_color, icon_name ON categories
FOR EACH ROW
BEGIN
    UPDATE categories SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER tr_tags_updated_at
AFTER UPDATE OF name, description, color ON tags
FOR EACH ROW
BEGIN
    UPDATE tags SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER tr_transactions_updated_at
AFTER UPDATE OF type, src_account_id, dest_account_id, amount_minor, description, category,
                refund_of_transaction_id, balance_adjustment_direction,
                is_void, voided_at, occurred_at ON transactions
FOR EACH ROW
BEGIN
    UPDATE transactions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 余额投影仅由应用账本服务在交易事务中维护。
CREATE TRIGGER tr_transaction_tags_insert_updated_at
AFTER INSERT ON transaction_tags
FOR EACH ROW
BEGIN
    UPDATE transactions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.transaction_id;
END;

CREATE TRIGGER tr_transaction_tags_delete_updated_at
AFTER DELETE ON transaction_tags
FOR EACH ROW
BEGIN
    UPDATE transactions SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.transaction_id;
END;
-- 导入审计模型

CREATE TABLE import_batches (
	id VARCHAR NOT NULL,
	provider VARCHAR NOT NULL,
	filename VARCHAR NOT NULL,
	sha256 VARCHAR NOT NULL,
	parser_version VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	version INTEGER NOT NULL,
	summary JSON NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	committed_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT ck_import_batch_provider CHECK (provider IN ('alipay', 'wechat')),
	CONSTRAINT ck_import_batch_status CHECK (status IN ('draft', 'committed')),
	CONSTRAINT ck_import_batch_version CHECK (version > 0)
);

CREATE TABLE import_account_mappings (
	id VARCHAR NOT NULL,
	provider VARCHAR NOT NULL,
	payment_key VARCHAR NOT NULL,
	account_id VARCHAR NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_import_mapping UNIQUE (provider, payment_key),
	FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE CASCADE
);

CREATE TABLE import_rows (
	id VARCHAR NOT NULL,
	batch_id VARCHAR NOT NULL,
	row_number INTEGER NOT NULL,
	source_id VARCHAR NOT NULL,
	original JSON NOT NULL,
	state VARCHAR NOT NULL,
	reason VARCHAR,
	included BOOLEAN NOT NULL,
	transaction_type VARCHAR,
	amount_minor INTEGER NOT NULL,
	occurred_at DATETIME,
	description TEXT NOT NULL,
	payment_key VARCHAR NOT NULL,
	account_id VARCHAR,
	category_id VARCHAR,
	transaction_id VARCHAR,
	PRIMARY KEY (id),
	CONSTRAINT uq_import_row_number UNIQUE (batch_id, row_number),
	CONSTRAINT ck_import_row_amount CHECK (amount_minor >= 0),
	FOREIGN KEY(batch_id) REFERENCES import_batches (id),
	FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE SET NULL,
	FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL,
	FOREIGN KEY(transaction_id) REFERENCES transactions (id)
);

CREATE TABLE import_sources (
	id VARCHAR NOT NULL,
	provider VARCHAR NOT NULL,
	source_id VARCHAR NOT NULL,
	batch_id VARCHAR NOT NULL,
	row_id VARCHAR NOT NULL,
	transaction_id VARCHAR NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_import_source UNIQUE (provider, source_id),
	FOREIGN KEY(batch_id) REFERENCES import_batches (id),
	UNIQUE (row_id),
	FOREIGN KEY(row_id) REFERENCES import_rows (id),
	UNIQUE (transaction_id),
	FOREIGN KEY(transaction_id) REFERENCES transactions (id)
);

CREATE INDEX ix_import_rows_batch_id ON import_rows (batch_id);

CREATE INDEX ix_import_rows_source_id ON import_rows (source_id);
