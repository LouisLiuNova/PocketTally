-- SQLite DDL generated from docs/contracts/db.dbml.
-- Foreign-key enforcement must be enabled per SQLite connection:
--   PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = ON;

CREATE TABLE categories (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
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
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    card_number TEXT,
    description TEXT,
    amount REAL NOT NULL DEFAULT 0.0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
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
    amount REAL NOT NULL CHECK (amount <> 0),
    description TEXT,
    category TEXT NOT NULL,
    tags TEXT,
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
