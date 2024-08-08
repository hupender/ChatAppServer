from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from marshmallow import ValidationError
import jwt
from django.conf import settings
from django.utils import timezone
from common.decorators import validate_json_request, json_token_required
from account.api.schema import UserSchema, LoginSchema
from common.api_exception import api_exception_handler, BadRequestData
from common.error.exceptions import BAD_REQUEST
from common.helpers import make_response, generate_random_string
from common.success.messages import (
    ACCOUNT_CREATED_SUCCESSFULLY,
    LOGIN_SUCCESSFULL,
    REFRESH_TOKEN_SUCCESSFULL,
)
from common.redis_proxy import data_cache
from django.contrib.auth import get_user_model, authenticate


user_model = get_user_model()

@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
def create_user(request):
    """
    This api can be used for create a new user.
    """
    model = user_model
    message = ACCOUNT_CREATED_SUCCESSFULLY
    schema = UserSchema()
    try:
        data = schema.loads(request.body)
    except ValidationError as e:
        raise BadRequestData(errors=str(e))
    
    user = model.objects.create_user(password=data.pop("password"), **data)

    response={}
    response["username"] = user.username
    response["id"] = user.id
    response["account_number"] = user.account_number
    
    return JsonResponse(
        {"response": make_response(request, "POST", response_text=message, response_data=response), "meta": {}}, status=200
    )

@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
def login(request):
    """
    This api can be used for log-in 
    """
    model = user_model
    message = LOGIN_SUCCESSFULL
    schema = LoginSchema()

    try:
        data = schema.loads(request.body)
    except ValidationError as e:
        raise BadRequestData(errors= str(e))
    
    try:
        user = authenticate(request, username=data["username"], password=data["password"])
    except ValueError as e:
        raise BadRequestData(errors= str(e))
    
    session_id = generate_random_string(32)
    session_cache_key = f"user:{user.id}:session"
    data_cache.set(key=session_cache_key, value=session_id)

    with open(settings.JWT_PRIVATE_KEY) as file:
        private_key = file.read()

    payload = {
        "user_id": user.id,
        "exp": (timezone.now() + timezone.timedelta(seconds=settings.JWT_TOKEN_EXPIRY)),
        "session_id": session_id
    }

    token = jwt.encode(payload, private_key, settings.JWT_ALGORITHM)
    response = {}
    response["user_id"] = user.id
    response["token"] = token
    response["account_number"] = user.account_number
    
    return JsonResponse(
        {"response": make_response(request, "POST", response_text=message, response_data=response), "meta": {}}, status=200
    )


@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
@json_token_required
def refresh_token(request):
    message = REFRESH_TOKEN_SUCCESSFULL
    session_id = generate_random_string(32)
    session_cache_key = f"user:{request.user.id}:session"
    data_cache.set(session_cache_key, session_id)

    with open(settings.JWT_PRIVATE_KEY) as file:
        private_key = file.read()

    payload = {
        "user_id": request.user.id,
        "session_id": session_id,
        "exp": (timezone.now() + timezone.timedelta(seconds=settings.JWT_TOKEN_EXPIRY))
    }

    token = jwt.encode(payload, private_key, settings.JWT_ALGORITHM)
    response ={}
    response["user_id"] = request.user.id
    response["token"] = token
    response["account_number"] = request.user.account_number
    
    return JsonResponse(
        {"response": make_response(request, "POST", response_text=message, response_data=response), "meta": {}}, status=200
    )


@require_http_methods(["PUT"])
@api_exception_handler
@validate_json_request
def update_user(request):
    pass