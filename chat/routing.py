from django.urls import path
from chat.consumer import AppConsumer

ws_patterns = [
	# path("ws/chat/<str:room_id>/",ChatConsumer.as_asgi(), name="chat_app"),
    path("ws/chat/<uuid:room_id>/",AppConsumer.as_asgi(), name="home")
]