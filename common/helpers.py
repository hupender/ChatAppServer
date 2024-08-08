from django.http import JsonResponse
from django.utils.translation import gettext as _
import random
import re
def make_response(request, response_type, response_text, id=None, response_data=None):
    """
    build response in proper format so maintain uniformity in whole code
    """

    result = {}
    if response_type == "POST":
        result["status_code"] = 201
    elif response_type == "PUT":
        result["status_code"] = 202
    else:
        result["status_code"] = 200

    result["message"] = _(response_text)

    if response_data:
        result["payload"] = response_data
    
    return result


def generate_random_string(length):
    characters = "abcdefghijklmnopqrstuvwxyz123456789"
    return ''.join(random.choices(characters, k=length))

def validate_password(value):
    regex = "^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{6,}$"
    return bool(re.fullmatch(regex,value))