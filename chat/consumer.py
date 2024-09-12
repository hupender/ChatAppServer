from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json
from chat.models import ChatRoom, GroupMember, Message
from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from chat.api.schema import GetAllRoomSchema, MessageSchema
from common.redis_proxy import get_redis_instance
from django.conf import settings
from .tasks import save_message_to_group

chat_instance = get_redis_instance("CHAT_DB")

class AppConsumer(AsyncJsonWebsocketConsumer):

    schema = MessageSchema()
    model = Message
    active_users = {}
    # TODO think
    # will store user_id: group_id 
    # or we can do group_id : [] but it will not be much help 
    # or we can do online_users: [] and group_user: [] 

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        # TODO add validation for valid room id
        # self.roomGroupName = f"chat_{self.room_id}"
        self.roomGroupName = 'chat_%s' % self.room_id

        await self.accept()
        await self.channel_layer.group_add(self.roomGroupName, self.channel_name)

        self.user = self.scope.get("user")

        # await self.send(text_data=f"Connected to group {self.roomGroupName}")

    
    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = self.schema.loads(text_data)

        # save message to db
        save_message_to_group.delay(self.room_id, data["message"], self.user.id)

        # notify offline users

        # it will send message to active users who are in group
        await self.channel_layer.group_send(self.roomGroupName, {
            "type": "sendMessage",
            "message": data["message"],
            "sender": self.user.first_name,
            # "group": data["group_id"],
        })

    async def sendMessage(self, event):
        data = self.schema.dump(event)
        await self.send(text_data=json.dumps(data))



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
