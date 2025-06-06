import os
import sys
import time
import threading
from core.server import start_server
from core.client import ChatClient
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
                                                                    
    Secure Console Chat via Tor Hidden Service
    """)

def print_menu():
    print("\n=== MAIN MENU ===")
    print("1. Create a new chat room")
    print("2. Join an existing chat room")
    print("3. About")
    print("4. Exit")
    print("\nSelect an option: ", end="")

def chat_room(client):
    clear_screen()
    print(f"=== CHAT ROOM: {client.room_code} ===")
    print("Type your message and press Enter to send.")
    print("Commands: /exit, /clear, /delete [msg_id], /history")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("> ")
            
            if user_input.lower() == "/exit":
                break
            elif user_input.lower() == "/clear":
                clear_screen()
                print(f"=== CHAT ROOM: {client.room_code} ===")
            elif user_input.lower().startswith("/delete "):
                msg_id = user_input.split(" ", 1)[1].strip()
                client.delete_message(msg_id)
                print(f"[System] Requested deletion of message {msg_id}")
            elif user_input.lower() == "/history":
                clear_screen()
                print("=== MESSAGE HISTORY ===")
                for msg in client.message_history:
                    print(f"[{msg['msg_id']}] {msg['username']}: {msg['message']}")
                print("=" * 50)
            elif user_input.strip():
                client.send_message(user_input)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[-] Error: {e}")
    
    print("[+] Leaving chat room...")
    client.disconnect()

def main():
    print_banner()
    port = 8000
    
    print("[+] Initializing BlackOut secure chat...")
    
    tor_process, onion_address = start_tor_service(port)
    if not onion_address:
        print("[-] Failed to get onion address. Using local address only.")
        server_url = f"http://127.0.0.1:{port}"
    else:
        server_url = f"http://{onion_address}"
    
    print(f"[+] Server URL: {server_url}")
    
    if not start_server(port=port):
        print("[-] Failed to start server")
        tor_process.terminate()
        return
    
    # Wait for server to be ready
    time.sleep(2)
    
    client = ChatClient(server_url=f"http://127.0.0.1:{port}")
    
    # Main application loop
    while True:
        print_menu()
        choice = input()
        
        if choice == "1":
            if client.connect():
                room_code = client.create_room()
                if room_code:
                    username = input("Enter your username: ")
                    if client.join_room(room_code, username):
                        print(f"[+] Room created and joined: {room_code}")
                        print(f"[+] Share this code with others: {room_code}")
                        input("Press Enter to continue to chat...")
                        chat_room(client)
                    else:
                        client.disconnect()
        
        elif choice == "2":
            room_code = input("Enter room code: ")
            username = input("Enter your username: ")
            
            if client.connect():
                if client.join_room(room_code, username):
                    input("Press Enter to continue to chat...")
                    chat_room(client)
                else:
                    client.disconnect()
        
        elif choice == "3":
            clear_screen()
            print("=== ABOUT BLACKOUT ===")
            print("BlackOut is a secure chat application that operates over Tor hidden services.")
            print("All messages are encrypted with AES-128 in CBC mode.")
            print("This tool is designed for secure communications for journalists and whistleblowers.")
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
        print("[+] Terminating Tor process...")
        tor_process.terminate()
        tor_process.wait()
        print("[+] Goodbye!")

if __name__ == "__main__":
    main()