from django.http import JsonResponse
from common.helpers import make_response
from common.views import BaseView, BulkBaseView
from .schema import AddToGroupSchema, AllMessageSchema, CreateGroupSchema, GetAllRoomSchema, FriendSchema
from chat.models import ChatRoom, GroupMember, Message, UserFriends
from common.api_exception import BadRequestData
from django.contrib.auth import get_user_model

class CreateGroup(BaseView):
    """
    This api can be used to create a new group.
    """

    message = "Group Created Successfully."
    schema = CreateGroupSchema
    model = ChatRoom
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):

        try:
            data = self.schema.loads(request.body)
        except Exception as e:
            raise BadRequestData(errors=str(e))

        user = self.schema.user
        room = self.model.objects.create(name=data["group_name"], created_by=user)
        response = dict()
        response["room_id"] = room.id

        return JsonResponse(
            {"response": make_response(request, "POST", response_text=self.message, response_data=response), "meta": {}}, status=200
        )

class AddToGroup(BulkBaseView):
    """
    This api can be used to add multiple users to a group
    """
    message = "User Added Successfully."
    schema = AddToGroupSchema
    model = GroupMember
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        user_model = get_user_model()
        try:
            data = self.schema.loads(request.body)
        except Exception as e:
            raise BadRequestData(errors=str(e))

        res = self.model.objects.bulk_create([self.model(**d) for d in data])

        return JsonResponse(
            {"response": make_response(request, "POST", response_text=self.message, response_data=self.schema.dump(res)), "meta": {}}, status=200
        )

class GetUserGroups(BulkBaseView):
    """
    This api can be used to get all the groups for a user
    """

    message = "Groups Info Fetched Successfully."
    schema = GetAllRoomSchema
    model = GroupMember
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        user = self.schema.user

        group_data = self.model.objects.filter(member=user.id)

        return JsonResponse(
            {"response": make_response(request, "GET", response_text=self.message, response_data=self.schema.dump(group_data)), "meta": {}}, status=200
        )
        
class GetGroupMessage(BulkBaseView):
    """
    This api can be uesd to get all message for a chat
    """

    message = "Messages fetched successfully."
    model = Message
    schema = AllMessageSchema
    http_method_names = ["get"]

    def get(self, request, group_id, *args, **kwargs):
        user = self.schema.user

        group_message_data = self.model.objects.filter(room=group_id).order_by("update_ts")

        return JsonResponse(
            {"response": make_response(request, "GET", response_text=self.message, response_data=self.schema.dump(group_message_data)), "meta": {}}, status=200
        )

class AddFriend(BaseView):
    """
    This api can be used to add a user's friend
    """
    
    message = "User friend added successfully."
    model = UserFriends
    http_method_names = ["post"]
    schema = FriendSchema

    def post(self, request, *args, **kwargs):
        try:
            data = self.schema.loads(request.body)
        except Exception as e:
            raise BadRequestData(errors=str(e))
        
        user = self.schema.user
        friend = self.schema.friend

        res = self.model.objects.create(user=user, friend=friend, status="pending")

        response = {}
        response["id"] = res.id

        return JsonResponse(
            {"response": make_response(request, "POST", response_text=self.message, response_data=response), "meta": {}}, status=201
        )
    
