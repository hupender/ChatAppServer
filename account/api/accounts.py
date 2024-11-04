from common.views import BaseView
from django.contrib.auth import get_user_model
from .schema import ChangePasswordSchema, DeleteUserSchema, GetUserDetailsSchema, UpdateUserSchema, SearchUserSchema
from common.success.messages import DELETE_ACCOUNT, GET_USER_DETAILS, PASSWORD_CHANGED_SUCCESS, USER_UPDATED_SUCCESSFULLY
from django.http import JsonResponse
from common.api_exception import BadRequestData, NotFound
from common.error.exceptions import CAN_NOT_UPDATE_OTHER_USER, INVALID_PASSWORD, USER_NOT_FOUND
from common.helpers import make_response
from common.redis_proxy import data_cache
from chat.models import UserFriends
from django.db.models import Q


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
    http_method_names = ["get"]
    message = GET_USER_DETAILS

    def get(self, request, *args, **kwargs):
        data = self.schema.dump(self.schema.user)
        return JsonResponse(make_response(request, "GET", response_data=data, response_text=self.message), status=200)
    

class DeleteAccount(BaseView):
    """
    This api can be used to delete user account
    """

    model = user_model
    schema = DeleteUserSchema
    http_method_names = ["delete"]
    message = DELETE_ACCOUNT

    def delete(self, request, *args, **kwargs):
        
        user = self.schema.user
        user.delete()
        return JsonResponse(make_response(request, "DELETE", response_text=self.message), status=200)

class SearchAccount(BaseView):
    """
    This api can be used for searching user using username
    """

    model = user_model
    schema = SearchUserSchema
    http_method_names = ["get"]
    message = "Searched users successfully."

    def get(self, request, *args, **kwargs):
        try:
            data = self.schema.load(request.GET)
        except Exception as e:
            raise BadRequestData(errors=str(e))
        
        user = self.schema.user
        
        qset = self.model.objects.exclude(id=user.id)
        # import pdb;pdb.set_trace()
        if "is_friend" in data:
            user_friends = UserFriends.objects.filter((Q(user=user) | Q(friend=user)), status="approved").values_list("user", "friend")
            friends = set()
            for pair in user_friends:
                friends.add(pair[0])
                friends.add(pair[1])
            if data.get("is_friend"):
                qset = qset.filter(id__in=friends)
            else:
                qset = qset.exclude(id__in=friends)

        if data.get("quick_search"):
            qset = qset.filter(username=data["username"])
        else:
            qset = qset.filter(username__icontains=data["username"])
        
        if not "is_friend" in data and not data.get("username"):
            qset = qset.none()
        
        return JsonResponse(make_response(request, "GET", response_data=self.schema.dump(qset, many=True), response_text=self.message), status=200)