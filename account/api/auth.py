import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from marshmallow import ValidationError
import jwt
from django.conf import settings
from django.utils import timezone
from common.decorators import validate_json_request, json_token_required
from account.api.schema import PasswordChangeOtpSchema, UserSchema, LoginSchema, OtpSchema, ValidateOtpSchema
from common.api_exception import api_exception_handler, BadRequestData
from common.error.exceptions import INVALID_TOKEN, USER_NOT_FOUND, EMAIL_MOBILE_NOT_VERIFIED, EMAIL_MOBILE_NOT_EXIST, USERNAME_PASSWORD_INCORRECT
from common.error.schema import INVALID_OTP
from common.helpers import make_response, generate_random_string, create_random_number
from account.helpers import get_user
from common.success.messages import (
    ACCOUNT_CREATED_SUCCESSFULLY,
    LOGIN_SUCCESSFULL,
    LOGOUT_SUCCESSFULL,
    OTP_VALIDATED,
    PASSWORD_CHANGED_SUCCESS,
    REFRESH_TOKEN_SUCCESSFULL,
    OTP_SENT,
)
from common.redis_proxy import data_cache, get_redis_instance
from django.contrib.auth import get_user_model, authenticate
from google.oauth2 import id_token
from google.auth.transport import requests


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
        raise BadRequestData(errors=e.messages_dict)
    
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
        raise BadRequestData(errors=e.messages_dict)
    
    try:
        user = authenticate(request, username=data["username"], password=data["password"])
    except Exception as e:
        raise BadRequestData(errors=USERNAME_PASSWORD_INCORRECT)
    
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
    result = {}
    result["user_id"] = user.id
    result["token"] = token
    result["account_number"] = user.account_number
    
    response = JsonResponse(
        {"response": make_response(request, "POST", response_text=message, response_data=result), "meta": {}}, status=200
    )
    response.set_cookie("CHAT-API-TOKEN", result["token"], 86400, httponly=True,secure=True, samesite='None')
    return response

@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
def oauth_login(request):
    message = LOGIN_SUCCESSFULL
    try:
        res = json.loads(request.body)
        data = id_token.verify_oauth2_token(res.get("credential"), requests.Request(), settings.GOOGLE_CLIENT_ID)
    except Exception as e:
        # TODO better error handling
        raise BadRequestData(errors=str(e))
    try:
        user = user_model.objects.get(email=data.get("email", None))
    except:
        modified_data = {}
        modified_data["first_name"] = data.get("given_name", None)
        modified_data["last_name"] = data.get("family_name", None)
        modified_data["email"] = data.get("email", None)
        modified_data["password"] = generate_random_string(10)
        # TODO generate a sudo random username usng first name and last name
        user = user_model.objects.create_user(password=modified_data.pop("password"), **modified_data)

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
    result = {}
    result["user_id"] = user.id
    result["token"] = token
    result["account_number"] = user.account_number
    
    response = JsonResponse(
        {"response": make_response(request, "POST", response_text=message, response_data=result), "meta": {}}, status=200
    )
    response.set_cookie("CHAT-API-TOKEN", result["token"], 86400, httponly=True,secure=True, samesite='None')
    return response




@require_http_methods(["POST"])
@api_exception_handler
@json_token_required
def log_out(request):
    """
    This api can be used to log out the user
    """

    message = LOGOUT_SUCCESSFULL
    user = request.user
    session_cache_key = f"user:{user.id}:session"
    data_cache.delete(session_cache_key)

    return JsonResponse(
        {"response": make_response(request, "POST", response_text=message), "meta": {}}, status=201
    )


@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
@json_token_required
def refresh_token(request):
    """
    This api can be used to refresh jwt token using previous token
    """
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
    """
    This api can be used to send otp for all kinds o verification
    """
    schema = OtpSchema()
    message = OTP_SENT

    try:
        data = schema.loads(request.body)
    except Exception as e:
        raise BadRequestData(errors=e.messages_dict)
    
    user = get_user(data["username"])

    if not user:
        raise BadRequestData(errors=USER_NOT_FOUND)
    
    if not (user.email or user.mobile_number):
        raise BadRequestData(EMAIL_MOBILE_NOT_EXIST)
    if not (user.email_verified or user.mobile_verified):
        raise BadRequestData(EMAIL_MOBILE_NOT_VERIFIED)
    

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
    """
    This api will validate the otp and give a token which can be used in further steps
    """
    schema = ValidateOtpSchema()
    message = OTP_VALIDATED

    try:
        data = schema.loads(request.body)
    except Exception as e:
        raise BadRequestData(errors=e.messages_dict)
    
    try:
        user = get_user(data["username"])
    except Exception as e:
        raise BadRequestData(errors=e.errors)
    
    
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

@require_http_methods(["POST"])
@api_exception_handler
@validate_json_request
def change_password(request):
    """
    This api can be used to change password using otp verification
    """
    schema = PasswordChangeOtpSchema()
    message = PASSWORD_CHANGED_SUCCESS

    try:
        data = schema.loads(request.body)
    except Exception as e:
        raise BadRequestData(errors=e.messages_dict)
    
    try:
        user = get_user(data["username"])
    except Exception as e:
        raise BadRequestData(errors=e.errors)
    
    token_key = f"user:{user.id}:token"
    if not (otp_cache.get(token_key) == data["token"]):
        raise BadRequestData(errors=INVALID_TOKEN)
    
    otp_cache.delete(token_key)
    
    user.set_password(data["password"])
    user.save()

    return JsonResponse(make_response(request, "POST", response_text=message))
    
