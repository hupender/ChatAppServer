from celery.utils.log import get_task_logger
from chat.models import ChatRoom, GroupMember, Message, UserMessage
from chatApp.celery import app as celery_app
from django.contrib.auth import get_user_model
from common.redis_proxy import get_redis_instance
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async
from cloudinary.uploader import destroy

chat_cache = get_redis_instance("CHAT_DB")

logger = get_task_logger(__name__)

@celery_app.task
def save_message_to_group(msg_id, room_id, message, user_id):
    user_model = get_user_model()
    group = ChatRoom.objects.get(id=room_id)
    user = user_model.objects.get(id=user_id)
    data = {
        "id": msg_id,
        "room": group,
        "sender": user,
        "content": message
    }
    message = Message.objects.create(**data)
    # usermessage = UserMessage.objects.create(message=message, user=user, is_read=True)
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

@celery_app.task
def edit_message(message_id, content):
    message = Message.objects.get(id=message_id)
    message.content = content
    message.save()
    logger.info("Message Edited successfully.")

@celery_app.task
def delete_message(message_id):
    Message.objects.get(id=message_id).delete()
    logger.info("Message deleted successfully.")

@celery_app.task
def delete_from_cloud(message_id):
    message = Message.objects.get(id=message_id)
    content = message.content
    # extract the public id and delete 
    public_id = "/".join(content.split("/")[-2:]).split(".")[0]
    destroy(public_id)
    logger.info("Successfully deleted file from cloud.")
    
            