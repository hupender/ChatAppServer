from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json
from chat.models import ChatRoom, GroupMember, Message
from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from chat.api.schema import GetAllRoomSchema, MessageSchema
from common.redis_proxy import get_redis_instance
from django.conf import settings
from .tasks import save_message_to_group, notify_active_user
from urllib.parse import parse_qs

chat_cache = get_redis_instance("CHAT_DB")

class AppConsumer(AsyncJsonWebsocketConsumer):

    schema = MessageSchema()
    model = Message

    async def connect(self):
        query_params = parse_qs(self.scope["query_string"].decode())
        self.room_id = query_params.get("group_id", [None])[0]
        # TODO add validation for valid room id
        if self.room_id:
            self.roomGroupName = f"chat_{self.room_id}"
        else:
            self.roomGroupName = "chat_home"

        await self.accept()
        await self.channel_layer.group_add(self.roomGroupName, self.channel_name)

        self.user = self.scope.get("user")

        chat_cache.set(self.user.id, self.channel_name)
        
        response_data = {
            "type": "connection_message",
            "message": f"Connected to group {self.roomGroupName}",
            "group_id": self.room_id
        }
        await self.send(text_data=self.schema.dumps(response_data))

    async def disconnect(self, code):
        chat_cache.delete(self.user.id)
        await self.channel_layer.group_discard(self.roomGroupName, self.channel_name)
        self.close()

    
    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = self.schema.loads(text_data)

        # save message to db
        save_message_to_group.delay(self.room_id, data["message"], self.user.id)

        # TODO notify offline users

        # notify users active in another group
        notify_active_user.delay(self.room_id, data["message"], self.user.id)

        # it will send message to active users who are in group
        await self.channel_layer.group_send(self.roomGroupName, {
            "type": "sendMessage",
            "message": data["message"],
            "sender": self.user.id,
            # "group": data["group_id"],
        })

    async def sendMessage(self, event):
        # event["type"] = "message"
        data = self.schema.dump(event)
        await self.send(text_data=self.schema.dumps(data))

    async def notify(self, event):
        # event["type"] = "notification"
        data = self.schema.dump(event)
        await self.send(text_data=self.schema.dumps(data))


class App1Consumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_id"]
        self.roomGroupName = 'chat_%s' % self.room_name

        await self.accept()
        await self.channel_layer.group_add(
            self.roomGroupName,
            self.channel_name
        )
        # await self.send(text_data=f"Connected to group {self.room_name}")
    
    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)

        await self.channel_layer.group_send(
            self.roomGroupName, {
                "type": "sendMessage",
                "message": data["message"],
                # "user": data["username"],
                # "room_name": data["room_name"],
                "user":"shree"
            }
        )

    async def sendMessage(self, event):
        message = event["message"]
        sender = event["user"]
        await self.send(text_data=json.dumps({"message": message, "sender": sender}))
