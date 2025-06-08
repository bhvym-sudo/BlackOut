import socket
import threading
import json
import random
import base64
import time
import requests
import os
import socks
from utils.encryption import encrypt_message, decrypt_message, generate_room_code

class P2PNode:
    def __init__(self, port, onion_address):
        self.port = port
        self.onion_address = onion_address
        self.server_socket = None
        self.peers = {}
        self.room_code = None
        self.username = None
        self.encryption_key = None
        self.message_history = []
        self.running = False
        self.is_room_creator = False
        
    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.port))
            self.server_socket.listen(10)
            self.running = True
            
            threading.Thread(target=self.accept_connections, daemon=True).start()
            print(f"[+] P2P node started on port {self.port}")
            return True
        except Exception as e:
            print(f"[-] Failed to start P2P node: {e}")
            return False
    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for peer_socket in self.peers.values():
            peer_socket.close()
        self.peers.clear()
    
    def accept_connections(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_peer, args=(client_socket,), daemon=True).start()
            except:
                break
    
    def handle_peer(self, peer_socket):
        peer_id = f"peer_{random.randint(1000, 9999)}"
        self.peers[peer_id] = peer_socket
        
        try:
            while self.running:
                data = peer_socket.recv(4096)
                if not data:
                    break
                
                try:
                    message_data = json.loads(data.decode())
                    self.process_message(message_data, peer_id)
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            pass
        finally:
            if peer_id in self.peers:
                del self.peers[peer_id]
            peer_socket.close()
    
    def process_message(self, data, sender_peer_id):
        msg_type = data.get("type")
        
        if msg_type == "join_request":
            self.handle_join_request(data, sender_peer_id)
        elif msg_type == "join_response":
            self.handle_join_response(data)
        elif msg_type == "chat_message":
            self.handle_chat_message(data)
        elif msg_type == "delete_message":
            self.handle_delete_message(data)
        elif msg_type == "peer_list":
            self.handle_peer_list(data)
    
    def handle_join_request(self, data, sender_peer_id):
        if self.room_code and data.get("room_code") == self.room_code:
            response = {
                "type": "join_response",
                "status": "success",
                "encryption_key": base64.b64encode(self.encryption_key).decode()
            }
            self.send_to_peer(sender_peer_id, response)
            
            welcome_msg = {
                "type": "chat_message",
                "username": "System",
                "message": f"{data.get('username')} has joined the chat!",
                "msg_id": f"system_{random.randint(1000, 9999)}",
                "encrypted": False
            }
            self.broadcast_message(welcome_msg)
        else:
            response = {
                "type": "join_response",
                "status": "invalid_room"
            }
            self.send_to_peer(sender_peer_id, response)
    
    def handle_join_response(self, data):
        if data.get("status") == "success":
            self.encryption_key = base64.b64decode(data.get("encryption_key"))
            print(f"[+] Joined room {self.room_code} as {self.username}")
        else:
            print("[-] Failed to join room - invalid room code")
    
    def handle_chat_message(self, data):
        username = data.get("username")
        message = data.get("message")
        msg_id = data.get("msg_id")
        encrypted = data.get("encrypted", True)
        
        if username.lower() == "system":
            decrypted = message
        else:
            if encrypted and self.encryption_key:
                try:
                    decrypted = decrypt_message(message, self.encryption_key)
                except Exception:
                    decrypted = "[ENCRYPTED]"
            else:
                decrypted = message
        
        self.message_history.append({
            "username": username,
            "message": decrypted,
            "encrypted": message if encrypted else decrypted,
            "msg_id": msg_id
        })
        
        if username != self.username:
            print(f"\n[{username}]: {decrypted}")
            print("> ", end="", flush=True)
        
        self.broadcast_message(data, exclude_self=True)
    
    def handle_delete_message(self, data):
        msg_id = data.get("msg_id")
        for i, msg in enumerate(self.message_history):
            if msg.get("msg_id") == msg_id:
                print(f"\n[System] Message from {msg['username']} was deleted")
                self.message_history.pop(i)
                break
        print("> ", end="", flush=True)
        
        self.broadcast_message(data, exclude_self=True)
    
    def handle_peer_list(self, data):
        peer_addresses = data.get("peers", [])
        for peer_addr in peer_addresses:
            if peer_addr != self.onion_address:
                self.connect_to_peer(peer_addr)
    
    def send_to_peer(self, peer_id, data):
        try:
            if peer_id in self.peers:
                message = json.dumps(data).encode()
                self.peers[peer_id].send(message)
        except:
            pass
    
    def broadcast_message(self, data, exclude_self=False):
        message = json.dumps(data).encode()
        for peer_id, peer_socket in list(self.peers.items()):
            try:
                peer_socket.send(message)
            except:
                if peer_id in self.peers:
                    del self.peers[peer_id]
    
    def connect_to_peer(self, peer_onion):
        try:
            if not peer_onion.endswith('.onion'):
                peer_onion += '.onion'
            
            peer_socket = socks.socksocket()
            peer_socket.set_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            peer_socket.settimeout(30)
            
            peer_host = peer_onion.replace('.onion', '')
            peer_socket.connect((peer_host + '.onion', 80))
            
            peer_id = f"peer_{random.randint(1000, 9999)}"
            self.peers[peer_id] = peer_socket
            
            threading.Thread(target=self.handle_peer, args=(peer_socket,), daemon=True).start()
            print(f"[+] Connected to peer: {peer_onion}")
            return True
            
        except Exception as e:
            print(f"[-] Failed to connect to peer {peer_onion}: {e}")
            return False
    
    def create_room(self):
        self.room_code = generate_room_code()
        self.encryption_key = os.urandom(16)
        self.is_room_creator = True
        return self.room_code
    
    def set_username(self, username):
        self.username = username
    
    def join_room(self, room_code, peer_onion, username):
        self.room_code = room_code
        self.username = username
        
        if self.connect_to_peer(peer_onion):
            join_request = {
                "type": "join_request",
                "room_code": room_code,
                "username": username,
                "onion_address": self.onion_address
            }
            
            time.sleep(1)
            for peer_socket in self.peers.values():
                try:
                    message = json.dumps(join_request).encode()
                    peer_socket.send(message)
                    break
                except:
                    continue
            
            time.sleep(2)
            return self.encryption_key is not None
        return False
    
    def send_message(self, message):
        if not self.room_code or not self.username:
            print("[-] Not connected to a room")
            return False
        
        msg_id = f"msg_{random.randint(10000, 99999)}"
        
        if self.encryption_key:
            encrypted_message = encrypt_message(message, self.encryption_key)
        else:
            encrypted_message = message
        
        chat_data = {
            "type": "chat_message",
            "username": self.username,
            "message": encrypted_message,
            "msg_id": msg_id,
            "encrypted": True
        }
        
        self.message_history.append({
            "username": self.username,
            "message": message,
            "encrypted": encrypted_message,
            "msg_id": msg_id
        })
        
        self.broadcast_message(chat_data)
        return msg_id
    
    def delete_message(self, msg_id):
        if not self.room_code:
            print("[-] Not connected to a room")
            return False
        
        delete_data = {
            "type": "delete_message",
            "msg_id": msg_id
        }
        
        self.broadcast_message(delete_data)
        return True
    
    def disconnect(self):
        self.stop()