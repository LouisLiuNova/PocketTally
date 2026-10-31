"""冻结结构迁移。"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
STATEMENTS = [
    "CREATE TABLE accounts (\n\tid TEXT NOT NULL, \n\ttype VARCHAR(6) NOT NULL, \n\tname TEXT COLLATE \"NOCASE\" NOT NULL, \n\tcard_number TEXT, \n\tdescription TEXT, \n\tamount_minor INTEGER DEFAULT 0 NOT NULL, \n\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_accounts_debit_amount_nonnegative CHECK (type = 'credit' OR amount_minor >= 0), \n\tCONSTRAINT ck_accounts_amount_minor_integer CHECK (typeof(amount_minor) = 'integer'), \n\tCONSTRAINT account_type CHECK (type IN ('debit', 'credit')), \n\tUNIQUE (name)\n)",
    "CREATE TABLE categories (\n\tid TEXT NOT NULL, \n\tname TEXT COLLATE \"NOCASE\" NOT NULL, \n\tpurpose VARCHAR(7) NOT NULL, \n\tdescription TEXT, \n\tparent_category_id VARCHAR, \n\ticon_color TEXT DEFAULT '#ff0000' NOT NULL, \n\ticon_name TEXT DEFAULT 'default_icon' NOT NULL, \n\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (name), \n\tCONSTRAINT category_purpose CHECK (purpose IN ('income', 'expense')), \n\tFOREIGN KEY(parent_category_id) REFERENCES categories (id)\n)",
    "CREATE TABLE tags (\n\tid TEXT NOT NULL, \n\tname TEXT COLLATE \"NOCASE\" NOT NULL, \n\tdescription TEXT, \n\tcolor TEXT DEFAULT '#ff0000' NOT NULL, \n\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (name)\n)",
    "CREATE TABLE transactions (\n\tid TEXT NOT NULL, \n\ttype VARCHAR(18) NOT NULL, \n\tsrc_account_id VARCHAR, \n\tdest_account_id VARCHAR, \n\tamount_minor INTEGER NOT NULL, \n\tdescription TEXT, \n\tcategory VARCHAR, \n\trefund_of_transaction_id VARCHAR, \n\tbalance_adjustment_direction VARCHAR(8), \n\tis_void BOOLEAN DEFAULT 0 NOT NULL, \n\tvoided_at DATETIME, \n\toccurred_at DATETIME NOT NULL, \n\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_transactions_amount_positive CHECK (amount_minor > 0), \n\tCONSTRAINT ck_transactions_amount_minor_integer CHECK (typeof(amount_minor) = 'integer'), \n\tCONSTRAINT ck_transactions_balance_adjustment_direction CHECK ((type = 'balance_adjustment' AND balance_adjustment_direction IS NOT NULL AND balance_adjustment_direction IN ('increase', 'decrease')) OR (type <> 'balance_adjustment' AND balance_adjustment_direction IS NULL)), \n\tCONSTRAINT ck_transactions_route CHECK ((type = 'income' AND src_account_id IS NULL AND dest_account_id IS NOT NULL AND category IS NOT NULL) OR (type IN ('expense', 'expense_refund') AND src_account_id IS NOT NULL AND dest_account_id IS NULL AND category IS NOT NULL) OR (type = 'transfer' AND src_account_id IS NOT NULL AND dest_account_id IS NOT NULL AND src_account_id <> dest_account_id AND category IS NULL) OR (type = 'balance_adjustment' AND src_account_id IS NOT NULL AND dest_account_id IS NULL AND category IS NULL)), \n\tCONSTRAINT ck_transactions_refund_reference CHECK ((type = 'expense_refund' AND refund_of_transaction_id IS NOT NULL AND refund_of_transaction_id <> id) OR (type <> 'expense_refund' AND refund_of_transaction_id IS NULL)), \n\tCONSTRAINT ck_transactions_void_state CHECK ((is_void = 0 AND voided_at IS NULL) OR (is_void = 1 AND voided_at IS NOT NULL)), \n\tCONSTRAINT transaction_type CHECK (type IN ('income', 'expense', 'expense_refund', 'transfer', 'balance_adjustment')), \n\tFOREIGN KEY(src_account_id) REFERENCES accounts (id), \n\tFOREIGN KEY(dest_account_id) REFERENCES accounts (id), \n\tFOREIGN KEY(category) REFERENCES categories (id), \n\tFOREIGN KEY(refund_of_transaction_id) REFERENCES transactions (id), \n\tCONSTRAINT balance_adjustment_direction CHECK (balance_adjustment_direction IN ('increase', 'decrease'))\n)",
    "CREATE TABLE transaction_tags (\n\ttransaction_id VARCHAR NOT NULL, \n\ttag_id VARCHAR NOT NULL, \n\tPRIMARY KEY (transaction_id, tag_id), \n\tFOREIGN KEY(transaction_id) REFERENCES transactions (id), \n\tFOREIGN KEY(tag_id) REFERENCES tags (id)\n)",
    "CREATE INDEX ix_categories_parent_category_id ON categories (parent_category_id)",
    "CREATE INDEX ix_transactions_category_occurred_at ON transactions (category, occurred_at)",
    "CREATE INDEX ix_transactions_src_account_id ON transactions (src_account_id)",
    "CREATE INDEX ix_transactions_category ON transactions (category)",
    "CREATE INDEX ix_transactions_type_status_refund_of ON transactions (type, is_void, refund_of_transaction_id)",
    "CREATE INDEX ix_transactions_status_occurred_at ON transactions (is_void, occurred_at)",
    "CREATE INDEX ix_transactions_src_occurred_at ON transactions (src_account_id, occurred_at)",
    "CREATE INDEX ix_transactions_occurred_at ON transactions (occurred_at)",
    "CREATE INDEX ix_transactions_refund_of_transaction_id ON transactions (refund_of_transaction_id)",
    "CREATE INDEX ix_transactions_dest_account_id ON transactions (dest_account_id)",
    "CREATE INDEX ix_transactions_dest_occurred_at ON transactions (dest_account_id, occurred_at)",
    "CREATE INDEX ix_transaction_tags_tag_id ON transaction_tags (tag_id)",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise RuntimeError("请停机恢复升级前备份，不执行破坏性降级")
