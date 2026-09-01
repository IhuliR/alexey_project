"""Add background export jobs."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003_export_jobs'
down_revision: Union[str, Sequence[str], None] = '0002_import_batches'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'core_exportjob',
        sa.Column(
            'id',
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
        ),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=True),
        sa.Column('format', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'],
            ['core_textdocument.id'],
            name='core_exportjob_document_id_fk_core_textdocument_id',
            ondelete='SET NULL',
            deferrable=True,
            initially='DEFERRED',
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users_myuser.id'],
            name='core_exportjob_user_id_fk_users_myuser_id',
            deferrable=True,
            initially='DEFERRED',
        ),
    )
    op.create_index(
        'core_exportjob_document_id_idx',
        'core_exportjob',
        ['document_id'],
    )
    op.create_index(
        'core_exportjob_user_id_idx',
        'core_exportjob',
        ['user_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'core_exportjob_user_id_idx',
        table_name='core_exportjob',
    )
    op.drop_index(
        'core_exportjob_document_id_idx',
        table_name='core_exportjob',
    )
    op.drop_table('core_exportjob')
