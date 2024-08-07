from django.core.exceptions import ValidationError
from django.conf import settings
from common.error.schema import (MOBILE_NUMBER_CONTAIN_ALPHANUMERIC, INCORRECT_LENGTH_OF_MOBILE_NUMBER, LANGUAGE_NOT_EXIST)
from django.core.validators import validate_email

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