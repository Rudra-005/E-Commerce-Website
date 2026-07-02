from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser, User
from django.conf import settings
import jwt

@database_sync_to_async
def get_user_from_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("token_type") == "access":
            return User.objects.get(id=payload["user_id"])
    except Exception:
        pass
    return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        cookies = {}
        if b"cookie" in headers:
            cookie_str = headers[b"cookie"].decode("utf-8")
            for c in cookie_str.split(";"):
                c = c.strip()
                if "=" in c:
                    k, v = c.split("=", 1)
                    cookies[k] = v
        
        access_token = cookies.get("access_token")
        
        if access_token:
            scope["user"] = await get_user_from_token(access_token)
        else:
            if "user" not in scope:
                scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
