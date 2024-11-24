from common.models import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _
from account.models import Users


class ChatRoom(BaseModel):
    name = models.CharField(_("name of chat room"), max_length=50)
    created_by = models.ForeignKey(Users, on_delete=models.CASCADE)
    is_group = models.BooleanField(_("wheather the room is a grouop or not"), default=False)

class Message(BaseModel):
    room = models.ForeignKey(ChatRoom, verbose_name=_("name of the room associated"), on_delete=models.CASCADE)
    sender = models.ForeignKey(Users, on_delete=models.CASCADE)
    content = models.TextField(_("content of the message "))
    is_file = models.BooleanField(_("wheather message is a file"), default=False, blank=True)


class UserMessage(BaseModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    is_read = models.BooleanField(_("mark message as read by user"), default=False)

class GroupMember(BaseModel):
    group = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    member = models.ForeignKey(Users, on_delete=models.CASCADE)

class UserFriends(BaseModel):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="user_set")
    friend = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="friend_set")
    status = models.CharField(verbose_name=_("Status of request"), max_length=50, default="pending")