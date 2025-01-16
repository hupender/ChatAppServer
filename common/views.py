from functools import reduce
import json
from operator import and_
from typing import Any
from django.http import HttpRequest, JsonResponse
from django.http.response import HttpResponse as HttpResponse
from django.views.generic import View
from django.utils.decorators import method_decorator
from common.pagination import Pagination
from common.helpers import make_response
from common.decorators import validate_json_request, json_token_required
from common.api_exception import BadRequestData, api_exception_handler
from django.db.models import Q

class BaseView(View):
    schema = None
    message = ""
    paginate = True
    
    @method_decorator(api_exception_handler)
    @method_decorator(validate_json_request)
    @method_decorator(json_token_required)
    def dispatch(self, request, *args, **kwargs):
        self.schema = self.schema()
        self.schema.user = request.user
        self.schema.account = request.account
        return super(BaseView, self).dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        try:
            data = self.schema.load(request.GET)
        except Exception as e:
            raise BadRequestData(errors=str(e))
        
        if not hasattr(self, "queryset"):
            self.queryset = self.model.objects.all()
        
        if hasattr(self, "related_model"):
            self.queryset = self.queryset.select_related(*self.related_model)

        if hasattr(self, "reverse_related_model"):
            self.queryset = self.queryset.prefetch_related(*self.reverse_related_model)

        if hasattr(self, "filters"):
            lookup = []
            for key, value in self.filters.items():
                if data.get(key):
                    if value["lookup"] == "eq":
                        lookup.append(Q(**{key: data.get(key)}))
                    elif value["lookup"] == "in":
                        lookup.append(Q(**{f"{key}__in": data.get(key)}))

            if lookup:
                combined_loopup = reduce(and_, lookup)
                self.queryset = self.queryset.filter(combined_loopup)

        if hasattr(self, "custom_filters"):
            for key, value in self.custom_filters.items():
                if key in data:
                    if hasattr(self, value):
                        getattr(self, value)(data.get(key))

        meta = dict()
        if self.paginate:
            data, prev_page_url, next_page_url, count, BASE_URL = Pagination(self.queryset).paginate(request)
            meta = {
                "BASE_URL": BASE_URL,
                "prev_page": prev_page_url,
                "next_page": next_page_url,
                "count": count
            }

        return JsonResponse(make_response(request, "GET", response_data=self.schema.dump(data, many=True), response_text=self.message, meta=meta), status=200)
        


    def post(self, request, *args, **kwargs):
        try:
            data = self.schema.loads(request.body)
        except Exception as e:
            raise BadRequestData(errors=str(e))
    
    def put(self, request, *args, **kwargs):
        pass

    def delete(self, request, *args, **kwargs):
        pass

class BulkBaseView(View):
    schema = None
    message = ""
    
    @method_decorator(api_exception_handler)
    @method_decorator(validate_json_request)
    @method_decorator(json_token_required)
    def dispatch(self, request, *args, **kwargs):
        self.schema = self.schema(many=True)
        self.schema.user = request.user
        self.schema.account = request.account
        return super(BulkBaseView, self).dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass
    
    def put(self, request, *args, **kwargs):
        pass

    def delete(self, request, *args, **kwargs):
        pass
