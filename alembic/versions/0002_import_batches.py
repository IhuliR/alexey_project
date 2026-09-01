"""Add batch import tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002_import_batches'
down_revision: Union[str, Sequence[str], None] = '0001_django_schema_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'core_importbatch',
        sa.Column(
            'id',
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
        ),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('files_total', sa.Integer(), nullable=False),
        sa.Column('files_processed', sa.Integer(), nullable=False),
        sa.Column('files_failed', sa.Integer(), nullable=False),
        sa.Column('archive_path', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users_myuser.id'],
            name='core_importbatch_user_id_fk_users_myuser_id',
            deferrable=True,
            initially='DEFERRED',
        ),
    )
    op.create_index(
        'core_importbatch_user_id_idx',
        'core_importbatch',
        ['user_id'],
    )

    op.create_table(
        'core_importitem',
        sa.Column(
            'id',
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
        ),
        sa.Column('import_batch_id', sa.BigInteger(), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=True),
        sa.Column('error', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'],
            ['core_textdocument.id'],
            name='core_importitem_document_id_fk_core_textdocument_id',
            ondelete='SET NULL',
            deferrable=True,
            initially='DEFERRED',
        ),
        sa.ForeignKeyConstraint(
            ['import_batch_id'],
            ['core_importbatch.id'],
            name='core_importitem_import_batch_id_fk_core_importbatch_id',
            ondelete='CASCADE',
            deferrable=True,
            initially='DEFERRED',
        ),
    )
    op.create_index(
        'core_importitem_document_id_idx',
        'core_importitem',
        ['document_id'],
    )
    op.create_index(
        'core_importitem_import_batch_id_idx',
        'core_importitem',
        ['import_batch_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'core_importitem_import_batch_id_idx',
        table_name='core_importitem',
    )
    op.drop_index(
        'core_importitem_document_id_idx',
        table_name='core_importitem',
    )
    op.drop_table('core_importitem')
    op.drop_index(
        'core_importbatch_user_id_idx',
        table_name='core_importbatch',
    )
    op.drop_table('core_importbatch')
