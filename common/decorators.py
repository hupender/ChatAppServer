import json
from common.api_exception import *
from functools import wraps
from common.error.exceptions import INVALID_JSON_REQUEST_FORMAT, NO_TOKEN, INVALID_TOKEN, USER_NOT_FOUND, USER_BLOCKED
from common.api_exception import BadRequestData, MethodNotAllowed, AuthenticationFailed, NotAuthenticated, NotFound
from django.conf import settings
import jwt
from django.contrib.auth import get_user_model
from common.redis_proxy import data_cache

def validate_json_request(f):
    """
    validates the request data
    """

    @wraps(f)
    def func(request, *args, **kwargs):
        if request.method in ["GET", "DELETE"]:
            return f(request, *args, **kwargs)
        
        if request.body is None:
            raise BadRequestData(errors = INVALID_JSON_REQUEST_FORMAT)
        
        try:
            if request.method in ["PUT", "POST"]:
                body = json.loads(request.body)
                if not isinstance(body, dict):
                    raise BadRequestData(errors = INVALID_JSON_REQUEST_FORMAT)
                request.username = body.get("username",None)
            else:
                raise MethodNotAllowed(request.method)
        except:
            raise BadRequestData(errors = INVALID_JSON_REQUEST_FORMAT)
        return f(request, *args, **kwargs)
    
    return func


def json_token_required(f):
    """
    validates the jwt token and also the session
    """

    @wraps(f)
    def func(request, *args, **kwargs):
        token = request.META.get("HTTP_CHAT_API_TOKEN", None)
        if not token:
            raise AuthenticationFailed(errors=NO_TOKEN)
        with open(settings.JWT_PUBLIC_KEY) as file:
            public_key = file.read()
        try:
            payload = jwt.decode(token, public_key, settings.JWT_ALGORITHM)
        except:
            raise NotAuthenticated(errors=INVALID_TOKEN)
        user_model = get_user_model()
        user = user_model.objects.get(id=payload["user_id"])
        if not user:
            raise NotFound(errors=USER_NOT_FOUND)
        
        request.user = user
        
        session_key = f"user:{user.id}:session"
        session = data_cache.get(session_key)
        if not session or session != payload["session_id"]:
            raise NotFound(errors=USER_NOT_FOUND)
        if not user.is_active:
            raise AuthenticationFailed(errors=USER_BLOCKED)
        
        return f(request, *args, **kwargs)

    return func