import os
import subprocess
import threading
import time
import socket

def print_stream(stream, prefix):
    while True:
        line = stream.readline()
        if not line:
            break
        # Only show Tor messages after menu is displayed
        if "Bootstrapped 100%" in line:
            print(f"[{prefix}] {line.strip()}")

def wait_for_tor_ready(port):
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            sock.close()
            return True
        except:
            time.sleep(1)

def start_tor_service(port=8000):
    print("[+] Starting Tor hidden service...")
    
    # Fix path construction - remove one level of directory traversal
    tor_exe = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tor", "tor.exe")
    torrc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tor", "torrc")
    
    tor_dir = os.path.dirname(torrc_path)
    data_dir = os.path.join(tor_dir, "Data")
    hidden_dir = os.path.join(tor_dir, "hidden_service")
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(hidden_dir, exist_ok=True)
    
    with open(torrc_path, "w") as f:
        f.write(f"""SocksPort 9050
ControlPort 9051
DataDirectory {data_dir}
HiddenServiceDir {hidden_dir}
HiddenServicePort 80 127.0.0.1:{port}
        """)
    
    tor_process = subprocess.Popen([
        tor_exe, "-f", torrc_path
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    threading.Thread(target=lambda: print_stream(tor_process.stdout, "Tor"), daemon=True).start()
    threading.Thread(target=lambda: print_stream(tor_process.stderr, "Tor Error"), daemon=True).start()
    
    print("[+] Waiting for Tor to initialize...")
    wait_for_tor_ready(9050)
    
    # Wait specifically for 100% bootstrap
    while True:
        line = tor_process.stdout.readline()
        if not line:
            break
        if "Bootstrapped 100%" in line:
            print(f"[Tor] {line.strip()}")
            break
    
    try:
        onion_file = os.path.join(hidden_dir, "hostname")
        if os.path.exists(onion_file):
            with open(onion_file, "r") as f:
                onion_address = f.read().strip()
                print(f"[+] Onion address: {onion_address}")
                return tor_process, onion_address
        else:
            print("[-] Onion hostname file not found")
            return tor_process, None
    except Exception as e:
        print(f"[-] Error reading onion address: {e}")
        return tor_process, None