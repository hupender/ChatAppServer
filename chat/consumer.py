from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json
from common.api_exception import AuthenticationFailed, BadRequestData
from chat.models import ChatRoom, GroupMember, Message, UserMessage
from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from chat.api.schema import GetAllRoomSchema, MessageSchema
from common.redis_proxy import get_redis_instance
from django.conf import settings
from .tasks import delete_from_cloud, delete_message, edit_message, save_message_to_group, notify_active_user
from urllib.parse import parse_qs
from channels.layers import get_channel_layer

chat_cache = get_redis_instance("CHAT_DB")

class AppConsumer(AsyncJsonWebsocketConsumer):

    schema = MessageSchema()
    model = Message

    async def connect(self):
        await self.accept()
        self.user = self.scope.get("user")

        chat_cache.set(self.user.id, self.channel_name)
        
        response_data = {
            "type": "connection_message",
            "message": "Connected to Channel",
        }
        await self.send(text_data=self.schema.dumps(response_data))

        offline_messages = chat_cache.lget(f"offline_{self.user.id}_messages")
        if offline_messages:
            for message in offline_messages:
                data = json.loads(message.decode())
                await self.channel_layer.send(self.channel_name, data)
                chat_cache.ldel(f"offline_{self.user.id}_messages", message, del_from=1)

    async def disconnect(self, code):
        print(f"Closed with code = {code}")
        chat_cache.delete(self.user.id)
        self.close()

    
    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            data = self.schema.loads(text_data)
        except Exception as e:
            await self.disconnect(code=402)
            raise BadRequestData(errors=e)
        
        chat_room = await self.get_chat_room(data["room_id"])
        if not chat_room:
            await self.disconnect(code=404)
            raise BadRequestData(errors="Invalid room id.")

        chat_members = await database_sync_to_async(
            lambda: list(chat_room.groupmember_set.all().values_list("member", flat=True))
        )()
        if self.user.id not in chat_members:
            await self.disconnect(code=403)
            raise BadRequestData(errors="U are not a member of this group.")
        
        if data["type"] == "sendIceCandidates" or data["type"] == "sendOffer" or data["type"] == "sendAnswer":
            message_id = None
            if chat_room.is_group:
                await self.disconnect(code=400)
                raise BadRequestData(errors="Call only for one to one chat.")
        elif data["type"] == "sendMessage":
            message = Message(room=chat_room, sender=self.user, content=data["message"])
            message_id = message.id
            save_message_to_group.delay(message.id, data["room_id"], data["message"], self.user.id)
        elif data["type"] == "editMessage" or data["type"] == "deleteMessage":
            message_id = data["id"]
            user_message = await self.get_user_message(data["id"], self.user.id)
            if not user_message:
                await self.disconnect(code=403)
                raise AuthenticationFailed(errors="Permisson error")
            if data["type"] == "editMessage" and user_message.is_file:
                await self.disconnect(code=400)
                raise BadRequestData(errors="Can not edit files.")
            if data["type"] == "deleteMessage" and user_message.is_file:
                delete_from_cloud.delay(user_message.id)
            
        
        try:
            for member in chat_members:
                channel_name = chat_cache.get(member, None)
                data = {
                    "type": data["type"],
                    "message": data["message"],
                    "sender": self.user.id,
                    "room_id": str(data["room_id"]),
                    "id": str(message_id)
                }
                if channel_name:
                    await self.channel_layer.send(channel_name, data)
                else:
                    if data["type"] == "deleteMessage":
                        chat_cache.ldel(f"offline_{member}_messages", json.dumps(data))
                    elif data["type"] == "editMessage":
                        offline_messages = chat_cache.lget(f"offline_{member}_messages")
                        if offline_messages:
                            for i, message in enumerate(offline_messages):
                                redis_data = json.loads(message.decode())
                                if data["id"] == redis_data["id"]:
                                    redis_data["message"] = data["message"]
                                    chat_cache.lsetindex(f"offline_{member}_messages", json.dumps(redis_data), i, 157680000)
                                    break
                    elif data["type"] == "sendMessage" or data["type"] == "sendFile":
                        chat_cache.lset(f"offline_{member}_messages", json.dumps(data), 157680000)
                    else:
                        chat_cache.lset(f"offline_{member}_messages", json.dumps(data), 10)

        except Exception as e:
            await self.disconnect(code=404)
            raise BadRequestData(errors=e)

    @database_sync_to_async
    def get_chat_room(self, id):
        try:
            chat_room = ChatRoom.objects.prefetch_related("groupmember_set").get(id=id)
            return chat_room
        except Exception as e:
            return None
        
    @database_sync_to_async
    def get_user_message(self, message, user):
        try:
            user_message = Message.objects.get(id=message)
            if user_message.sender.id == user:
                return user_message
            else:
                return None
        except Exception as e:
            return None
        
    async def sendIceCandidates(self, event):
        data = self.schema.dump(event)
        await self.send(text_data=self.schema.dumps(data))

    async def sendOffer(self, event):
        data = self.schema.dump(event)
        await self.send(text_data=self.schema.dumps(data))
    
    async def sendAnswer(self, event):
        data = self.schema.dump(event)
        await self.send(text_data=self.schema.dumps(data))

    async def sendMessage(self, event):
        data = self.schema.dump(event)
        await self.send(text_data=self.schema.dumps(data))

    async def sendFile(self, event):
        data = self.schema.dump(event)
        await self.send(text_data=self.schema.dumps(data))

    async def editMessage(self, event):
        data = self.schema.dump(event)
        edit_message.delay(data["id"], data["message"])
        await self.send(text_data=self.schema.dumps(data))
    
    async def deleteMessage(self, event):
        data = self.schema.dump(event)
        delete_message.delay(data["id"])
        await self.send(text_data=self.schema.dumps(data))

    async def notify(self, event):
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
