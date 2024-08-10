from django.contrib import admin
from django.urls import path
from .api import auth
from .api import accounts

urlpatterns = [
    path("create-user/", auth.create_user, name="create_user"),
    path("user-login/", auth.login, name="login"),
    # path("update-user/", auth.update_user, name="update_user"),
    path("refresh-token/", auth.refresh_token, name="refresh_token"),
    path("change-password/", accounts.ChangePassword.as_view(), name="change_password"),
    path("get-otp/", auth.send_otp, name="send_otp"),
    path("validate-otp/", auth.validate_otp, name="validate_otp"),
    path("change-password-using-otp/", auth.change_password, name="change_password_using_otp"),
]
