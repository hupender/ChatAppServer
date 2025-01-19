from chatApp.celery import app as celery_app
from celery.utils.log import get_task_logger
from datetime import datetime
from notification.tasks import notify_user
from django.contrib.auth import get_user_model

logger = get_task_logger(__name__)

@celery_app.task
def send_signup_notification(user_id):
    user = get_user_model().objects.get(id=user_id)
    context = {
        "first_name": user.first_name,
        "email": user.email,
        "signup_date": datetime.now(),
        "receivers": [user.email],
        "app": "accounts",
        "file_code": "welcome",
        "notify": ["email", ],
        "language": user.language
    }
    
    notify_user.delay(context)