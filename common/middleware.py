from channels.middleware import BaseMiddleware
from django.conf import settings
import jwt
from django.contrib.auth import get_user_model
from .redis_proxy import data_cache

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
        token = self.extract_token(scope)
        is_valid = self.validate_token(token, scope)
        if is_valid:
            return await self.inner(scope, receive, send)
        else:
            await send({
                "type": "websocket.close"
            })

    
    def extract_token(self, scope):
        """
        Extract the token from headers
        """
        headers = dict(scope["headers"])
        token = headers.get(b'chat-api-token', b'').decode()
        return token
    
    def validate_token(self, token, scope):
        if not token:
            raise AuthenticationFailed(errors=NO_TOKEN)
        with open(settings.JWT_PUBLIC_KEY) as file:
            public_key = file.read()
        try:
            payload = jwt.decode(token, public_key, settings.JWT_ALGORITHM)
        except:
            return False
            raise NotAuthenticated(errors=INVALID_TOKEN)
        user_model = get_user_model()
        try:
            user = user_model.objects.get(id=payload["user_id"])
        except:
            return False
            raise NotFound(errors=USER_NOT_FOUND)
        
        session_key = f"user:{user.id}:session"
        session = data_cache.get(session_key)
        if not session or session != payload["session_id"]:
            return False
            raise NotFound(errors=USER_NOT_FOUND)
        if not user.is_active:
            return False
            raise AuthenticationFailed(errors=USER_BLOCKED)
        
        scope["user"] = user
        return True