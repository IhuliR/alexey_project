from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.errors import ApiValidationError
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    validate_password,
    verify_password,
)
from app.models import User
from app.schemas import (
    AccessToken,
    CurrentUserRead,
    PasswordChange,
    RegisteredUser,
    TokenObtain,
    TokenPair,
    TokenRefresh,
    TokenVerify,
    UserCreate,
)


router = APIRouter(prefix='/api/v1', tags=['Auth'])


def validate_username(username: str) -> str:
    username = username.strip()
    if not username:
        raise ApiValidationError({'username': 'This field may not be blank.'})
    if len(username) > 150:
        raise ApiValidationError(
            {'username': 'Ensure this field has no more than 150 characters.'}
        )
    if not all(
        character.isalnum() or character in '@.+-_'
        for character in username
    ):
        raise ApiValidationError(
            {
                'username': (
                    'Enter a valid username. This value may contain only '
                    'letters, numbers, and @/./+/-/_ characters.'
                )
            }
        )
    return username


def validate_email(email: str) -> str:
    email = email.strip()
    if len(email) > 254:
        raise ApiValidationError(
            {'email': 'Ensure this field has no more than 254 characters.'}
        )
    if email and (
        email.count('@') != 1
        or email.startswith('@')
        or email.endswith('@')
        or '.' not in email.rsplit('@', 1)[1]
    ):
        raise ApiValidationError({'email': 'Enter a valid email address.'})
    return email


@router.post('/users/', response_model=RegisteredUser, status_code=201)
async def register_user(data: UserCreate, db: DatabaseSession) -> User:
    username = validate_username(data.username)
    email = validate_email(data.email)
    existing_user = await db.scalar(
        select(User).where(User.username == username)
    )
    if existing_user is not None:
        raise ApiValidationError(
            {'username': 'A user with that username already exists.'}
        )

    password_errors = validate_password(data.password, username, email)
    if password_errors:
        raise ApiValidationError({'password': password_errors})

    user = User(
        username=username,
        email=email,
        password=hash_password(data.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ApiValidationError(
            {'username': 'A user with that username already exists.'}
        ) from None
    await db.refresh(user)
    return user


@router.get('/users/me/', response_model=CurrentUserRead)
async def current_user(user: CurrentUser) -> User:
    return user


@router.post('/users/set_password/', status_code=204)
async def set_password(
    data: PasswordChange,
    user: CurrentUser,
    db: DatabaseSession,
) -> Response:
    if not verify_password(data.current_password, user.password):
        raise ApiValidationError(
            {'current_password': 'Invalid password.'}
        )
    if data.new_password != data.re_new_password:
        raise ApiValidationError(
            {'non_field_errors': 'The two password fields did not match.'}
        )

    password_errors = validate_password(
        data.new_password,
        user.username,
        user.email,
    )
    if password_errors:
        raise ApiValidationError({'new_password': password_errors})

    user.password = hash_password(data.new_password)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/jwt/create/', response_model=TokenPair)
async def create_tokens(data: TokenObtain, db: DatabaseSession) -> TokenPair:
    user = await db.scalar(
        select(User).where(
            User.username == data.username,
            User.is_active.is_(True),
        )
    )
    if user is None or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=401,
            detail='No active account found with the given credentials',
        )
    return TokenPair(
        refresh=create_token(user.id, token_type='refresh'),
        access=create_token(user.id, token_type='access'),
    )


@router.post('/jwt/refresh/', response_model=AccessToken)
async def refresh_token(data: TokenRefresh) -> AccessToken:
    try:
        payload = decode_token(data.refresh, token_type='refresh')
        user_id = int(payload['user_id'])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail='Token is invalid or expired.',
        ) from None
    return AccessToken(access=create_token(user_id, token_type='access'))


@router.post('/jwt/verify/', status_code=200)
async def verify_token(data: TokenVerify) -> dict[str, str]:
    try:
        decode_token(data.token)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail='Token is invalid or expired.',
        ) from None
    return {}
