import os
import json
from flask import Flask, request, jsonify
from utils.encryption import encrypt_message, generate_room_code
from flask_socketio import SocketIO, emit, join_room
import threading
import random
import base64

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*")

chatrooms = {}

@socketio.on("join")
def handle_join(data):
    room = data["room_code"]
    username = data["username"]
    join_room(room)
    emit("message", {
        "username": "System", 
        "message": f"{username} has joined the chat!", 
        "msg_id": f"system_{random.randint(1000,9999)}"
    }, room=room)

@socketio.on("message")
def handle_message(data):
    room = data["room_code"]
    username = data["username"]
    message = data["message"]
    msg_id = data.get("msg_id", f"msg_{random.randint(10000,99999)}")
    
    if room not in chatrooms:
        return
        
    key = chatrooms[room]
    encrypted_message = encrypt_message(message, key)
    emit("message", {
        "username": username, 
        "message": encrypted_message, 
        "msg_id": msg_id
    }, room=room)

@socketio.on("delete_message")
def handle_delete_message(data):
    room = data["room_code"]
    msg_id = data["msg_id"]
    emit("delete_message", {"msg_id": msg_id}, room=room)

@app.route("/create_room", methods=["POST"])
def create_room():
    room = generate_room_code()
    chatrooms[room] = os.urandom(16)
    return jsonify({"room_code": room, "status": "success"})

@app.route("/join_room/<room_code>", methods=["GET"])
def check_room(room_code):
    if room_code in chatrooms:
        return jsonify({"status": "valid"})
    return jsonify({"status": "invalid"}), 404

@app.route("/get_key/<room_code>")
def get_key(room_code):
    if room_code not in chatrooms:
        return jsonify({"error": "Invalid Room Code"}), 404
    key_b64 = base64.b64encode(chatrooms[room_code]).decode("utf-8")
    return jsonify({"key": key_b64})

def start_server(host="127.0.0.1", port=8000):
    threading.Thread(target=lambda: socketio.run(
        app, host=host, port=port, debug=False, use_reloader=False
    ), daemon=True).start()
    
    print(f"[+] Server started on {host}:{port}")
    return True