from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.errors import ApiValidationError
from app.models import Annotation, Label
from app.schemas import LabelPatch, LabelRead, LabelWrite


router = APIRouter(prefix='/api/v1/labels', tags=['Labels'])


async def get_label(
    label_id: int,
    user: CurrentUser,
    db: DatabaseSession,
) -> Label:
    label = await db.scalar(
        select(Label).where(Label.id == label_id, Label.user_id == user.id)
    )
    if label is None:
        raise HTTPException(status_code=404, detail='Not found.')
    return label


def validate_label_values(name: str, color: str) -> tuple[str, str]:
    name = name.strip()
    if not name:
        raise ApiValidationError({'name': 'This field may not be blank.'})
    if len(name) > 100:
        raise ApiValidationError(
            {'name': 'Ensure this field has no more than 100 characters.'}
        )
    if not color:
        raise ApiValidationError({'color': 'This field may not be blank.'})
    if len(color) > 7:
        raise ApiValidationError(
            {'color': 'Ensure this field has no more than 7 characters.'}
        )
    return name, color


async def ensure_unique_name(
    db: DatabaseSession,
    user_id: int,
    name: str,
    label_id: int | None = None,
) -> None:
    query = select(Label.id).where(
        Label.user_id == user_id,
        Label.name == name,
    )
    if label_id is not None:
        query = query.where(Label.id != label_id)
    if await db.scalar(query) is not None:
        raise ApiValidationError(
            {
                'name': (
                    'У вас уже есть метка '
                    'с таким названием.'
                )
            }
        )


@router.get('/', response_model=list[LabelRead])
async def list_labels(user: CurrentUser, db: DatabaseSession) -> list[Label]:
    return list(
        (
            await db.scalars(
                select(Label)
                .where(Label.user_id == user.id)
                .order_by(Label.id)
            )
        ).all()
    )


@router.post('/', response_model=LabelRead, status_code=201)
async def create_label(
    data: LabelWrite,
    user: CurrentUser,
    db: DatabaseSession,
) -> Label:
    name, color = validate_label_values(data.name, data.color)
    await ensure_unique_name(db, user.id, name)
    label = Label(user_id=user.id, name=name, color=color)
    db.add(label)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ApiValidationError(
            {
                'name': (
                    'У вас уже есть метка '
                    'с таким названием.'
                )
            }
        ) from None
    await db.refresh(label)
    return label


@router.get('/{label_id}/', response_model=LabelRead)
async def retrieve_label(
    label: Annotated[Label, Depends(get_label)],
) -> Label:
    return label


async def update_label(
    label: Label,
    data: LabelPatch,
    db: DatabaseSession,
    partial: bool,
) -> Label:
    fields = data.model_fields_set
    if not partial and 'name' not in fields:
        raise ApiValidationError({'name': 'This field is required.'})

    name = data.name if 'name' in fields else label.name
    color = data.color if 'color' in fields else label.color
    name, color = validate_label_values(name, color)
    await ensure_unique_name(db, label.user_id, name, label.id)
    label.name = name
    label.color = color
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ApiValidationError(
            {
                'name': (
                    'У вас уже есть метка '
                    'с таким названием.'
                )
            }
        ) from None
    await db.refresh(label)
    return label


@router.put('/{label_id}/', response_model=LabelRead)
async def replace_label(
    label: Annotated[Label, Depends(get_label)],
    data: LabelPatch,
    db: DatabaseSession,
) -> Label:
    return await update_label(label, data, db, partial=False)


@router.patch('/{label_id}/', response_model=LabelRead)
async def patch_label(
    label: Annotated[Label, Depends(get_label)],
    data: LabelPatch,
    db: DatabaseSession,
) -> Label:
    return await update_label(label, data, db, partial=True)


@router.delete('/{label_id}/', status_code=204)
async def delete_label(
    label: Annotated[Label, Depends(get_label)],
    db: DatabaseSession,
) -> Response:
    annotations_count = await db.scalar(
        select(func.count(Annotation.id)).where(
            Annotation.label_id == label.id
        )
    )
    if annotations_count:
        annotations_word = (
            'аннотации'
            if annotations_count % 10 == 1
            and annotations_count % 100 != 11
            else 'аннотациях'
        )
        return JSONResponse(
            status_code=409,
            content={
                'detail': (
                    'Нельзя удалить метку '
                    f'«{label.name}»: '
                    'она '
                    f'используется в {annotations_count} '
                    f'{annotations_word}. Сначала удалите '
                    'или '
                    'измените '
                    'эти аннотации.'
                ),
                'code': 'label_in_use',
                'annotations_count': annotations_count,
            },
        )

    await db.delete(label)
    await db.commit()
    return Response(status_code=204)
