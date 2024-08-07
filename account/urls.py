from django.contrib import admin
from django.urls import path
from .api import auth

urlpatterns = [
    path("create-user/", auth.create_user, name="create_user"),
    path("user-login/", auth.login, name="login"),
    path("update-user/", auth.update_user, name="update_user"),
]
