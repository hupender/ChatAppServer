import json
from common.api_exception import *
from functools import wraps
from django.http import HttpResponseNotAllowed
from common.error.exceptions import INVALID_JSON_REQUEST_FORMAT
from common.api_exception import BadRequestData, MethodNotAllowed

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
