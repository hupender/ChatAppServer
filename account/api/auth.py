from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from marshmallow import ValidationError
import jwt
from django.conf import settings
from django.utils import timezone
from common.decorators import validate_json_request, json_token_required
from account.api.schema import UserSchema, LoginSchema, OtpSchema, ValidateOtpSchema
from common.api_exception import api_exception_handler, BadRequestData
from common.error.exceptions import USER_NOT_FOUND, EMAIL_MOBILE_NOT_VERIFIED, EMAIL_MOBILE_NOT_EXIST
from common.error.schema import INVALID_OTP
from common.helpers import make_response, generate_random_string, create_random_number
from account.helpers import get_user
from common.success.messages import (
    ACCOUNT_CREATED_SUCCESSFULLY,
    LOGIN_SUCCESSFULL,
    OTP_VALIDATED,
    REFRESH_TOKEN_SUCCESSFULL,
    OTP_SENT,
)
from common.redis_proxy import data_cache, get_redis_instance
from django.contrib.auth import get_user_model, authenticate


user_model = get_user_model()
otp_cache = get_redis_instance("OTP_DB")

@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
def create_user(request):
    """
    This api can be used for create a new user.
    """

    message = ACCOUNT_CREATED_SUCCESSFULLY
    schema = UserSchema()
    try:
        data = schema.loads(request.body)
    except ValidationError as e:
        raise BadRequestData(errors=str(e))
    
    user = user_model.objects.create_user(password=data.pop("password"), **data)

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


@require_http_methods(["GET"])
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
    response["account_number"] = request.account

    return JsonResponse(
        {"response": make_response(request, "POST", response_text=message, response_data=response), "meta": {}}, status=200
    )


@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
def send_otp(request):
    schema = OtpSchema()
    message = OTP_SENT

    try:
        data = schema.loads(request.body)
    except Exception as e:
        raise BadRequestData(errors=str(e))
    
    user = get_user(data["username"])

    if not user:
        raise BadRequestData(errors=USER_NOT_FOUND)
    
    if not (user.email or user.mobile_number):
        raise EMAIL_MOBILE_NOT_EXIST
    if not (user.email_verified or user.mobile_verified):
        raise EMAIL_MOBILE_NOT_VERIFIED
    

    otp = create_random_number()

    session_key = f"user:{user.id}:otp"
    otp_cache.set(session_key, otp)
    response = {}
    response["otp"]=otp

    return JsonResponse(
        {"response": make_response(request, "POST", message, response), "meta": {}}, status=200
    )
    

@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
def validate_otp(request):
    schema = ValidateOtpSchema()
    message = OTP_VALIDATED

    try:
        data = schema.loads(request.body)
    except Exception as e:
        raise BadRequestData(errors=str(e))
    
    try:
        user = get_user(data["username"])
    except Exception as e:
        raise BadRequestData(errors=str(e))
    
    
    session_key = f"user:{user.id}:otp"
    if not (otp_cache.get(session_key) == data["otp"]):
        raise BadRequestData(errors=INVALID_OTP)
    
    token = create_random_number()
    token_key = f"user:{user.id}:token"
    otp_cache.set(token_key, token, ex=settings.REDIS_OTP_EXPIRY)

    response = {}
    response["token"] = token

    return JsonResponse(
        {"response": make_response(request, "POST", message, response), "meta": {}}, status=200
    )
