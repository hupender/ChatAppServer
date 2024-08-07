from django.contrib.auth import get_user_model
from django.db.models import Q
from common.api_exception import BadRequestData
from common.error.exceptions import USERNAME_PASSWORD_INCORRECT, ACCOUNT_NOT_EXISTS, EMAIL_NOT_VERIFIED, MOBILE_NOT_VERIFIED, EMAIL_MOBILE_NOT_VERIFIED
from .helpers import isEmail, isMobileNumber



user_model = get_user_model()

class AuthBackend:
    """
    Custom auth model for user authentication
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = user_model.objects.get(Q(username=username) | Q(email=username) | Q(mobile_number=username), is_active=True)
            if not user:
                raise BadRequestData(errors = ACCOUNT_NOT_EXISTS)
            
            if user.check_password(password):
                if isEmail(username) and not user.email_verified:
                    raise BadRequestData(errors = EMAIL_NOT_VERIFIED)
                if isMobileNumber(username) and user.mobile_number_verified:
                    raise BadRequestData(errors=MOBILE_NOT_VERIFIED)
                elif not (user.email_verified or user.mobile_number_verified):
                    raise BadRequestData(errors= EMAIL_MOBILE_NOT_VERIFIED)
                return user
            login_with_otp = kwargs.get("login_with_otp",None)
            if login_with_otp:
                # add logic for otp verification 
                pass
            else:
                raise BadRequestData(errors= USERNAME_PASSWORD_INCORRECT)

        except user_model.DoesNotExist:
            raise BadRequestData(errors = ACCOUNT_NOT_EXISTS)

    def get_user(self, user_id):
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
