from common.views import BaseView
from django.contrib.auth import get_user_model
from .schema import ChangePasswordSchema, GetUserDetailsSchema, UpdateUserSchema
from common.success.messages import PASSWORD_CHANGED_SUCCESS, USER_UPDATED_SUCCESSFULLY
from django.http import JsonResponse
from common.api_exception import BadRequestData
from common.error.exceptions import CAN_NOT_UPDATE_OTHER_USER, INVALID_PASSWORD
from common.helpers import make_response
from common.redis_proxy import data_cache


user_model = get_user_model()

class ChangePassword(BaseView):
    """
    This api can be used to change user password when user is logged in
    """
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
        
class UpdateUser(BaseView):
    """
    This api can be used to update user details
    """
    model = user_model
    schema = UpdateUserSchema
    message = USER_UPDATED_SUCCESSFULLY
    http_method_names = ["put"]

    def put(self, request, *args, **kwargs):

        try:
            data = self.schema.loads(request.body)
        except Exception as e:
            raise BadRequestData(errors=str(e))
        
        user = self.schema.user
        if hasattr(data, "password"):
            data.pop("password")
        
        user.update_fields(user, **data)

        return JsonResponse(make_response(request, "PUT", response_data=self.schema.dump(user), response_text=self.message), status=202)
    

class GetUserDetails(BaseView):
    """
    This api can be used to get user details
    """
    model = user_model
    schema = GetUserDetailsSchema

    def get(self, request, *args, **kwargs):
        data = self.schema.dump(self.schema.user)
        return JsonResponse(make_response(request, "GET", response_data=data, response_text=self.message), status=200)