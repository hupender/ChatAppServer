from common.views import BaseView
from django.contrib.auth import get_user_model
from .schema import ChangePasswordSchema
from common.success.messages import PASSWORD_CHANGED_SUCCESS
from django.http import JsonResponse
from common.api_exception import BadRequestData


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
        return JsonResponse({"hi":"hi"})