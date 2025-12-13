import asyncio
import websockets
import json

clients = {}    # client_id -> websocket
sockets = {}    # websocket -> client_id

async def handler(ws):
    print("[+] New connection")

    try:
        async for raw in ws:
            print("[>] RAW:", raw)

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send(json.dumps({"type": "error", "msg": "Invalid JSON"}))
                continue

            msg_type = msg.get("type")

            # 1️⃣ REGISTER
            if msg_type == "register":
                client_id = msg.get("id")
                if not client_id:
                    await ws.send(json.dumps({"type": "error", "msg": "Missing id"}))
                    continue

                # Kick old connection if ID already exists
                if client_id in clients:
                    old_ws = clients[client_id]
                    print(f"[!] ID already in use, replacing: {client_id}")
                    await old_ws.close()

                clients[client_id] = ws
                sockets[ws] = client_id
                print(f"[+] Registered: {client_id}")

                # ✅ Send proper 'registered' message
                await ws.send(json.dumps({"type": "registered", "id": client_id}))
                continue

            # 2️⃣ MUST BE REGISTERED
            if ws not in sockets:
                await ws.send(json.dumps({"type": "error", "msg": "Not registered"}))
                continue

            sender_id = sockets[ws]
            target_id = msg.get("to")
            if not target_id:
                print("[!] Missing target")
                continue

            # 3️⃣ FORWARD
            target_ws = clients.get(target_id)
            if target_ws:
                await target_ws.send(json.dumps(msg))
                print(f"[<] {msg_type} {sender_id} → {target_id}")
            else:
                print(f"[!] Target not found: {target_id}")

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print("[!] Handler error:", e)

    # 4️⃣ CLEANUP
    if ws in sockets:
        cid = sockets[ws]
        print(f"[-] Disconnected: {cid}")
        del sockets[ws]
        if cid in clients and clients[cid] == ws:
            del clients[cid]

async def main():
    print("🚀 Signaling server running on ws://0.0.0.0:10000")
    async with websockets.serve(
        handler,
        "0.0.0.0",
        10000,
        ping_interval=20,
        ping_timeout=20,
        max_size=2**20,
    ):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
