from celery.utils.log import get_task_logger
from chat.models import ChatRoom, GroupMember, Message, UserMessage
from chatApp.celery import app as celery_app
from django.contrib.auth import get_user_model
from common.redis_proxy import get_redis_instance
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async

chat_cache = get_redis_instance("CHAT_DB")

logger = get_task_logger(__name__)

@celery_app.task
def save_message_to_group(room_id, message, user_id):
    user_model = get_user_model()
    group = ChatRoom.objects.get(id=room_id)
    user = user_model.objects.get(id=user_id)
    data = {
        "room": group,
        "sender": user,
        "content": message
    }
    message = Message.objects.create(**data)
    usermessage = UserMessage.objects.create(message=message, user=user, is_read=True)
    logger.info("Message saved successfully to database.")

@celery_app.task
def notify_active_user(group_id, message, sender):
    group_members = GroupMember.objects.filter(group=group_id).select_related("member")
    channel_layer = get_channel_layer()
    for group in group_members:
        channel_name = chat_cache.get(group.member.id, None)
        if channel_name:
            async_to_sync(channel_layer.send)(channel_name,{
                "type": "notify",
                "room_id": str(group_id),
                "message": message,
                "sender": sender,
            })
    logger.info("Notified active users")
            