from django.urls import path
from chat.consumer import ChatConsumer, AppConsumer

ws_patterns = [
	# path("ws/chat/<str:room_id>/",ChatConsumer.as_asgi(), name="chat_app"),
    path("ws/chat/<str:room_id>/",AppConsumer.as_asgi(), name="home")
]