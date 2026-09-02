-- SQLite authoritative DDL for the structure described in docs/contracts/db.dbml.
-- Foreign-key enforcement must be enabled per SQLite connection:
--   PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = ON;

CREATE TABLE categories (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT COLLATE NOCASE NOT NULL UNIQUE,
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
    type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer', 'balance_adjustment')),
    src_account_id TEXT NOT NULL,
    dest_account_id TEXT,
    amount_minor INTEGER NOT NULL
        CONSTRAINT ck_transactions_amount_positive CHECK (amount_minor > 0)
        CONSTRAINT ck_transactions_amount_minor_integer
        CHECK (typeof(amount_minor) = 'integer'),
    description TEXT,
    category TEXT NOT NULL,
    is_refund BOOLEAN NOT NULL DEFAULT 0,
    related_transaction_id TEXT,
    occurred_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (src_account_id) REFERENCES accounts (id),
    FOREIGN KEY (dest_account_id) REFERENCES accounts (id),
    FOREIGN KEY (related_transaction_id) REFERENCES transactions (id),
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
CREATE INDEX ix_transactions_related_transaction_id
    ON transactions (related_transaction_id);
CREATE INDEX ix_transactions_category
    ON transactions (category);
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
AFTER UPDATE OF name, description, parent_category_id, icon_color, icon_name ON categories
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
                is_refund, related_transaction_id, occurred_at ON transactions
FOR EACH ROW
BEGIN
    UPDATE transactions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

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
