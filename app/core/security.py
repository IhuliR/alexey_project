from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from uuid import uuid4

import jwt
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.contrib.auth.password_validation import CommonPasswordValidator

from app.core.config import get_settings


password_hasher = PBKDF2PasswordHasher()
common_passwords = frozenset(CommonPasswordValidator().passwords)


def hash_password(password: str) -> str:
    return password_hasher.encode(password, password_hasher.salt())


def verify_password(password: str, encoded_password: str) -> bool:
    if not encoded_password.startswith('pbkdf2_sha256$'):
        return False
    try:
        return password_hasher.verify(password, encoded_password)
    except (TypeError, ValueError):
        return False


def validate_password(
    password: str,
    username: str = '',
    email: str = '',
) -> list[str]:
    errors = []
    if len(password) < 8:
        errors.append(
            'This password is too short. It must contain at least 8 '
            'characters.'
        )
    if password.strip().lower() in common_passwords:
        errors.append('This password is too common.')
    if password.isdigit():
        errors.append('This password is entirely numeric.')

    for value in (username, email):
        value = value.lower().strip()
        similarity = SequenceMatcher(
            a=password.lower(),
            b=value,
        ).quick_ratio()
        if value and similarity >= 0.7:
            errors.append('The password is too similar to the user data.')
            break
    return errors


def create_token(user_id: int, token_type: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    lifetime = (
        settings.jwt_access_token_lifetime
        if token_type == 'access'
        else settings.jwt_refresh_token_lifetime
    )
    payload = {
        'token_type': token_type,
        'exp': now + timedelta(seconds=lifetime),
        'iat': now,
        'jti': uuid4().hex,
        'user_id': user_id,
    }
    return jwt.encode(payload, settings.secret_key, algorithm='HS256')


def decode_token(token: str, token_type: str | None = None) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=['HS256'])
    except jwt.PyJWTError:
        raise ValueError('Invalid token') from None
    if token_type is not None and payload.get('token_type') != token_type:
        raise ValueError('Invalid token type')
    return payload
