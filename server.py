import asyncio
import websockets
import json
import secrets
import os

PORT = int(os.environ.get("PORT", 10000))
clients = {}  # id → websocket


async def handler(ws):
    client_id = secrets.token_hex(4)
    clients[client_id] = ws

    await ws.send(json.dumps({
        "type": "welcome",
        "id": client_id
    }))

    print(f"[+] Client connected: {client_id}")

    try:
        async for message in ws:
            print("[>] recv:", message)
            msg = json.loads(message)

            target = msg.get("to")
            if target in clients:
                try:
                    await clients[target].send(json.dumps(msg))
                    print(f"[<] Forwarded to {target}")
                except:
                    pass

    except:
        pass

    print(f"[-] Client disconnected: {client_id}")
    del clients[client_id]


async def main():
    print(f"Signaling server active on port {PORT}")
    async with websockets.serve(
        handler, 
        "0.0.0.0", 
        PORT
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
