import asyncio
import websockets
import json

clients = {}   # client_id -> websocket
sockets = {}   # websocket -> client_id

async def handler(ws):
    print("[+] New connection from", ws.remote_address)
    try:
        # First message must be register
        raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
        print("[>] RAW:", raw)
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            print("[!] Invalid JSON on register")
            await ws.close(code=1008, reason="Invalid JSON")
            return

        if msg.get("type") != "register" or not msg.get("id"):
            print("[!] First message not register")
            await ws.close(code=1008, reason="Must register first")
            return

        client_id = msg["id"]
        if client_id in clients:
            print(f"[!] Replacing old connection for {client_id}")
            await clients[client_id].close(code=1000)

        clients[client_id] = ws
        sockets[ws] = client_id
        print(f"[+] Registered: {client_id}")

        # Broadcast registration to everyone (including self)
        registered_msg = json.dumps({"type": "registered", "id": client_id})
        for other_ws in list(clients.values()):
            try:
                await other_ws.send(registered_msg)
            except:
                pass

        # Send list of already connected peers to the new client
        known = [cid for cid in clients if cid != client_id]
        if known:
            await ws.send(json.dumps({"type": "already_registered", "ids": known}))
            print(f"[*] Sent already_registered {known} → {client_id}")

        # Main loop: handle incoming signaling messages and keep alive
        async for raw in ws:
            print("[>] RAW:", raw)
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            sender_id = sockets.get(ws)
            if not sender_id:
                continue

            target_id = msg.get("to")
            if not target_id or target_id not in clients:
                print(f"[!] Invalid target: {target_id}")
                continue

            await clients[target_id].send(raw)
            print(f"[<] Forwarded {msg.get('type', 'unknown')} {sender_id} → {target_id}")

    except asyncio.TimeoutError:
        print("[!] Timeout waiting for register")
    except websockets.exceptions.ConnectionClosed:
        print("[!] Connection closed by client")
    except Exception as e:
        print("[!] Error:", e)
    finally:
        # Cleanup
        if ws in sockets:
            cid = sockets[ws]
            print(f"[-] Disconnected: {cid}")
            del sockets[ws]
            if cid in clients and clients[cid] == ws:
                del clients[cid]

async def main():
    print("🚀 Signaling server running on wss://0.0.0.0:10000 (render.com)")

    server = await websockets.serve(
        handler,
        "0.0.0.0",
        10000,
        ping_interval=20,   # Critical: keeps connection alive on render.com
        ping_timeout=20,
        close_timeout=10
    )
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())