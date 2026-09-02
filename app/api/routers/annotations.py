from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.errors import ApiValidationError
from app.models import Annotation, Label, TextDocument
from app.schemas import AnnotationPatch, AnnotationRead, AnnotationWrite


router = APIRouter(prefix='/api/v1/annotations', tags=['Annotations'])


async def get_annotation(
    annotation_id: int,
    user: CurrentUser,
    db: DatabaseSession,
) -> Annotation:
    annotation = await db.scalar(
        select(Annotation)
        .join(TextDocument)
        .where(
            Annotation.id == annotation_id,
            TextDocument.user_id == user.id,
        )
    )
    if annotation is None:
        raise HTTPException(status_code=404, detail='Not found.')
    return annotation


async def validate_annotation(
    db: DatabaseSession,
    user_id: int,
    document_id: int,
    label_id: int,
    start: int,
    end: int,
) -> tuple[TextDocument, Label, str]:
    document = await db.get(TextDocument, document_id)
    if document is None or document.user_id != user_id:
        raise ApiValidationError(
            {
                'document': (
                    'Нельзя создавать аннотации '
                    'для чужого документа.'
                )
            }
        )
    label = await db.get(Label, label_id)
    if label is None or label.user_id != user_id:
        raise ApiValidationError(
            {
                'label': (
                    'Нельзя использовать '
                    'чужую метку.'
                )
            }
        )
    if start < 0:
        raise ApiValidationError(
            {'start': 'Ensure this value is greater than or equal to 0.'}
        )
    if end < 0:
        raise ApiValidationError(
            {'end': 'Ensure this value is greater than or equal to 0.'}
        )
    if start >= end:
        raise ApiValidationError(
            {
                'end': (
                    'Конец выделения должен '
                    'быть больше начала.'
                )
            }
        )
    if end > len(document.content):
        raise ApiValidationError(
            {
                'end': (
                    'Конец выделения выходит '
                    'за границы документа.'
                )
            }
        )
    text = document.content[start:end]
    if not text.strip():
        raise ApiValidationError(
            {
                'start': (
                    'Выделение не может состоять '
                    'только из пробелов.'
                )
            }
        )
    return document, label, text


@router.get('/', response_model=list[AnnotationRead])
async def list_annotations(
    user: CurrentUser,
    db: DatabaseSession,
    document: Annotated[int | None, Query()] = None,
) -> list[Annotation]:
    query = (
        select(Annotation)
        .join(TextDocument)
        .where(TextDocument.user_id == user.id)
        .order_by(Annotation.id)
    )
    if document is not None:
        query = query.where(Annotation.document_id == document)
    return list((await db.scalars(query)).all())


@router.post('/', response_model=AnnotationRead, status_code=201)
async def create_annotation(
    data: AnnotationWrite,
    user: CurrentUser,
    db: DatabaseSession,
) -> Annotation:
    _, _, text = await validate_annotation(
        db,
        user.id,
        data.document,
        data.label,
        data.start,
        data.end,
    )
    annotation = Annotation(
        document_id=data.document,
        label_id=data.label,
        start=data.start,
        end=data.end,
        text=text,
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    return annotation


@router.get('/{annotation_id}/', response_model=AnnotationRead)
async def retrieve_annotation(
    annotation: Annotated[Annotation, Depends(get_annotation)],
) -> Annotation:
    return annotation


async def update_annotation(
    annotation: Annotation,
    data: AnnotationPatch,
    user_id: int,
    db: DatabaseSession,
    partial: bool,
) -> Annotation:
    fields = data.model_fields_set
    required_fields = {'document', 'label', 'start', 'end'}
    if not partial:
        missing_fields = required_fields - fields
        if missing_fields:
            raise ApiValidationError(
                {
                    field: 'This field is required.'
                    for field in sorted(missing_fields)
                }
            )

    document_id = (
        data.document if 'document' in fields else annotation.document_id
    )
    label_id = data.label if 'label' in fields else annotation.label_id
    start = data.start if 'start' in fields else annotation.start
    end = data.end if 'end' in fields else annotation.end
    _, _, text = await validate_annotation(
        db,
        user_id,
        document_id,
        label_id,
        start,
        end,
    )
    annotation.document_id = document_id
    annotation.label_id = label_id
    annotation.start = start
    annotation.end = end
    annotation.text = text
    await db.commit()
    await db.refresh(annotation)
    return annotation


@router.put('/{annotation_id}/', response_model=AnnotationRead)
async def replace_annotation(
    annotation: Annotated[Annotation, Depends(get_annotation)],
    data: AnnotationPatch,
    user: CurrentUser,
    db: DatabaseSession,
) -> Annotation:
    return await update_annotation(
        annotation,
        data,
        user.id,
        db,
        partial=False,
    )


@router.patch('/{annotation_id}/', response_model=AnnotationRead)
async def patch_annotation(
    annotation: Annotated[Annotation, Depends(get_annotation)],
    data: AnnotationPatch,
    user: CurrentUser,
    db: DatabaseSession,
) -> Annotation:
    return await update_annotation(
        annotation,
        data,
        user.id,
        db,
        partial=True,
    )


@router.delete('/{annotation_id}/', status_code=204)
async def delete_annotation(
    annotation: Annotated[Annotation, Depends(get_annotation)],
    db: DatabaseSession,
) -> Response:
    await db.delete(annotation)
    await db.commit()
    return Response(status_code=204)
