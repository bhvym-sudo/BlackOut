import os
import sys
import time
import threading
import socket
import json
import random
from core.p2p_node import P2PNode
from utils.tor_service import start_tor_service

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    clear_screen()
    print("""
██████╗ ██╗      █████╗  ██████╗██╗  ██╗ ██████╗ ██╗   ██╗████████╗
██╔══██╗██║     ██╔══██╗██╔════╝██║ ██╔╝██╔═══██╗██║   ██║╚══██╔══╝
██████╔╝██║     ███████║██║     █████╔╝ ██║   ██║██║   ██║   ██║   
██╔══██╗██║     ██╔══██║██║     ██╔═██╗ ██║   ██║██║   ██║   ██║   
██████╔╝███████╗██║  ██║╚██████╗██║  ██╗╚██████╔╝╚██████╔╝   ██║   
╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝   
                                                                    
    P2P Secure Console Chat via Tor Hidden Service
    """)

def print_menu():
    print("\n=== MAIN MENU ===")
    print("1. Create a new chat room")
    print("2. Join an existing chat room")
    print("3. About")
    print("4. Exit")
    print("\nSelect an option: ", end="")

def chat_room(node):
    clear_screen()
    print(f"=== CHAT ROOM: {node.room_code} ===")
    print("Type your message and press Enter to send.")
    print("Commands: /exit, /clear, /delete [msg_id], /history, /peers")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("> ")
            
            if user_input.lower() == "/exit":
                break
            elif user_input.lower() == "/clear":
                clear_screen()
                print(f"=== CHAT ROOM: {node.room_code} ===")
            elif user_input.lower().startswith("/delete "):
                msg_id = user_input.split(" ", 1)[1].strip()
                node.delete_message(msg_id)
                print(f"[System] Requested deletion of message {msg_id}")
            elif user_input.lower() == "/history":
                clear_screen()
                print("=== MESSAGE HISTORY ===")
                for msg in node.message_history:
                    print(f"[{msg['msg_id']}] {msg['username']}: {msg['message']}")
                print("=" * 50)
            elif user_input.lower() == "/peers":
                print(f"[System] Connected peers: {len(node.peers)}")
                for peer in node.peers:
                    print(f"  - {peer}")
            elif user_input.strip():
                node.send_message(user_input)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[-] Error: {e}")
    
    print("[+] Leaving chat room...")
    node.disconnect()

def main():
    print_banner()
    
    port = random.randint(8000, 9000)
    
    print("[+] Initializing BlackOut P2P secure chat...")
    
    tor_process, onion_address = start_tor_service(port)
    if not onion_address:
        print("[-] Failed to get onion address. Exiting.")
        return
    
    print(f"[+] Your onion address: {onion_address}")
    
    node = P2PNode(port=port, onion_address=onion_address)
    
    if not node.start():
        print("[-] Failed to start P2P node")
        tor_process.terminate()
        return
    
    time.sleep(2)
    
    try:
        while True:
            print_menu()
            choice = input()
            
            if choice == "1":
                room_code = node.create_room()
                if room_code:
                    username = input("Enter your username: ")
                    node.set_username(username)
                    print(f"[+] Room created: {room_code}")
                    print(f"[+] Your onion address: {onion_address}")
                    print(f"[+] Share this info with others to join:")
                    print(f"    Room Code: {room_code}")
                    print(f"    Onion Address: {onion_address}")
                    input("Press Enter to continue to chat...")
                    chat_room(node)
            
            elif choice == "2":
                room_code = input("Enter room code: ")
                peer_onion = input("Enter peer's onion address: ")
                username = input("Enter your username: ")
                
                if node.join_room(room_code, peer_onion, username):
                    input("Press Enter to continue to chat...")
                    chat_room(node)
            
            elif choice == "3":
                clear_screen()
                print("=== ABOUT BLACKOUT P2P ===")
                print("BlackOut P2P is a decentralized secure chat application.")
                print("Each participant is both server and client.")
                print("All messages are encrypted with AES-128 in CBC mode.")
                print("No central server - direct peer-to-peer communication.")
                print("This tool is designed for secure communications for journalists and whistleblowers.")
                print("Made by bhvym , bhvym72@gmail.com")
                print("\nPress Enter to return to menu...")
                input()
                print_banner()
            
            elif choice == "4":
                break
            
            else:
                print("[-] Invalid choice. Please try again.")
    
    except KeyboardInterrupt:
        print("\n[+] Shutting down...")
    finally:
        print("[+] Stopping P2P node...")
        node.stop()
        print("[+] Terminating Tor process...")
        tor_process.terminate()
        tor_process.wait()
        print("[+] Goodbye!")

if __name__ == "__main__":
    main()