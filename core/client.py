import socketio
import requests
import base64
import threading
import time
import random
import os
from utils.encryption import decrypt_message

class ChatClient:
    def __init__(self, server_url="http://127.0.0.1:8000"):
        self.server_url = server_url
        self.sio = socketio.Client()
        self.room_code = None
        self.username = None
        self.encryption_key = None
        self.message_history = []
        self.setup_socket_events()
        
    def setup_socket_events(self):
        @self.sio.event
        def connect():
            print("[+] Connected to server")
            
        @self.sio.event
        def disconnect():
            print("[-] Disconnected from server")
            
        @self.sio.on("message")
        def on_message(data):
            username = data["username"]
            message = data["message"]
            msg_id = data.get("msg_id", "unknown")
            
            if username.lower() == "system":
                decrypted = message
            else:
                if self.encryption_key:
                    try:
                        decrypted = decrypt_message(message, self.encryption_key)
                    except Exception:
                        decrypted = "[ENCRYPTED]"
                else:
                    decrypted = "[ENCRYPTED - NO KEY]"
            
            self.message_history.append({
                "username": username,
                "message": decrypted,
                "encrypted": message,
                "msg_id": msg_id
            })
            
            print(f"\n[{username}]: {decrypted}")
            print("> ", end="", flush=True)
            
        @self.sio.on("delete_message")
        def on_delete(data):
            msg_id = data["msg_id"]
            for i, msg in enumerate(self.message_history):
                if msg.get("msg_id") == msg_id:
                    print(f"\n[System] Message from {msg['username']} was deleted")
                    self.message_history.pop(i)
                    break
            print("> ", end="", flush=True)
    
    def connect(self):
        try:
            self.sio.connect(self.server_url)
            return True
        except Exception as e:
            print(f"[-] Connection error: {e}")
            return False
    
    def disconnect(self):
        if self.sio.connected:
            self.sio.disconnect()
    
    def create_room(self):
        try:
            response = requests.post(f"{self.server_url}/create_room")
            if response.status_code == 200:
                data = response.json()
                self.room_code = data["room_code"]
                print(f"[+] Room created: {self.room_code}")
                return self.room_code
            else:
                print("[-] Failed to create room")
                return None
        except Exception as e:
            print(f"[-] Error creating room: {e}")
            return None
    
    def join_room(self, room_code, username):
        try:
            response = requests.get(f"{self.server_url}/join_room/{room_code}")
            if response.status_code == 200:
                self.room_code = room_code
                self.username = username
                self.sio.emit("join", {"room_code": room_code, "username": username})
                
                key_response = requests.get(f"{self.server_url}/get_key/{room_code}")
                if key_response.status_code == 200:
                    key_data = key_response.json()
                    key_b64 = key_data["key"]
                    self.encryption_key = base64.b64decode(key_b64)
                    print(f"[+] Joined room {room_code} as {username}")
                    return True
                else:
                    print("[-] Failed to get encryption key")
                    return False
            else:
                print("[-] Invalid room code")
                return False
        except Exception as e:
            print(f"[-] Error joining room: {e}")
            return False
    
    def send_message(self, message):
        if not self.room_code or not self.username:
            print("[-] Not connected to a room")
            return False
        
        msg_id = f"msg_{random.randint(10000, 99999)}"
        self.sio.emit("message", {
            "room_code": self.room_code,
            "username": self.username,
            "message": message,
            "msg_id": msg_id
        })
        return msg_id
    
    def delete_message(self, msg_id):
        if not self.room_code:
            print("[-] Not connected to a room")
            return False
        
        self.sio.emit("delete_message", {
            "room_code": self.room_code,
            "msg_id": msg_id
        })
        return True