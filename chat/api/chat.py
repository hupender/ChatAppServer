import json
from django.conf import settings
from django.http import JsonResponse
from common.redis_proxy import get_redis_instance
from common.decorators import json_token_required
from common.error.exceptions import NOT_FOUND_ERROR
from django.views.decorators.http import require_http_methods
from common.helpers import make_response
from common.views import BaseView, BulkBaseView
from .schema import AddToGroupSchema, AllMessageSchema, CreateGroupSchema, GetAllRoomSchema, FriendSchema, GetFriendRequestSchema, UpdateFriendRequestSchema
from chat.models import ChatRoom, GroupMember, Message, UserFriends
from common.api_exception import BadRequestData, NotFound, PermissionDenied, api_exception_handler
from django.contrib.auth import get_user_model
from django.db.models import Case, When, F, CharField, Subquery, OuterRef, IntegerField, Count, Value
from cloudinary.uploader import upload_large
from chat.utils import magic_number_map
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

chat_cache = get_redis_instance("CHAT_DB")


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
        room = self.model.objects.create(name=data["group_name"], created_by=user, is_group=True)

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
            raise BadRequestData(errors=e.messages_dict)

        res = self.model.objects.bulk_create([self.model(**d) for d in data])

        return JsonResponse(
            {"response": make_response(request, "POST", response_text=self.message, response_data=self.schema.dump(res)), "meta": {}}, status=200
        )

class GetUserGroups(BaseView):
    """
    This api can be used to get all the groups for a user
    """

    message = "Groups Info Fetched Successfully."
    schema = GetAllRoomSchema
    model = GroupMember
    http_method_names = ["get"]
    custom_filters = {
        "display_name": "filtering_display_name",
        "has_chat": "filtering_has_chat",
    }

    def filtering_display_name(self, value):
        self.queryset = self.queryset.filter(display_name__icontains=value)

    def filtering_has_chat(self, value):
        """
        filteing either a group or has   messges in chat
        """
        message_count = Message.objects.filter(room=OuterRef("group")).annotate(count=Count("id")).values("count")[:1]

        self.queryset = self.queryset.annotate(message_count=Case(
            When(group__is_group=True, then=Value(1)),
            When(group__is_group=False, then=Subquery(message_count)),
            default=Value(0),
            output_field=IntegerField()
        ))

        if value:
            self.queryset = self.queryset.exclude(message_count=0)
        else:
            self.queryset = self.queryset.filter(message_count=0)

    def get(self, request, *args, **kwargs):
        self.queryset = self.model.objects.filter(member=self.schema.user).annotate(
            display_name = Case(
                When(group__is_group=True, then=F("group__name")),
                When(group__is_group=False, then=F("member__username")),
                output_field=CharField()
            )
        ).select_related("group")

        return super(GetUserGroups, self).get(request, *args, **kwargs)
        
class GetGroupMessage(BaseView):
    """
    This api can be uesd to get all message for a chat
    """

    message = "Messages fetched successfully."
    model = Message
    schema = AllMessageSchema
    http_method_names = ["get"]

    def get(self, request, group_id, *args, **kwargs):
        self.queryset = self.model.objects.filter(room=group_id).order_by("created_ts")
        return super(GetGroupMessage, self).get(request, *args, **kwargs)

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
        self.queryset = self.model.objects.filter(
            friend=self.schema.user, friend__is_active=True, status="pending"
        ).select_related("user", "friend")

        return super(GetRequestList, self).get(request, *args, **kwargs)
    
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
            group = ChatRoom.objects.create(name="System", created_by=self.schema.user, is_group=False)
            GroupMember.objects.bulk_create([GroupMember(group=group, member=friend_request.user), GroupMember(group=group, member=user)])
        friend_request.status = data.get("request_status")
        friend_request.save()

        
        return JsonResponse(
            make_response(request, "PUT", response_data=self.schema.dump(friend_request), response_text=self.message), status=202
        )


@require_http_methods(["POST"])
@api_exception_handler
@json_token_required
def share_files_to_room(request, id, *args, **kwargs):
        resp_message = "File has been sent successfully."
        if request.FILES:
            file = request.FILES.get("file", None)
            if file:
                if file.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
                    raise BadRequestData(errors="Max size limit reached")
                file.seek(0)
                magic_number = file.read(8).hex().upper()
                file_type = None
                for magic, ftype in magic_number_map.items():
                    if magic_number.startswith(magic):
                        file_type = ftype
                        break
                file.seek(0)

                response = upload_large(file, resource_type="auto", folder="/ChatApp")

                # send message to all users in group
                try:
                    group = ChatRoom.objects.prefetch_related("groupmember_set").get(id=id)
                except Exception as e:
                    NotFound(errors="Room does not exists.")
                message = Message.objects.create(
                    room=group, sender=request.user, content=f"{response['secure_url']}, {file_type}", is_file=True
                )

                chat_members = list(group.groupmember_set.all().values_list("member", flat=True))
                channel_layer = get_channel_layer()
                for member in chat_members:
                    channel_name = chat_cache.get(member, None)
                    data = {
                        "type": "sendFile",
                        "message": message.content,
                        "sender": request.user.id,
                        "room_id": str(id),
                        "id": str(message.id),
                        "is_file": True
                        
                    }
                    if channel_name:
                        async_to_sync(channel_layer.send)(channel_name, data)
                    else:
                        chat_cache.lset(f"offline_{member}_messages", json.dumps(data), 157680000)
                return JsonResponse(
                    make_response(request, "POST", response_text=resp_message), status=201
                )
            else:
                raise BadRequestData(errors="Please provide file to be sent.")
        else:
            raise BadRequestData(errors="Please provide file to be sent.")
