from fastapi import WebSocket
from fastapi.websockets import WebSocketState


class ConnectionManager:
    """N-member chat connections (DM + groups).

    Each chat has two buckets:
    - members: open thread websocket
    - list: sidebar list websocket (chat_connection=true)
    """

    def __init__(self):
        self.chats: dict[int, dict] = {}

    def _ensure(self, chat_id: int) -> dict:
        if chat_id not in self.chats:
            self.chats[chat_id] = {"members": {}, "list": {}}
        return self.chats[chat_id]

    async def connect(
        self, websocket: WebSocket, chat_id: int, user_id: int, chat_connection: bool | None = None
    ):
        await websocket.accept()
        room = self._ensure(chat_id)
        bucket = "list" if chat_connection is not None else "members"
        room[bucket][user_id] = websocket

        # Notify others that this user is online (list peers for sidebar)
        peer_bucket = "list" if bucket == "list" else "members"
        for uid, ws in list(room[peer_bucket].items()):
            if uid == user_id:
                continue
            if ws is not None and ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_json({"online": True})
                except Exception:
                    pass
        if websocket.client_state == WebSocketState.CONNECTED:
            # If anyone else already connected in same bucket, tell newcomer they're online
            others = [
                uid
                for uid, ws in room[bucket].items()
                if uid != user_id and ws and ws.client_state == WebSocketState.CONNECTED
            ]
            if others:
                try:
                    await websocket.send_json({"online": True})
                except Exception:
                    pass

    async def disconnect(self, chat_id: int, user_id: int, chat_connection: bool | None = None):
        room = self.chats.get(chat_id)
        if not room:
            return
        bucket = "list" if chat_connection is not None else "members"
        room[bucket].pop(user_id, None)

        for uid, ws in list(room[bucket].items()):
            if ws is not None and ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_json({"online": False})
                except Exception:
                    pass

    async def _broadcast(
        self,
        chat_id: int,
        payload: dict,
        *,
        exclude_user_id: int | None = None,
        buckets: tuple[str, ...] = ("members", "list"),
    ):
        room = self.chats.get(chat_id)
        if not room:
            return
        for bucket in buckets:
            for uid, ws in list(room.get(bucket, {}).items()):
                if exclude_user_id is not None and uid == exclude_user_id:
                    continue
                if ws is not None and ws.client_state == WebSocketState.CONNECTED:
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        pass

    async def send_message(self, message: dict, chat_id: int, user_id: int):
        if "user_read_messages" in message:
            await self._broadcast(
                chat_id, {"user_read_messages": True}, exclude_user_id=user_id, buckets=("list",)
            )
            return

        for key in (
            "user_start_sending_media",
            "user_stop_sending_media",
            "user_start_typing",
            "user_stop_typing",
        ):
            if key in message:
                await self._broadcast(chat_id, {key: True}, exclude_user_id=user_id)
                return

        room = self.chats.get(chat_id)
        if not room:
            return

        # If nobody else has the thread open, ping list connections to refresh
        other_members = [
            uid
            for uid, ws in room["members"].items()
            if uid != user_id and ws and ws.client_state == WebSocketState.CONNECTED
        ]
        if not other_members:
            await self._broadcast(
                chat_id, {"chat_id": chat_id}, exclude_user_id=user_id, buckets=("list",)
            )
            return

        await self._broadcast(chat_id, message, exclude_user_id=user_id, buckets=("members",))


manager = ConnectionManager()
