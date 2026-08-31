from app.core.cache import delete_key, get_json, set_json
from app.core.config import get_settings
from app.models import Label
from app.schemas import LabelRead


def labels_cache_key(user_id: int) -> str:
    return f'user:{user_id}:labels'


def serialize_labels(labels: list[Label]) -> list[dict]:
    return [
        LabelRead.model_validate(label).model_dump(mode='json')
        for label in labels
    ]


async def get_cached_labels(user_id: int) -> list[dict] | None:
    value = await get_json(labels_cache_key(user_id))
    if not isinstance(value, list):
        return None
    return value


async def cache_labels(user_id: int, labels: list[dict]) -> None:
    await set_json(
        labels_cache_key(user_id),
        labels,
        get_settings().cache_ttl_seconds,
    )


async def invalidate_labels_cache(user_id: int) -> None:
    await delete_key(labels_cache_key(user_id))
