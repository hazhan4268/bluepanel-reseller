from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'resellers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(length=128), nullable=True),
        sa.Column('pasar_admin_id', sa.Integer(), nullable=True),
        sa.Column('pasar_username', sa.String(length=64), nullable=False),
        sa.Column('pasar_role_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('balance_toman', sa.BigInteger(), nullable=False),
        sa.Column('price_per_gb_toman', sa.Integer(), nullable=False),
        sa.Column('debt_limit_toman', sa.Integer(), nullable=False),
        sa.Column('last_total_usage_bytes', sa.BigInteger(), nullable=False),
        sa.Column('low_balance_alert_sent', sa.Boolean(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_resellers_telegram_id', 'resellers', ['telegram_id'], unique=True)
    op.create_index('ix_resellers_pasar_username', 'resellers', ['pasar_username'], unique=True)
    op.create_index('ix_resellers_pasar_admin_id', 'resellers', ['pasar_admin_id'])
    op.create_index('ix_resellers_status', 'resellers', ['status'])

    op.create_table(
        'wallet_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('reseller_id', sa.Integer(), sa.ForeignKey('resellers.id'), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('amount_toman', sa.BigInteger(), nullable=False),
        sa.Column('balance_before_toman', sa.BigInteger(), nullable=False),
        sa.Column('balance_after_toman', sa.BigInteger(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_wallet_transactions_reseller_id', 'wallet_transactions', ['reseller_id'])
    op.create_index('ix_wallet_transactions_type', 'wallet_transactions', ['type'])

    op.create_table(
        'usage_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('reseller_id', sa.Integer(), sa.ForeignKey('resellers.id'), nullable=False),
        sa.Column('old_usage_bytes', sa.BigInteger(), nullable=False),
        sa.Column('total_usage_bytes', sa.BigInteger(), nullable=False),
        sa.Column('delta_usage_bytes', sa.BigInteger(), nullable=False),
        sa.Column('cost_toman', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_usage_snapshots_reseller_id', 'usage_snapshots', ['reseller_id'])


def downgrade() -> None:
    op.drop_table('usage_snapshots')
    op.drop_table('wallet_transactions')
    op.drop_table('resellers')
