from celery.utils.log import get_task_logger
from chat.models import ChatRoom, Message
from chatApp.celery import app as celery_app
from django.contrib.auth import get_user_model

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
        Message.objects.create(**data)
        logger.info("Message saved successfully to database.")