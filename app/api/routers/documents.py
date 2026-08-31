import re
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy import delete, func, select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.errors import ApiValidationError
from app.models import Annotation, TextDocument
from app.schemas import ChunkPage, DocumentRead, PaginatedDocuments
from app.services.documents import (
    generate_unique_document_slug,
    normalize_newlines,
    resolve_document_title,
)


router = APIRouter(prefix='/api/v1/documents', tags=['Documents'])


async def get_document(
    document_id: int,
    user: CurrentUser,
    db: DatabaseSession,
) -> TextDocument:
    document = await db.scalar(
        select(TextDocument).where(
            TextDocument.id == document_id,
            TextDocument.user_id == user.id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail='Not found.')
    return document


@router.get('/', response_model=list[DocumentRead] | PaginatedDocuments)
async def list_documents(
    request: Request,
    user: CurrentUser,
    db: DatabaseSession,
    limit: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TextDocument] | PaginatedDocuments:
    query = (
        select(TextDocument)
        .where(TextDocument.user_id == user.id)
        .order_by(TextDocument.id)
    )
    if limit is None:
        return list((await db.scalars(query)).all())

    count = await db.scalar(
        select(func.count(TextDocument.id)).where(
            TextDocument.user_id == user.id
        )
    )
    documents = list(
        (await db.scalars(query.offset(offset).limit(limit))).all()
    )
    next_url = None
    previous_url = None
    if offset + limit < count:
        next_url = str(
            request.url.include_query_params(
                limit=limit,
                offset=offset + limit,
            )
        )
    if offset > 0:
        previous_url = str(
            request.url.include_query_params(
                limit=limit,
                offset=max(0, offset - limit),
            )
        )
    return PaginatedDocuments(
        count=count,
        next=next_url,
        previous=previous_url,
        results=documents,
    )


@router.post('/upload/', response_model=DocumentRead, status_code=201)
async def upload_document(
    user: CurrentUser,
    db: DatabaseSession,
    file: Annotated[UploadFile | None, File()] = None,
) -> TextDocument:
    if file is None:
        raise HTTPException(
            status_code=400,
            detail='Файл не найден.',
        )
    if not file.filename or not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail='Только .txt файлы разрешены.',
        )
    try:
        content = (await file.read()).decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail=(
                'Ошибка при чтении файла. '
                'Проверьте кодировку.'
            ),
        ) from None

    if len(file.filename) > 255:
        raise ApiValidationError(
            {
                'original_filename': (
                    'Ensure this field has no more than 255 characters.'
                )
            }
        )

    title = resolve_document_title(Path(file.filename).stem, file.filename)
    document = TextDocument(
        user_id=user.id,
        title=title,
        slug=await generate_unique_document_slug(db, user.id, title),
        original_filename=file.filename,
        content=normalize_newlines(content),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


@router.post('/', response_model=DocumentRead, status_code=201)
async def create_document(
    user: CurrentUser,
    db: DatabaseSession,
    content: Annotated[str | None, Form()] = None,
    title: Annotated[str, Form()] = '',
    original_filename: Annotated[str, Form()] = '',
) -> TextDocument:
    if content is None:
        raise ApiValidationError({'content': 'This field is required.'})
    if len(title) > 255:
        raise ApiValidationError(
            {'title': 'Ensure this field has no more than 255 characters.'}
        )
    if len(original_filename) > 255:
        raise ApiValidationError(
            {
                'original_filename': (
                    'Ensure this field has no more than 255 characters.'
                )
            }
        )

    resolved_title = resolve_document_title(title, original_filename)
    document = TextDocument(
        user_id=user.id,
        title=resolved_title,
        slug=await generate_unique_document_slug(
            db,
            user.id,
            resolved_title,
        ),
        original_filename=original_filename,
        content=normalize_newlines(content),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


@router.get('/{document_id}/chunks/', response_model=ChunkPage)
async def document_chunks(
    document: Annotated[TextDocument, Depends(get_document)],
    page: str = '1',
    page_size: str = '1',
) -> ChunkPage:
    try:
        page_number = int(page)
        size = int(page_size)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail='page and page_size must be integers.',
        ) from None
    if page_number < 1 or size < 1:
        raise HTTPException(
            status_code=400,
            detail='page and page_size must be >= 1.',
        )

    matches = list(
        re.finditer(r'\S.*?(?=\n\s*\n|\Z)', document.content, flags=re.DOTALL)
    )
    if not matches:
        return ChunkPage(
            document_id=document.id,
            page=page_number,
            page_size=size,
            has_next=False,
            has_prev=False,
            total_chunks=0,
            chunk=[],
            chunk_index=None,
            chunk_start=None,
            chunk_end=None,
        )

    start_index = (page_number - 1) * size
    end_index = start_index + size
    if start_index >= len(matches):
        raise HTTPException(
            status_code=404,
            detail='Страница вне диапазона.',
        )

    page_matches = matches[start_index:end_index]
    one_chunk = len(page_matches) == 1
    return ChunkPage(
        document_id=document.id,
        page=page_number,
        page_size=size,
        has_next=end_index < len(matches),
        has_prev=page_number > 1,
        total_chunks=len(matches),
        chunk=[match.group(0) for match in page_matches],
        chunk_index=start_index if one_chunk else None,
        chunk_start=page_matches[0].start() if one_chunk else None,
        chunk_end=page_matches[0].end() if one_chunk else None,
    )


@router.get('/{document_id}/', response_model=DocumentRead)
async def retrieve_document(
    document: Annotated[TextDocument, Depends(get_document)],
) -> TextDocument:
    return document


async def update_document(
    document: TextDocument,
    db: DatabaseSession,
    title: str | None,
    original_filename: str | None,
    content: str | None,
    partial: bool,
) -> TextDocument:
    if not partial and content is None:
        raise ApiValidationError({'content': 'This field is required.'})
    if title is not None and len(title) > 255:
        raise ApiValidationError(
            {'title': 'Ensure this field has no more than 255 characters.'}
        )
    if original_filename is not None and len(original_filename) > 255:
        raise ApiValidationError(
            {
                'original_filename': (
                    'Ensure this field has no more than 255 characters.'
                )
            }
        )

    if original_filename is not None:
        document.original_filename = original_filename
    if content is not None:
        document.content = normalize_newlines(content)
    if title is not None:
        resolved_title = resolve_document_title(
            title,
            document.original_filename,
        )
        if resolved_title != document.title:
            document.title = resolved_title
            document.slug = await generate_unique_document_slug(
                db,
                document.user_id,
                resolved_title,
                document.id,
            )

    await db.commit()
    await db.refresh(document)
    return document


@router.put('/{document_id}/', response_model=DocumentRead)
async def replace_document(
    document: Annotated[TextDocument, Depends(get_document)],
    db: DatabaseSession,
    content: Annotated[str | None, Form()] = None,
    title: Annotated[str | None, Form()] = None,
    original_filename: Annotated[str | None, Form()] = None,
) -> TextDocument:
    return await update_document(
        document,
        db,
        title,
        original_filename,
        content,
        partial=False,
    )


@router.patch('/{document_id}/', response_model=DocumentRead)
async def patch_document(
    document: Annotated[TextDocument, Depends(get_document)],
    db: DatabaseSession,
    content: Annotated[str | None, Form()] = None,
    title: Annotated[str | None, Form()] = None,
    original_filename: Annotated[str | None, Form()] = None,
) -> TextDocument:
    return await update_document(
        document,
        db,
        title,
        original_filename,
        content,
        partial=True,
    )


@router.delete('/{document_id}/', status_code=204)
async def delete_document(
    document: Annotated[TextDocument, Depends(get_document)],
    db: DatabaseSession,
) -> Response:
    await db.execute(
        delete(Annotation).where(Annotation.document_id == document.id)
    )
    await db.delete(document)
    await db.commit()
    return Response(status_code=204)
