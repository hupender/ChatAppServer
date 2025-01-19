from django.template import Context, Template
from chatApp.celery import app as celery_app
from celery.utils.log import get_task_logger
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string, get_template
from datetime import datetime
from django.utils.translation import gettext as _, activate
from notification.notify import Notify

logger = get_task_logger(__name__)

@celery_app.task
def notify_user(context={}):
    if settings.WHITELISTED_NOTIFICATION_GROUP:
        context["receiver_email"] = [d["email"] for d in settings.WHITELISTED_NOTIFICATION_GROUP]
        context["receiver_mobile_number"] = [d["mobile_number"] for d in settings.WHITELISTED_NOTIFICATION_GROUP]
    else:
        pass
    
    Notify(context).send_notifications()

