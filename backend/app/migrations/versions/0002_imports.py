"""冻结结构迁移。"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None
STATEMENTS = [
    "CREATE TABLE import_batches (\n\tid VARCHAR NOT NULL, \n\tprovider VARCHAR NOT NULL, \n\tfilename VARCHAR NOT NULL, \n\tsha256 VARCHAR NOT NULL, \n\tparser_version VARCHAR NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\tversion INTEGER NOT NULL, \n\tsummary JSON NOT NULL, \n\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tcommitted_at DATETIME, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_import_batch_provider CHECK (provider IN ('alipay', 'wechat')), \n\tCONSTRAINT ck_import_batch_status CHECK (status IN ('draft', 'committed')), \n\tCONSTRAINT ck_import_batch_version CHECK (version > 0)\n)",
    "CREATE TABLE import_account_mappings (\n\tid VARCHAR NOT NULL, \n\tprovider VARCHAR NOT NULL, \n\tpayment_key VARCHAR NOT NULL, \n\taccount_id VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_import_mapping UNIQUE (provider, payment_key), \n\tFOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE CASCADE\n)",
    "CREATE TABLE import_rows (\n\tid VARCHAR NOT NULL, \n\tbatch_id VARCHAR NOT NULL, \n\trow_number INTEGER NOT NULL, \n\tsource_id VARCHAR NOT NULL, \n\toriginal JSON NOT NULL, \n\tstate VARCHAR NOT NULL, \n\treason VARCHAR, \n\tincluded BOOLEAN NOT NULL, \n\ttransaction_type VARCHAR, \n\tamount_minor INTEGER NOT NULL, \n\toccurred_at DATETIME, \n\tdescription TEXT NOT NULL, \n\tpayment_key VARCHAR NOT NULL, \n\taccount_id VARCHAR, \n\tcategory_id VARCHAR, \n\ttransaction_id VARCHAR, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_import_row_number UNIQUE (batch_id, row_number), \n\tCONSTRAINT ck_import_row_amount CHECK (amount_minor >= 0), \n\tFOREIGN KEY(batch_id) REFERENCES import_batches (id), \n\tFOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE SET NULL, \n\tFOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL, \n\tFOREIGN KEY(transaction_id) REFERENCES transactions (id)\n)",
    "CREATE TABLE import_sources (\n\tid VARCHAR NOT NULL, \n\tprovider VARCHAR NOT NULL, \n\tsource_id VARCHAR NOT NULL, \n\tbatch_id VARCHAR NOT NULL, \n\trow_id VARCHAR NOT NULL, \n\ttransaction_id VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_import_source UNIQUE (provider, source_id), \n\tFOREIGN KEY(batch_id) REFERENCES import_batches (id), \n\tUNIQUE (row_id), \n\tFOREIGN KEY(row_id) REFERENCES import_rows (id), \n\tUNIQUE (transaction_id), \n\tFOREIGN KEY(transaction_id) REFERENCES transactions (id)\n)",
    "CREATE INDEX ix_import_rows_batch_id ON import_rows (batch_id)",
    "CREATE INDEX ix_import_rows_source_id ON import_rows (source_id)",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise RuntimeError("请停机恢复升级前备份，不执行破坏性降级")
