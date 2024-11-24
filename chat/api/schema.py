from marshmallow import Schema, ValidationError, fields, validate, validates, post_load, validates_schema
from account.models import Users
from django.core.validators import validate_email
from chat.models import ChatRoom, GroupMember, Message, UserFriends
from django.db.models import Q
from common.error.schema import (
    INVALID_OTP,
    INVALID_FIRST_NAME, 
    INVALID_LAST_NAME, 
    INVALID_MOBILE_NUMBER, 
    EMAIL_ALREADY_EXISTS,
    INVALID_TOKEN,
    MOBILE_NUMBER_EXISTS,
    INVALID_EMAIL_ID,
    PASSWORD_MIN_LENGTH,
)
from account.helpers import clean_mobile_number
from django.contrib.auth import get_user_model
from datetime import datetime
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async, async_to_sync


class GetAllRoomSchema(Schema):
    model = GroupMember

    display_name = fields.String(required=False)
    # has_chat will filter out 1-1 chat with no messages
    has_chat = fields.Boolean(required=False, load_only=True, default=False)

    last_update = fields.Method("get_update_time")
    group_id = fields.Function(lambda obj: obj.group.id)

    def get_update_time(self, obj):
        return obj.group.update_ts.strftime('%Y-%m-%d %H:%M:%S')

class MessageSchema(Schema):
    model = Message
    
    type = fields.String(load_default="sendMessage")
    message = fields.String(required=True)
    sender = fields.UUID(dump_only=True)
    message_time = fields.Method("get_message_time")
    message_date = fields.Method("get_message_date")
    room_id = fields.UUID(required=True)
    id = fields.UUID()
    is_file = fields.Boolean(dump_default=False, dump_only=True)

    def get_message_time(self, obj):
        return datetime.now().strftime('%H:%M')
    
    def get_message_date(self, obj):
        return datetime.now().strftime('%d-%m-%Y')

class AllMessageSchema(Schema):
    model = Message
    
    message = fields.Function(lambda obj: obj.content)
    sender = fields.Function(lambda obj: obj.sender.id)
    room_id = fields.Function(lambda obj: obj.room.id)
    message_time = fields.Method("get_message_time")
    message_date = fields.Method("get_message_date")
    id = fields.UUID()

    def get_message_time(self, obj):
        return obj.update_ts.strftime('%H:%M')
    
    def get_message_date(self, obj):
        return obj.update_ts.strftime('%d-%m-%Y')

class CreateGroupSchema(Schema):
    model = ChatRoom

    group_name = fields.String(load_only=True)
    group_members = fields.List(fields.UUID(), required=True)

    @validates("group_members")
    def validate_members(self, value):
        self.users = list(Users.objects.filter(id__in=value).exclude(id=self.user.id))
        if len(self.users) != len(value):
            raise ValidationError("Please enter unique user id's", "group_members")
        if len(self.users)<1:
            raise ValidationError("Atleast 1 other member should be added in the group")
        self.users.append(self.user)
        

class AddToGroupSchema(Schema):
    model = GroupMember

    group = fields.UUID(required=True, data_key="group_id")
    member =fields.UUID(required=True, data_key="member_id")
    id = fields.UUID(dump_to="id", dump_only=True)


    @post_load(pass_many=True)
    def validate_group_member(self, data, many, partial):
        if many:
            groups = set([d["group"] for d in data])
            members = [d["member"] for d in data]
            qset = Users.objects.filter(id__in=members)
            chat_set = ChatRoom.objects.filter(id__in=groups)
            if qset.count() != len(members):
                raise ValidationError("Some users does not exist", "user")
            if len(groups) > 1:
                raise ValidationError("Group must be unique.", "group")
            if not chat_set.exists():
                raise ValidationError("Group does not exists.", "user")
            if self.model.objects.filter(group__in=groups, member__in=members):
                raise ValidationError("Some users already in group", "user")
            
            data = [{"member": user, "group": chat_set[0]} for user in qset]
        return data

class FriendSchema(Schema):
    model = UserFriends
    user_model = get_user_model()

    friend = fields.UUID(required=True, data_key="friend_id")

    @validates("friend")
    def validate_friend(self, value):
        try:
            self.friend = self.user_model.objects.get(id=value)
        except:
            raise ValidationError("User does not exist in the system", "friend")
        if self.friend == self.user:
            raise ValidationError("Can not send friend request to own", "friend")
        
    @post_load
    def validate_friend_request(self, data, many, partial):
        # check if they are already friend or request exist with pending status
        friend_request = self.model.objects.filter(
            Q(user=self.friend, friend=self.user) | Q(user=self.user, friend=self.friend)
        ).exclude(status="rejected")
        if friend_request:
            if friend_request[0].status == "approved":
                raise ValidationError("You are already friends with this user.", "friend")
            elif friend_request[0].status == "pending":
                raise ValidationError("Friend Request already exists.", "request")

        return data
        
class GetFriendRequestSchema(Schema):
    model = UserFriends

    id = fields.String(dump_only=True)
    user_id = fields.Function(lambda obj: obj.user.id)
    username = fields.Function(lambda obj: obj.user.username)
    name = fields.Function(lambda obj: obj.user.get_full_name(obj.user))
    status = fields.Function(lambda obj: obj.status)

class UpdateFriendRequestSchema(GetFriendRequestSchema):
    request_status = fields.String(load_only=True, validate=validate.OneOf(["rejected", "approved"]), required=True)