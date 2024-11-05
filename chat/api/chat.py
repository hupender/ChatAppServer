from django.http import JsonResponse
from common.error.exceptions import NOT_FOUND_ERROR
from common.helpers import make_response
from common.views import BaseView, BulkBaseView
from .schema import AddToGroupSchema, AllMessageSchema, CreateGroupSchema, GetAllRoomSchema, FriendSchema, GetFriendRequestSchema, UpdateFriendRequestSchema
from chat.models import ChatRoom, GroupMember, Message, UserFriends
from common.api_exception import BadRequestData, NotFound, PermissionDenied
from django.contrib.auth import get_user_model
from django.db.models import Q


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
            raise BadRequestData(errors=e.messages_dict)

        user = self.schema.user
        room = self.model.objects.create(name=data["group_name"], created_by=user)

        GroupMember.objects.bulk_create([GroupMember(group=room, member=d) for d in self.schema.users])
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
            raise BadRequestData(errors=e.messages_dict)
        
        user = self.schema.user
        friend = self.schema.friend

        res, is_created = self.model.objects.update_or_create(
            user=user,
            friend=friend,
            defaults={
                "status": "pending"
            }
        )

        response = {}
        response["id"] = res.id

        return JsonResponse(
            {"response": make_response(request, "POST", response_text=self.message, response_data=response), "meta": {}}, status=201
        )
    
class GetRequestList(BaseView):
    model = UserFriends
    schema = GetFriendRequestSchema
    http_method_names = ["get"]
    message = "Fetched friend requests successfully."

    def get(self, request, *args, **kwargs):
        user = self.schema.user
        
        queryset = self.model.objects.filter(
            friend=user, friend__is_active=True, status="pending"
        ).select_related("user", "friend")

        return JsonResponse(
            make_response(request, "GET", response_data=self.schema.dump(queryset, many=True), response_text=self.message), status=200
        )
    
class UpdateFriendRequest(BaseView):
    model = UserFriends
    schema = UpdateFriendRequestSchema
    message = "Friend request updated successfully."
    http_method_names = ["put"]

    def put(self, request, id, *args, **kwargs):
        user = self.schema.user
        try:
            data = self.schema.loads(request.body)
        except Exception as e:
            raise BadRequestData(errors=e.messages_dict)
        try:
            friend_request = self.model.objects.get(id=id)
        except self.model.DoesNotExist:
            raise NotFound(errors=NOT_FOUND_ERROR)
        
        if data.get("request_status") == "approved":
            if friend_request.user == self.schema.user:
                raise PermissionDenied()
            # reject any reverse request if any exists
            rev_request = self.model.objects.filter(user=friend_request.friend, friend=user).first()
            if rev_request:
                rev_request.status = "rejected"
                rev_request.save()
        friend_request.status = data.get("request_status")
        friend_request.save()

        
        return JsonResponse(
            make_response(request, "PUT", response_data=self.schema.dump(friend_request), response_text=self.message), status=202
        )
