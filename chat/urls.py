from django.urls import path
from .api import chat
urlpatterns = [
    path("create-group/", chat.CreateGroup.as_view(), name="create_group"),
    path("add-to-group/", chat.AddToGroup.as_view(), name="add_to_group"),
    path("get-user-groups/", chat.GetUserGroups.as_view(), name="get_user_group"),
    path("get-group-messgaes/<uuid:group_id>/", chat.GetGroupMessage.as_view(), name="get_group_all_message"),
]