from django.conf import settings
from common.decorators import translate_activator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from sms import Message
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

class Notify:

    def __init__(self, context=None):
        self.app = context.pop("app")
        self.file_code = context.pop("file_code")
        self.context = context

    @translate_activator
    def send_notifications(self):
        if ("email" in self.context["notify"]
            and settings.SEND_EMAIL_NOTIFICATION
        ):
            template = {
                "body": "email/%s/%s_body.txt",
                "html_body": "email/%s/%s_body_html.html",
                "subject": "email/%s/%s_subject.txt"
            }
            self.context["body"] = render_to_string(template["body"] % (self.app, self.file_code), self.context)
            self.context["html_body"] = render_to_string(template["html_body"] % (self.app, self.file_code), self.context)
            self.context["subject"] = render_to_string(template["subject"] % (self.app, self.file_code), self.context).strip()
            self.send_email()
        
        if ("sms" in self.context["notify"]
            and settings.SEND_SMS_NOTIFICATION
        ):
            template = {
                "body": "sms/%s/%s_body.txt"
            }
            self.context["body"] = render_to_string(template["body"] % (self.app, self.file_code), self.context)
            self.send_sms()

    def send_email(self):
        email = EmailMultiAlternatives(
            self.context["subject"],
            self.context["body"],
            settings.EMAIL_HOST_USER,
            self.context["receiver_email"]
        )
        email.attach_alternative(self.context["html_body"], "text/html")
        email.send()

    def send_sms(self):
        message = Message(
            self.context["body"],
            settings.SMS_SENDER_NUMBER,
            self.context["receiver_mobile_number"]
        )
        message.send()