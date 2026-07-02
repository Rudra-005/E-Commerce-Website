import jwt

from datetime import datetime, timedelta
from django.conf import settings


ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7


def generate_access_token(user):

    role = "customer"
    permissions = []
    if hasattr(user, "userprofile"):
        role = user.userprofile.role
        permissions = user.userprofile.permissions

    payload = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role,
        "permissions": permissions,
        "token_type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )


def generate_refresh_token(user):

    role = "customer"
    permissions = []
    if hasattr(user, "userprofile"):
        role = user.userprofile.role
        permissions = user.userprofile.permissions

    payload = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role,
        "permissions": permissions,
        "token_type": "refresh",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_DAYS)
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )


def generate_tokens(user):

    access = generate_access_token(user)
    refresh = generate_refresh_token(user)

    return access, refresh


def verify_token(token, token_type):

    try:

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )

        if payload.get("token_type") != token_type:
            return None

        return payload

    except jwt.ExpiredSignatureError:
        return None

    except jwt.InvalidTokenError:
        return None