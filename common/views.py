from typing import Any
from django.http import HttpRequest
from django.http.response import HttpResponse as HttpResponse
from django.views.generic import View
from django.utils.decorators import method_decorator
from common.decorators import validate_json_request, json_token_required
from common.api_exception import api_exception_handler

class BaseView(View):
    schema = None
    message = ""
    
    @method_decorator(api_exception_handler)
    @method_decorator(validate_json_request)
    @method_decorator(json_token_required)
    def dispatch(self, request, *args, **kwargs):
        self.schema = self.schema()
        self.schema.user = request.user
        self.schema.account = request.account
        return super(BaseView, self).dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass
    
    def put(self, request, *args, **kwargs):
        pass

    def delete(self, request, *args, **kwargs):
        pass
