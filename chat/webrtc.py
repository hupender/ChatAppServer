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


class DummyAudioStreamTrack(MediaStreamTrack):
    """
    A dummy audio stream track that generates silent audio.
    """

    kind = "audio"

    async def recv(self):
        # Wait for a moment before sending the next audio packet
        await asyncio.sleep(0.02)  # Simulate 20ms audio packet interval
        # Generate silent audio packets
        return await super(DummyAudioStreamTrack, self).recv()


class DummyVideoStreamTrack(MediaStreamTrack):
    """
    A dummy video stream track that generates a simple synthetic video.
    """

    kind = "video"

    def __init__(self):
        super().__init__()
        self.width = 640
        self.height = 480
        self.counter = 0

    async def recv(self):
        """
        Generates a synthetic video frame at regular intervals.
        Uses OpenCV to generate synthetic frames.
        """
        await asyncio.sleep(0.033)  # Simulate ~30fps
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Draw simple graphics on the frame to simulate motion
        cv2.putText(
            frame,
            f"Frame {self.counter}",
            (50, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        self.counter += 1

        # Convert frame to bytes for sending over WebRTC
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return await super(DummyVideoStreamTrack, self).recv()


class WebRTC:
    def __init__(self, group=None, user=None, group_members=None, **kwargs):
        self.user = user
        self.group = group
        self.group_members = group_members
        self.peerRTC = RTCPeerConnection()
        # Add dummy audio/video initially to allow connection establishment
        self.audio_transceiver = self.peerRTC.addTransceiver("audio", direction="sendrecv")
        self.video_transceiver = self.peerRTC.addTransceiver("video", direction="sendrecv")

        # Replace these with dummy media streams initially
        # self.audio_transceiver.sender.replaceTrack(DummyAudioStreamTrack())
        # self.video_transceiver.sender.replaceTrack(DummyVideoStreamTrack())

        @self.peerRTC.on("track")
        async def on_track(track: MediaStreamTrack):
            print(f"Ontrack called for {self.user}")
            # Relay the track to other group members
            relayed_track = relay.subscribe(track)
            if self.user in active_track_cache:
                active_track_cache[self.user][track.kind] = relayed_track
            else:
                active_track_cache[self.user] = {
                    track.kind: relayed_track
                }

            # for member in self.group_members:
            #     peer_connection = connection_cache.get(f"webrtc_{member}_call")
            #     if member != self.user:
            #         if member in active_track_cache:
            #             self.audio_transceiver.sender.replaceTrack(active_track_cache[member]["audio"])
            #             self.audio_transceiver.sender.replaceTrack(active_track_cache[member]["video"])


            #         if track.kind == "audio":
            #             peer_connection.audio_transceiver.sender.replaceTrack(relayed_track)
            #         if track.kind == "video":
            #             peer_connection.video_transceiver.sender.replaceTrack(relayed_track)

            # if track.kind == "audio":
            #     self.audio_transceiver.sender.replaceTrack(relayed_track)
            # if track.kind == "video":
            #     self.video_transceiver.sender.replaceTrack(relayed_track)

            # for member in self.group_members:
            #     if member != self.user:
            #         peer_connection = connection_cache.get(f"webrtc_{member}_call")
            #         if peer_connection:
            #             if track.kind == "audio":
            #                 peer_connection.audio_transceiver.sender.replaceTrack(relayed_track)
            #             if track.kind == "video":
            #                 peer_connection.video_transceiver.sender.replaceTrack(relayed_track)
            for member_id in self.group_members:
                if member_id != self.user:
                    # Fetch connection for the group member
                    other_peer = connection_cache.get(f"webrtc_{member_id}_call")
                    if other_peer:
                        if track.kind == "audio":
                            print(f"{self.user} releaying media to member {member_id}")
                            try:
                                other_peer.audio_transceiver.sender.replaceTrack(relayed_track)
                            except Exception as e:
                                print(f"Error relaying audio to {member_id}: {e}")
                        elif track.kind == "video":
                            try:
                                other_peer.video_transceiver.sender.replaceTrack(relayed_track)
                            except Exception as e:
                                print(f"Error relaying video to {member_id}: {e}")
            
            for member in self.group_members:
                if member != self.user:
                    active_track = active_track_cache.get(member, None)
                    if active_track:
                        self.audio_transceiver.sender.replaceTrack(active_track["audio"])
                        self.video_transceiver.sender.replaceTrack(active_track["video"])


                    # else:
                    #     print(f"{self.user} releaying media to member {self.user}")
                    #     if track.kind == "audio":
                    #         self.audio_transceiver.sender.replaceTrack(relayed_track)
                    #     if track.kind == "video":
                    #         self.video_transceiver.sender.replaceTrack(relayed_track)

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
 