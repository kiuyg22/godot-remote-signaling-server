import asyncio
import websockets
import json

clients = {}  # client_id -> websocket
sockets = {}  # websocket -> client_id

async def handler(ws):
    print("[+] New connection")
    try:
        async for raw in ws:
            print("[>] RAW:", raw)
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                print("[!] Invalid JSON")
                continue

            msg_type = msg.get("type")
            if msg_type == "register":
                client_id = msg.get("id")
                if not client_id:
                    print("[!] Missing id")
                    continue

                # Replace old connection
                if client_id in clients:
                    await clients[client_id].close()
                    print(f"[!] Replacing old connection for {client_id}")

                clients[client_id] = ws
                sockets[ws] = client_id
                print(f"[+] Registered: {client_id}")

                # BROADCAST to ALL clients (including the new one) that this client is registered
                registered_msg = json.dumps({"type": "registered", "id": client_id})
                for other_ws in list(clients.values()):
                    try:
                        await other_ws.send(registered_msg)
                        print(f"[*] Sent registered for {client_id} to a client")
                    except:
                        pass  # Ignore if disconnected

                # === ADD THIS BLOCK: Send list of already-connected peers to the NEW client ===
                known_clients = [cid for cid in clients.keys() if cid != client_id]
                if known_clients:
                    init_msg = json.dumps({"type": "already_registered", "ids": known_clients})
                    await ws.send(init_msg)
                    print(f"[*] Sent already_registered: {known_clients} → {client_id}")

                continue

            # Forward messages (offer, answer, candidate)
            sender_id = sockets.get(ws)
            if not sender_id:
                continue

            target_id = msg.get("to")
            if not target_id:
                print("[!] Missing target")
                continue

            target_ws = clients.get(target_id)
            if target_ws:
                await target_ws.send(raw)
                print(f"[<] {msg_type} {sender_id} → {target_id}")
            else:
                print(f"[!] Target not found: {target_id}")

    except websockets.exceptions.ConnectionClosed:
        print("[!] Connection closed")
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
    print("🚀 Signaling server running on ws://0.0.0.0:10000")
    async with websockets.serve(handler, "0.0.0.0", 10000, ping_interval=20, ping_timeout=20):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())