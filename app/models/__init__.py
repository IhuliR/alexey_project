from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users_myuser'
    __table_args__ = (
        Index(
            'users_myuser_username_25718abe_like',
            'username',
            postgresql_ops={'username': 'varchar_pattern_ops'},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    password: Mapped[str] = mapped_column(String(128))
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    username: Mapped[str] = mapped_column(String(150), unique=True)
    first_name: Mapped[str] = mapped_column(String(150), default='')
    last_name: Mapped[str] = mapped_column(String(150), default='')
    email: Mapped[str] = mapped_column(String(254), default='')
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    date_joined: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class TextDocument(Base):
    __tablename__ = 'core_textdocument'
    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'slug',
            name='unique_document_slug_per_user',
        ),
        Index('core_textdocument_user_id_11297e0a', 'user_id'),
        Index('core_textdocument_slug_4aa4b6bf', 'slug'),
        Index(
            'core_textdocument_slug_4aa4b6bf_like',
            'slug',
            postgresql_ops={'slug': 'varchar_pattern_ops'},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default='')
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            'users_myuser.id',
            name='core_textdocument_user_id_11297e0a_fk_users_myuser_id',
            deferrable=True,
            initially='DEFERRED',
        ),
    )
    slug: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255), default='')


class Label(Base):
    __tablename__ = 'core_label'
    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'name',
            name='unique_label_name_per_user',
        ),
        Index('core_label_user_id_5817295c', 'user_id'),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default='#ffff00')
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            'users_myuser.id',
            name='core_label_user_id_5817295c_fk_users_myuser_id',
            deferrable=True,
            initially='DEFERRED',
        ),
    )


class Annotation(Base):
    __tablename__ = 'core_annotation'
    __table_args__ = (
        CheckConstraint('start >= 0', name='core_annotation_start_check'),
        CheckConstraint('"end" >= 0', name='core_annotation_end_check'),
        Index('core_annotation_label_id_e8eaf5bd', 'label_id'),
        Index('core_annotation_document_id_a2087876', 'document_id'),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    label_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            'core_label.id',
            name='core_annotation_label_id_e8eaf5bd_fk_core_label_id',
            deferrable=True,
            initially='DEFERRED',
        ),
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            'core_textdocument.id',
            name=(
                'core_annotation_document_id_a2087876_fk_'
                'core_textdocument_id'
            ),
            deferrable=True,
            initially='DEFERRED',
        ),
    )
