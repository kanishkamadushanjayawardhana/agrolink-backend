from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter(
    prefix="/ws",
    tags=["Auction WebSocket"]
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, auction_id: int, websocket: WebSocket):
        await websocket.accept()

        if auction_id not in self.active_connections:
            self.active_connections[auction_id] = []

        self.active_connections[auction_id].append(websocket)

    def disconnect(self, auction_id: int, websocket: WebSocket):
        if auction_id in self.active_connections:
            if websocket in self.active_connections[auction_id]:
                self.active_connections[auction_id].remove(websocket)

            if not self.active_connections[auction_id]:
                del self.active_connections[auction_id]

    async def broadcast(self, auction_id: int, message: dict):
        connections = self.active_connections.get(auction_id, [])

        disconnected = []

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(auction_id, connection)


manager = ConnectionManager()


@router.websocket("/auctions/{auction_id}")
async def auction_websocket(
    websocket: WebSocket,
    auction_id: int
):
    await manager.connect(auction_id, websocket)

    try:
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to auction room",
            "auction_id": auction_id
        })

        while True:
            data = await websocket.receive_json()

            await manager.broadcast(
                auction_id,
                data
            )

    except WebSocketDisconnect:
        manager.disconnect(
            auction_id,
            websocket
        )