from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from marshmallow import ValidationError
from common.decorators import validate_json_request
from account.api.schema import UserSchema, LoginSchema
from common.api_exception import api_exception_handler, BadRequestData
from common.error.exceptions import BAD_REQUEST
from common.helpers import make_response
from common.success.messages import (
    ACCOUNT_CREATED_SUCCESSFULLY,
    LOGIN_SUCCESSFULL,
)
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
    

    
    return JsonResponse({"msg":"login successfull"})


@require_http_methods(["PUT"])
@api_exception_handler
@validate_json_request
def update_user(request):
    pass