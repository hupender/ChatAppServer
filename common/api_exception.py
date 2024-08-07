from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.utils.encoding import force_str
from functools import wraps
from common.error.exceptions import (
    SERVER_ERROR, 
    BAD_REQUEST,
    PARSE_ERROR,
    AUTH_ERROR,
    PERMISSION_ERROR,
    NOT_FOUND_ERROR,
    RESOURCE_ALREADY_EXIST,
    TOO_MANY_REQUEST,
    METHOD_ERROR,
)

def api_exception_handler(f):
    @wraps(f)
    def wrapper(request, *args, **kwargs):
        try:
            func = f(request, *args, **kwargs)
            return func
        except APIException as e:
            return JsonResponse({"message": _(str(e.detail)), "error": e.errors, "status_code": e.code}, status=e.code)
    
    return wrapper





class APIException(Exception):
    status_code = 500
    default_detail = SERVER_ERROR

    def __init__(self, detail=None, errors=None, code=None, r_code=None):

        if detail is None:
            self.detail = self.default_detail
        else:
            self.detail = detail

        self.errors = errors

        if code is None:
            self.code = self.status_code
        else:
            self.code = code

        if r_code is None:
            self.r_code = self.code
        else:
            self.r_code = r_code
    
    def __str__(self):
        return self.detail


class BadRequestData(APIException):
    status_code = 400
    default_detail = BAD_REQUEST


class ParseError(APIException):
    status_code = 400
    default_detail = PARSE_ERROR


class AuthenticationFailed(APIException):
    status_code = 401
    default_detail = AUTH_ERROR


class NotAuthenticated(APIException):
    status_code = 401
    default_detail = AUTH_ERROR


class PermissionDenied(APIException):
    status_code = 403
    default_detail = PERMISSION_ERROR


class NotFound(APIException):
    status_code = 404
    default_detail = NOT_FOUND_ERROR


class DuplicateResource(APIException):
    status_code = 409
    default_detail = RESOURCE_ALREADY_EXIST


class HTTPTooManyRequest(APIException):
    status_code = 429
    default_detail = TOO_MANY_REQUEST


class ValidationError(APIException):
    status_code = 400
    default_detail = BAD_REQUEST


class MethodNotAllowed(APIException):
    status_code = 405
    default_detail = METHOD_ERROR

    def __init__(self, method, detail=None):
        if detail is not None:
            self.detail = force_str(detail).format(method=method)
        else:
            self.detail = force_str(self.default_detail).format(method=method)
        super(MethodNotAllowed, self).__init__(self.detail)