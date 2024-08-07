from channels.generic.websocket import WebsocketConsumer
import json
# from asgiref.sync import aysnc_to_sync

class TestConsumer(WebsocketConsumer):
	def connect(self):
		# self.room_name="test_consumer"
		# self.room_group_name = "test_consumer_group"
		# aysnc_to_sync(self.channel_layer.group_add)(
		# 	self.room_name,self.room_group_name	
		# )
		self.accept()
		# self.send(text_data=json.dumps({"msg":"connected"}))
		super().send(text_data=json.dumps({"message":"connected_successfully"}))

	def send(self):
		pass

	def receive(self):
		pass