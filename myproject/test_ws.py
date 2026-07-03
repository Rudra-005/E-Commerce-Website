import asyncio
import websockets
import json

async def test_chat():
    uri = "ws://127.0.0.1:8000/ws/support/"
    
    # We need authentication cookies for the connection
    # But wait, without valid JWT tokens or session cookies, the websocket will be AnonymousUser!
    # Let's get a token first via requests.
    
    import requests
    
    print("Logging in...")
    login_data = {"username": "Rudra", "password": "admin123"}
    session = requests.Session()
    
    # Get CSRF token
    session.get("http://127.0.0.1:8000/login/")
    csrftoken = session.cookies.get("csrftoken", "")
    
    res = session.post("http://127.0.0.1:8000/login/", data={
        "username": "Rudra",
        "password": "admin123",
        "csrfmiddlewaretoken": csrftoken
    }, headers={"Referer": "http://127.0.0.1:8000/login/"})
    
    cookies = session.cookies.get_dict()
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    print("Got cookies:", cookie_str)
    
    # Connect Admin
    admin_ws = await websockets.connect(uri, extra_headers={"Cookie": cookie_str})
    print("Admin connected")
    
    # Join conversation 1
    await admin_ws.send(json.dumps({
        "type": "join_conversation",
        "payload": {"conversation_id": 1}
    }))
    
    # Send message from Admin
    print("Sending message from admin...")
    await admin_ws.send(json.dumps({
        "type": "send_message",
        "payload": {
            "conversation_id": 1,
            "message": "hello from test script",
            "sender_type": "admin"
        }
    }))
    
    # Wait for receive
    while True:
        try:
            msg = await asyncio.wait_for(admin_ws.recv(), timeout=2.0)
            print("Admin received:", msg)
        except asyncio.TimeoutError:
            print("No more messages")
            break
            
    await admin_ws.close()

if __name__ == "__main__":
    asyncio.run(test_chat())
