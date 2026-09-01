from pathlib import Path

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TextDocument


def normalize_newlines(content: str) -> str:
    return content.replace('\r\n', '\n').replace('\r', '\n')


def resolve_document_title(title: str, original_filename: str) -> str:
    title = title.strip()
    if title:
        return title
    filename_title = Path(original_filename).stem.strip()
    return filename_title or 'Новый документ'


async def generate_unique_document_slug(
    db: AsyncSession,
    user_id: int,
    title: str,
    document_id: int | None = None,
) -> str:
    base_slug = slugify(
        title,
        replacements=(('Я', 'Ya'), ('я', 'ya')),
    )[:255] or 'document'
    query = select(TextDocument.slug).where(TextDocument.user_id == user_id)
    if document_id is not None:
        query = query.where(TextDocument.id != document_id)
    used_slugs = set((await db.scalars(query)).all())

    slug = base_slug
    counter = 2
    while slug in used_slugs:
        suffix = f'-{counter}'
        slug = f'{base_slug[:255 - len(suffix)]}{suffix}'
        counter += 1
    return slug


async def create_text_document(
    db: AsyncSession,
    user_id: int,
    title: str,
    original_filename: str,
    content: str,
) -> TextDocument:
    resolved_title = resolve_document_title(title, original_filename)
    document = TextDocument(
        user_id=user_id,
        title=resolved_title,
        slug=await generate_unique_document_slug(db, user_id, resolved_title),
        original_filename=original_filename,
        content=normalize_newlines(content),
    )
    db.add(document)
    return document
