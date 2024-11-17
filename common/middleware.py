from channels.middleware import BaseMiddleware
from django.conf import settings
from django.http import JsonResponse
import jwt
from django.contrib.auth import get_user_model
from .redis_proxy import data_cache
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from common.api_exception import AuthenticationFailed, NotAuthenticated, NotFound
from common.error.exceptions import INVALID_TOKEN, NO_TOKEN, USER_BLOCKED, USER_NOT_FOUND

class ChatAuthentication(BaseMiddleware):
    """
    Middleware for authentication when connecting to channels
    """


    async def __call__(self, scope, receive, send):
        """
        ASGI application; can insert things into the scope and run asynchronous
        code.
        """
        try:
            token = await self.extract_token(scope)
        except:
            await send({
                "type": "websocket.close"
            })
            return
        # TODO improve exception handling
        if not token:
            await send({
                "type": "websocket.close"
            })
            print(INVALID_TOKEN)
            return
            raise NotAuthenticated(errors=INVALID_TOKEN)
        try:
            user = await self.validate_token(token)
            scope["user"]=user
            return await self.inner(scope, receive, send)
        except Exception as e:
            print(e)
            await send({
                "type": "websocket.close"
            })
            return

    
    async def extract_token(self, scope):
        """
        Extract the token from headers
        """
        headers = dict(scope["headers"])
        token_string = parse_qs(headers.get(b'cookie', b'').decode())
        token = token_string.get("CHAT-API-TOKEN", [None])[0]
        return token
    
    async def validate_token(self, token):
        if not token:
            raise AuthenticationFailed(errors=NO_TOKEN)
        with open(settings.JWT_PUBLIC_KEY) as file:
            public_key = file.read()
        try:
            payload = jwt.decode(token, public_key, settings.JWT_ALGORITHM)
        except:
            # return None
            raise NotAuthenticated(errors=INVALID_TOKEN)
        user_model = get_user_model()
        try:
            # user = await user_model.objects.get(id=payload["user_id"])
            user = await database_sync_to_async(user_model.objects.get)(id=payload["user_id"])
        except:
            # return None
            raise NotFound(errors=USER_NOT_FOUND)
        
        session_key = f"user:{user.id}:session"
        session = data_cache.get(session_key)
        if not session or session != payload["session_id"]:
            # return None
            raise NotFound(errors=USER_NOT_FOUND)
        if not user.is_active:
            # return None
            raise AuthenticationFailed(errors=USER_BLOCKED)
        return user