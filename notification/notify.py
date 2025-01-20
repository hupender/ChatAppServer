from django.conf import settings
from common.decorators import translate_activator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from sms import Message
from celery.utils.log import get_task_logger
import firebase_admin
from firebase_admin import credentials, messaging


cred = credentials.Certificate(settings.FCM_SERVICE_FILE)
firebase_admin.initialize_app(cred)
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

        if ("mob" in self.context["notify"]
            and settings.SEND_PUSH_NOTIFICATION
        ):
            template = {
                "body": "mob/%s/%s_body.txt",
                "title": "mob/%s/%s_title.txt"
            }
            self.context["body"] = render_to_string(template["body"] % (self.app, self.file_code), self.context)
            self.context["title"] = render_to_string(template["title"] % (self.app, self.file_code), self.context)
            self.send_push_notification()

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

    def send_push_notification(self):

        message = messaging.Message(
            notification=messaging.Notification(
                title=self.context["title"],
                body=self.context["body"]
                # image=""
            ),
            token="eJ1ScgUxeMr9IrQvBN3XEI:APA91bGsRw_le46aXT0b9xZsZh_u2NP4GPENhRmdhj3G1BpTOlBJ-gFYEMwp6RRE0H6ra3pigZIdBwA1JC4hpLZrGnpxEf-Us4mt8nj62aecstFb5xMlPcw"
        )
        
        try:
            res = messaging.send(message)
            print(res)
        except Exception as e:
            print(e)
