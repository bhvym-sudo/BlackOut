import os
import subprocess
import threading
import time
import socket

def wait_for_tor_ready(port):
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(("127.0.0.1", port))
            sock.close()
            return True
        except:
            time.sleep(1)
    return False

def monitor_tor_output(process):
    bootstrap_complete = False
    start_time = time.time()
    
    while not bootstrap_complete and (time.time() - start_time) < 30:
        try:
            if process.poll() is not None:
                break
                
            line = process.stdout.readline()
            if line:
                line = line.strip()
                if "Bootstrapped 100%" in line:
                    print(f"[Tor] {line}")
                    bootstrap_complete = True
                    break
                elif "err" in line.lower() or "warn" in line.lower():
                    print(f"[Tor] {line}")
        except:
            time.sleep(0.1)
    
    return bootstrap_complete

def start_tor_service(port=8000):
    print("[+] Starting Tor hidden service...")
    
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
Log notice stdout
        """)
    
    try:
        tor_process = subprocess.Popen([
            tor_exe, "-f", torrc_path
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    except FileNotFoundError:
        print("[-] Tor executable not found. Please ensure tor.exe is in the tor/ directory")
        return None, None
    
    print("[+] Waiting for Tor to initialize...")
    
    bootstrap_complete = monitor_tor_output(tor_process)
    
    if not bootstrap_complete:
        print("[+] Tor bootstrap timeout - checking if service is ready...")
    
    if not wait_for_tor_ready(9050):
        print("[-] Tor SOCKS port not ready")
        tor_process.terminate()
        return None, None
    
    time.sleep(2)
    
    try:
        onion_file = os.path.join(hidden_dir, "hostname")
        max_wait = 10
        wait_count = 0
        
        while not os.path.exists(onion_file) and wait_count < max_wait:
            time.sleep(1)
            wait_count += 1
        
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