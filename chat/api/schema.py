from marshmallow import Schema, ValidationError, fields, validate, validates, post_load, validates_schema
from account.models import Users
from django.core.validators import validate_email
from chat.models import ChatRoom, GroupMember, Message
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


class GetAllRoomSchema(Schema):
    model = GroupMember

    group_name = fields.Function(lambda obj: obj.group.name, dump_only=True)
    last_update = fields.Method("get_update_time")
    group_id = fields.Function(lambda obj: obj.group.id)

    def get_update_time(self, obj):
        return obj.group.update_ts.strftime('%Y-%m-%d %H:%M:%S')

class MessageSchema(Schema):
    model = Message
    
    type = fields.String()
    message = fields.String()
    sender = fields.UUID(dump_only=True)
    group_id = fields.UUID()
    message_time = fields.Method("get_message_time")

    def get_message_time(self, obj):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class AllMessageSchema(Schema):
    model = Message
    
    message = fields.Function(lambda obj: obj.content)
    sender = fields.Function(lambda obj: obj.sender.id)
    group_id = fields.Function(lambda obj: obj.room.id)
    message_time = fields.Method("get_message_time")

    def get_message_time(self, obj):
        return obj.update_ts.strftime('%Y-%m-%d %H:%M:%S')

class CreateGroupSchema(Schema):
    model = ChatRoom

    group_name = fields.String(load_only=True)

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


