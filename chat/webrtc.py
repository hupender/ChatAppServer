import json
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack
from asgiref.sync import async_to_sync
from common.redis_proxy import get_redis_instance
from channels.layers import get_channel_layer
from aiortc.contrib.media import MediaRelay, MediaStreamTrack
import re
import numpy as np
import cv2
import asyncio

relay = MediaRelay()
chat_cache = get_redis_instance("CHAT_DB")
connection_cache = {}
active_track_cache = {}
channel_layer = get_channel_layer()

class ClonedVideoTrack(MediaStreamTrack):
    """
    A cloned video track that behaves the same way as the original one.
    """
    def __init__(self, original_track: MediaStreamTrack):
        super().__init__()  # Initialize the base class
        self.original_track = original_track

    async def recv(self):
        # This method is called to retrieve the next frame.
        frame = await self.original_track.recv()
        return frame 


class WebRTC:
    def __init__(self, group=None, user=None, group_members=None, **kwargs):
        self.user = user
        self.group = group
        self.group_members = group_members
        self.peerRTC = RTCPeerConnection()
        self.count = 0

        @self.peerRTC.on("track")
        async def on_track(track: MediaStreamTrack):
            self.count += 1
            # Relay the track to other group members
            # relayed_track = relay.subscribe(track)
            # relayed_track = ClonedVideoTrack(track)
            relayed_track = track

            if self.user in active_track_cache:
                active_track_cache[self.user][track.kind] = relayed_track
            else:
                active_track_cache[self.user] = {
                    track.kind: relayed_track
                }

            for member in self.group_members:
                # if member != self.user:
                    other_peer = connection_cache.get(f"webrtc_{member}_call")
                    if other_peer:
                        # send my track to all the currently joined members
                        try:
                            other_peer.peerRTC.addTrack(relayed_track)
                        except Exception as e:
                            print(track.kind)
                            print("sending new user data to existing ones")
                            print(e)

                        # active_track = active_track_cache.get(member, None)
                        # if active_track:
                        #     # other users track to myself
                        #     try:
                        #         self.peerRTC.addTrack(active_track[track.kind])
                        #     except Exception as e:
                        #         print("sending old users track to current")
                        #         print(track.kind)
                        #         print(e)

            # if self.count == 2:
            #     self.count = 0
            #     await self.handle_renegotiation()

        @self.peerRTC.on("iceconnectionstatechange")
        async def on_ice_change():
            # print(self.peerRTC.iceConnectionState)
            pass

        @self.peerRTC.on("connectionstatechange")
        async def on_conection_state_change():
            pass
            # if self.peerRTC.connectionState == "connected":
            #     # ask user to do renegotiation
            #     data = {
            #         "type": "sendRenegotiationRequest",
            #         "message": "Initiate renegotiation",
            #         "sender": "550e8400-e29b-41d4-a716-446655440000",
            #         "room_id": self.group,
            #         "id": None
            #     }
            #     channel_name = chat_cache.get(self.user, None)
            #     await channel_layer.send(channel_name, data)


        @self.peerRTC.on("icecandidate")
        async def on_ice_candidate(candidate):
            data = {
                "type": "sendIceCandidates",
                "message": json.dumps({
                    "candidate": candidate["candidate"],
                    "sdpMid": candidate["sdpMid"],
                    "sdpMLineIndex": candidate["sdpMLineIndex"]
                }),
                "sender": "550e8400-e29b-41d4-a716-446655440000",
                "room_id": self.group,
                "id": None
            }
            channel_layer = get_channel_layer()
            channel_name = chat_cache.get(self.user, None)
            if channel_name:
                await channel_layer.send(channel_name, data)

    async def handle_renegotiation(self):
        for member in self.group_members:
            other_peer = connection_cache.get(f"webrtc_{member}_call")
            if (other_peer and member != self.user):
                # or (member == self.user and self.peerRTC.connectionState == "connected"):
                # ask user to do renegotiation
                data = {
                    "type": "sendRenegotiationRequest",
                    "message": "Initiate renegotiation",
                    "sender": "550e8400-e29b-41d4-a716-446655440000",
                    "room_id": self.group,
                    "id": None
                }
                channel_name = chat_cache.get(member, None)
                if channel_name:
                    await channel_layer.send(channel_name, data)


    async def handle_ice_candidates(self, data):
        candidate = json.loads(data["message"])
        candidate_parts = candidate["candidate"].split(" ")
        rtc_candidate = RTCIceCandidate(
            foundation=candidate_parts[0],
            component=int(candidate_parts[1]),
            protocol=candidate_parts[2].lower(),
            priority=int(candidate_parts[3]),
            ip=candidate_parts[4],
            port=int(candidate_parts[5]),
            type=candidate_parts[7],
            sdpMid=candidate["sdpMid"],
            sdpMLineIndex=candidate["sdpMLineIndex"],
        )
        await self.peerRTC.addIceCandidate(rtc_candidate)

    async def handle_answer_call(self, data):
        offer = json.loads(data["message"])

        # handle offer
        remote_description = RTCSessionDescription(sdp=offer.get("sdp"), type=offer.get("type"))
        await self.peerRTC.setRemoteDescription(remote_description)
        answer = await self.peerRTC.createAnswer()
        await self.peerRTC.setLocalDescription(RTCSessionDescription(sdp=answer.sdp, type=answer.type))
        
        # send answer to the initiator
        answer = {
            "sdp": answer.sdp,
            "type": answer.type
        }
        data = {
            "type": "sendAnswer",
            "message": json.dumps(answer),
            "sender": "550e8400-e29b-41d4-a716-446655440000",
            "room_id": self.group,
            "id": None
        }
        channel_name = chat_cache.get(self.user, None)
        await channel_layer.send(channel_name, data)

    async def handle_renegotiation_offer(self, data):
        offer = json.loads(data["message"])

        # handle offer
        remote_description = RTCSessionDescription(sdp=offer.get("sdp"), type=offer.get("type"))
        await self.peerRTC.setRemoteDescription(remote_description)
        answer = await self.peerRTC.createAnswer()
        await self.peerRTC.setLocalDescription(RTCSessionDescription(sdp=answer.sdp, type=answer.type))
        
        # send answer to the initiator
        answer = {
            "sdp": answer.sdp,
            "type": answer.type
        }

        data = {
            "type": "sendRenegotiationAnswer",
            "message": json.dumps(answer),
            "sender": "550e8400-e29b-41d4-a716-446655440000",
            "room_id": self.group,
            "id": None
        }
        channel_name = chat_cache.get(self.user, None)
        if channel_name:
            try:
                await channel_layer.send(channel_name, data)
            except Exception as e:
                print("issue here")
                print(channel_name)

    async def handle_offer(self, data):
        offer = json.loads(data["message"])

        # handle offer
        remote_description = RTCSessionDescription(sdp=offer.get("sdp"), type=offer.get("type"))
        await self.peerRTC.setRemoteDescription(remote_description)
        answer = await self.peerRTC.createAnswer()
        await self.peerRTC.setLocalDescription(RTCSessionDescription(sdp=answer.sdp, type=answer.type))
        
        # send answer to the initiator
        answer = {
            "sdp": answer.sdp,
            "type": answer.type
        }

        # notify all active users about incoming call
        for member in self.group_members:
            channel_name = chat_cache.get(member, None)
            if member != self.user:
                data = {
                    "type": "sendIncomingCall",
                    "message": "incoming call",
                    "sender": self.user,
                    "room_id": self.group,
                    "id": None
                }

                if channel_name:
                    await channel_layer.send(channel_name, data)
            else:
                data = {
                    "type": "sendAnswer",
                    "message": json.dumps(answer),
                    "sender": "550e8400-e29b-41d4-a716-446655440000",
                    "room_id": self.group,
                    "id": None
                }
                await channel_layer.send(channel_name, data)
 
    async def handle_end_call(self):
        connection_cache.pop(f"webrtc_{self.user}_call", None)
        active_track_cache.pop(self.user, None)
        
        for transceiver in self.peerRTC.getTransceivers():
            if transceiver.sender.track:
                transceiver.sender.track.stop()
            if transceiver.receiver.track:
                transceiver.receiver.stop()

            transceiver = None
        
        self.peerRTC.close()