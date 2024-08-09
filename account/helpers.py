from django.core.exceptions import ValidationError
from django.conf import settings
from common.error.schema import (MOBILE_NUMBER_CONTAIN_ALPHANUMERIC, INCORRECT_LENGTH_OF_MOBILE_NUMBER, LANGUAGE_NOT_EXIST)
from django.core.validators import validate_email
from django.contrib.auth import get_user_model
from django.db.models import Q


def clean_mobile_number(number):
    number = str(number)
    number = number.strip()
    wild_chars = (",", ";", "(", ")", "-", ".", " ", "+", "/", "%", "@", "!", "=", "&")
    for ch in wild_chars:
        number = number.replace(ch, "")
    if not number.isdigit():
        raise ValidationError(MOBILE_NUMBER_CONTAIN_ALPHANUMERIC)
    # poor man's validation
    if len(number) != 10:
        raise ValidationError(INCORRECT_LENGTH_OF_MOBILE_NUMBER)
    return number

def validate_language(value):
    for lang in settings.LANGUAGES:
        if value == lang[0]:
            return value
    raise ValidationError(LANGUAGE_NOT_EXIST)

def isEmail(value):
    try:
        validate_email(value)
    except:
        return False
    return True

def isMobileNumber(value):
    try:
        clean_mobile_number(value)
    except:
        return False
    return True

def get_user(username):
    user_model = get_user_model()
    user = user_model.objects.get(Q(username=username) | Q(email=username) | Q(mobile_number=username), is_active=True)
    return user
