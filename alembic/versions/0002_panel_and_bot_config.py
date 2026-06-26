from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '0002_panel_and_bot_config'
down_revision: str | None = '0001_initial'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'pasarguard_panels',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('base_url', sa.String(length=255), nullable=False),
        sa.Column('dashboard_url', sa.String(length=255), nullable=True),
        sa.Column('admin_username', sa.String(length=128), nullable=False),
        sa.Column('admin_secret', sa.Text(), nullable=False),
        sa.Column('default_role_id', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_pasarguard_panels_name', 'pasarguard_panels', ['name'], unique=True)
    op.create_index('ix_pasarguard_panels_is_active', 'pasarguard_panels', ['is_active'])

    op.create_table(
        'bot_config',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bot_token', sa.Text(), nullable=True),
        sa.Column('bot_username', sa.String(length=128), nullable=True),
        sa.Column('webhook_url', sa.String(length=512), nullable=True),
        sa.Column('webhook_secret', sa.String(length=128), nullable=True),
        sa.Column('webhook_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column('resellers', sa.Column('panel_id', sa.Integer(), nullable=True))
    op.create_index('ix_resellers_panel_id', 'resellers', ['panel_id'])
    op.create_foreign_key('fk_resellers_panel_id', 'resellers', 'pasarguard_panels', ['panel_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_resellers_panel_id', 'resellers', type_='foreignkey')
    op.drop_index('ix_resellers_panel_id', table_name='resellers')
    op.drop_column('resellers', 'panel_id')
    op.drop_table('bot_config')
    op.drop_table('pasarguard_panels')
