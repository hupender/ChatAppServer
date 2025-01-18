from django.conf import settings
from common.decorators import translate_activator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

class Notify:

    def __init__(self, context=None):
        self.receivers = context.pop("receivers")
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

    def send_email(self):
        email = EmailMultiAlternatives(
            self.context["subject"],
            self.context["body"],
            settings.SENDER_EMAIL,
            self.receivers
        )
        email.attach_alternative(self.context["html_body"], "text/html")
        email.send()