import asyncio
import websockets
import json

# id -> websocket
clients = {}


async def handler(ws):
    my_id = None

    print("[+] New connection")

    try:
        async for message in ws:
            print("[>] Received:", message)

            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                print("[!] Invalid JSON")
                continue

            msg_type = msg.get("type")

            # -----------------------------
            # REGISTER (client chooses ID)
            # -----------------------------
            if msg_type == "register":
                requested_id = msg.get("id")

                if not requested_id:
                    await ws.send(json.dumps({
                        "type": "error",
                        "reason": "ID required"
                    }))
                    continue

                if requested_id in clients:
                    await ws.send(json.dumps({
                        "type": "error",
                        "reason": "ID already in use"
                    }))
                    continue

                my_id = requested_id
                clients[my_id] = ws

                await ws.send(json.dumps({
                    "type": "registered",
                    "id": my_id
                }))

                print(f"[+] Registered client as {my_id}")
                continue

            # -----------------------------
            # FORWARD SIGNALING MESSAGES
            # -----------------------------
            target = msg.get("to")
            if not target:
                print("[!] No target in message")
                continue

            target_ws = clients.get(target)
            if not target_ws:
                print(f"[!] Target not found: {target}")
                continue

            try:
                await target_ws.send(json.dumps(msg))
                print(f"[<] Forwarded {msg_type} → {target}")
            except:
                print(f"[!] Failed to forward to {target}")

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        if my_id and my_id in clients:
            del clients[my_id]
            print(f"[-] Client disconnected: {my_id}")


async def main():
    print("Signaling server running on ws://0.0.0.0:8080")
    async with websockets.serve(handler, "0.0.0.0", 8080):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
