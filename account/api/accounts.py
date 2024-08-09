from common.views import BaseView
from django.contrib.auth import get_user_model
from .schema import ChangePasswordSchema
from common.success.messages import PASSWORD_CHANGED_SUCCESS
from django.http import JsonResponse
from common.api_exception import BadRequestData
from common.error.exceptions import INVALID_PASSWORD
from common.helpers import make_response
from common.redis_proxy import data_cache


user_model = get_user_model()

class ChangePassword(BaseView):
    model = user_model
    schema = ChangePasswordSchema
    message = PASSWORD_CHANGED_SUCCESS
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):

        try:
            data = self.schema.loads(request.body)
        except Exception as e:
            raise BadRequestData(errors=str(e))
        
        user = self.schema.user

        is_valid_pass = user.check_password(data["old_password"])
        if is_valid_pass:
            session_key = f"user:{user.id}:session"
            data_cache.delete(session_key)
            user.set_password(data["new_password"])
            user.save()
            return JsonResponse(make_response(request, "POST", response_text=self.message))
        else:
            raise BadRequestData(errors=INVALID_PASSWORD)