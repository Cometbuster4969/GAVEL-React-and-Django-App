import functools
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from django.conf import settings

from apps.shared.errors import AppError

from . import repository


TOKEN_ALGORITHM = "HS256"
VALID_ROLES = ("administrator", "owner", "reviewer", "adjudicator")


def public_user(user):
    return {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role}


def issue_token(user):
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=86400),
        "aud": settings.JWT_AUDIENCE,
        "iss": settings.JWT_ISSUER,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=TOKEN_ALGORITHM)


def login(email, password):
    user = repository.find_user_by_email(email.strip().lower())
    valid = user is not None and bcrypt.checkpw(password.encode(), user.password_hash.encode())
    if not valid:
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    return {"user": public_user(user), "token": issue_token(user)}


def authenticate(request):
    authorization = request.headers.get("Authorization", "")
    token = authorization[7:].strip() if authorization.startswith("Bearer ") else ""
    if not token:
        raise AppError(401, "AUTH_REQUIRED", "Sign in to continue.")
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[TOKEN_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except jwt.PyJWTError:
        raise AppError(401, "INVALID_TOKEN", "Your Gavel session is invalid or has expired.")
    user = repository.find_user(payload.get("sub", ""))
    if user is None:
        raise AppError(401, "ACCOUNT_UNAVAILABLE", "This Gavel account is no longer available.")
    return user


def require_auth(*roles):
    def decorate(view):
        @functools.wraps(view)
        def wrapped(request, *args, **kwargs):
            request.gavel_user = authenticate(request)
            if roles and request.gavel_user.role not in roles:
                raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot perform this action.")
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


def check_password(user, password):
    return bcrypt.checkpw(password.encode(), user.password_hash.encode())
