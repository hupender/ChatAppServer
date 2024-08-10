from marshmallow import Schema, ValidationError, fields, validate, validates, post_load
from account.models import Users
from django.core.validators import validate_email
from common.error.schema import (
    INVALID_OTP,
    INVALID_FIRST_NAME, 
    INVALID_LAST_NAME, 
    INVALID_MOBILE_NUMBER, 
    EMAIL_ALREADY_EXISTS,
    INVALID_TOKEN,
    MOBILE_NUMBER_EXISTS,
    INVALID_EMAIL_ID,
    PASSWORD_MIN_LENGTH,
)
from account.helpers import clean_mobile_number
from django.contrib.auth import get_user_model
from common.helpers import validate_password

user_model = get_user_model()

class UserSchema(Schema):
    model = user_model

    first_name = fields.String(required=True, validate=validate.Length(max=60, error=INVALID_FIRST_NAME))
    last_name = fields.String(required=False, validate=validate.Length(max=60, error=INVALID_LAST_NAME))
    email = fields.Email(required=True)
    mobile_number = fields.String(required=False)
    password = fields.String(required=True, validate=validate.Length(min=6), load_only=True)

    @validates("mobile_number")
    def validate_mobile_number(self, value):
        try:
            clean_mobile_number(value)
        except:
            raise ValidationError(INVALID_MOBILE_NUMBER)
        
    @validates("email")
    def validate_email(self, value):
        try:
            validate_email(value)
        except:
            ValidationError(INVALID_EMAIL_ID)
        
    @post_load
    def validates_fields(self, data, many=False, partial=False):
        email = data.get("email", None)
        mobile_number = data.get("mobile_number", None)
        queryset = self.model.objects.filter()
        if email:
            if queryset.filter(email=email, is_active=True).exists():
                raise ValidationError(EMAIL_ALREADY_EXISTS)
        if mobile_number:
            if queryset.filter(mobile_number=mobile_number, is_active=True).exists():
                raise ValidationError(MOBILE_NUMBER_EXISTS)
        return data


class LoginSchema(Schema):
    model = user_model

    username = fields.String(required=True)
    password = fields.String(required=True)
    login_with_otp = fields.Boolean(required=False)

class ChangePasswordSchema(Schema):
    model = user_model

    old_password = fields.String(required=True, load_only=True, validate=validate.Length(min=6, error=PASSWORD_MIN_LENGTH))
    new_password = fields.String(required=True, load_only=True, validate=validate.Length(min=6, error=PASSWORD_MIN_LENGTH))

    # enable later for password validation
    # @validates("new_password")
    # def validate_old_password(self,value):
    #     return validate_password(value)


class OtpSchema(Schema):
    model = user_model

    username = fields.String(required=True)


class ValidateOtpSchema(OtpSchema):

    otp = fields.String(required=True, validate=validate.Length(min=6, error=INVALID_OTP))


class PasswordChangeOtpSchema(OtpSchema):

    password = fields.String(required=True, validate=validate.Length(min=6, error=PASSWORD_MIN_LENGTH))
    token = fields.String(required=True, validate=validate.Length(min=6, error=INVALID_TOKEN))

