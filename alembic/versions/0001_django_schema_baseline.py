"""Create the core schema when Django migrations have not done so."""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = '0001_django_schema_baseline'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = (
        set()
        if context.is_offline_mode()
        else set(sa.inspect(op.get_bind()).get_table_names())
    )

    if 'users_myuser' not in existing_tables:
        op.create_table(
            'users_myuser',
            sa.Column(
                'id',
                sa.BigInteger(),
                sa.Identity(always=False),
                primary_key=True,
            ),
            sa.Column('password', sa.String(length=128), nullable=False),
            sa.Column(
                'last_login',
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column('is_superuser', sa.Boolean(), nullable=False),
            sa.Column('username', sa.String(length=150), nullable=False),
            sa.Column('first_name', sa.String(length=150), nullable=False),
            sa.Column('last_name', sa.String(length=150), nullable=False),
            sa.Column('email', sa.String(length=254), nullable=False),
            sa.Column('is_staff', sa.Boolean(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column(
                'date_joined',
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.UniqueConstraint(
                'username',
                name='users_myuser_username_key',
            ),
            if_not_exists=True,
        )
        op.create_index(
            'users_myuser_username_25718abe_like',
            'users_myuser',
            ['username'],
            if_not_exists=True,
            postgresql_ops={'username': 'varchar_pattern_ops'},
        )

    if 'core_textdocument' not in existing_tables:
        op.create_table(
            'core_textdocument',
            sa.Column(
                'id',
                sa.BigInteger(),
                sa.Identity(always=False),
                primary_key=True,
            ),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('slug', sa.String(length=255), nullable=False),
            sa.Column(
                'original_filename',
                sa.String(length=255),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ['user_id'],
                ['users_myuser.id'],
                name=(
                    'core_textdocument_user_id_11297e0a_fk_'
                    'users_myuser_id'
                ),
                deferrable=True,
                initially='DEFERRED',
            ),
            sa.UniqueConstraint(
                'user_id',
                'slug',
                name='unique_document_slug_per_user',
            ),
            if_not_exists=True,
        )
        op.create_index(
            'core_textdocument_user_id_11297e0a',
            'core_textdocument',
            ['user_id'],
            if_not_exists=True,
        )
        op.create_index(
            'core_textdocument_slug_4aa4b6bf',
            'core_textdocument',
            ['slug'],
            if_not_exists=True,
        )
        op.create_index(
            'core_textdocument_slug_4aa4b6bf_like',
            'core_textdocument',
            ['slug'],
            if_not_exists=True,
            postgresql_ops={'slug': 'varchar_pattern_ops'},
        )

    if 'core_label' not in existing_tables:
        op.create_table(
            'core_label',
            sa.Column(
                'id',
                sa.BigInteger(),
                sa.Identity(always=False),
                primary_key=True,
            ),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('color', sa.String(length=7), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.ForeignKeyConstraint(
                ['user_id'],
                ['users_myuser.id'],
                name='core_label_user_id_5817295c_fk_users_myuser_id',
                deferrable=True,
                initially='DEFERRED',
            ),
            sa.UniqueConstraint(
                'user_id',
                'name',
                name='unique_label_name_per_user',
            ),
            if_not_exists=True,
        )
        op.create_index(
            'core_label_user_id_5817295c',
            'core_label',
            ['user_id'],
            if_not_exists=True,
        )

    if 'core_annotation' not in existing_tables:
        op.create_table(
            'core_annotation',
            sa.Column(
                'id',
                sa.BigInteger(),
                sa.Identity(always=False),
                primary_key=True,
            ),
            sa.Column('start', sa.Integer(), nullable=False),
            sa.Column('end', sa.Integer(), nullable=False),
            sa.Column('text', sa.String(length=500), nullable=False),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column('label_id', sa.BigInteger(), nullable=False),
            sa.Column('document_id', sa.BigInteger(), nullable=False),
            sa.CheckConstraint(
                'start >= 0',
                name='core_annotation_start_check',
            ),
            sa.CheckConstraint(
                '"end" >= 0',
                name='core_annotation_end_check',
            ),
            sa.ForeignKeyConstraint(
                ['document_id'],
                ['core_textdocument.id'],
                name=(
                    'core_annotation_document_id_a2087876_fk_'
                    'core_textdocument_id'
                ),
                deferrable=True,
                initially='DEFERRED',
            ),
            sa.ForeignKeyConstraint(
                ['label_id'],
                ['core_label.id'],
                name='core_annotation_label_id_e8eaf5bd_fk_core_label_id',
                deferrable=True,
                initially='DEFERRED',
            ),
            if_not_exists=True,
        )
        op.create_index(
            'core_annotation_document_id_a2087876',
            'core_annotation',
            ['document_id'],
            if_not_exists=True,
        )
        op.create_index(
            'core_annotation_label_id_e8eaf5bd',
            'core_annotation',
            ['label_id'],
            if_not_exists=True,
        )


def downgrade() -> None:
    # This revision may adopt tables created by Django migrations.
    pass
