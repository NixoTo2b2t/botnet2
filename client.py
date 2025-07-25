import socket
import threading
import ssl
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

from key_manager import generate_rsa_keys, serialize_rsa_public_key, deserialize_rsa_public_key, \
                        generate_ecdh_keys, serialize_ecdh_public_key, deserialize_ecdh_public_key, \
                        derive_shared_key, encrypt_data, decrypt_data

# Функция для перенаправления трафика
def forward_data(source, destination, aes_key, is_client_to_server):
    while True:
        try:
            data = source.recv(4096)
            if not data:
                break
            
            # Если данные идут от локального клиента к серверу, шифруем
            if is_client_to_server:
                encrypted_data = encrypt_data(aes_key, data)
                destination.sendall(encrypted_data)
            # Если данные идут от сервера к локальному клиенту, расшифровываем
            else:
                decrypted_data = decrypt_data(aes_key, data)
                destination.sendall(decrypted_data)

        except Exception as e:
            print(f"[-] Ошибка перенаправления данных: {e}")
            break

# Обработка клиентского соединения
def handle_client_connection(client_conn, server_host, server_port, client_rsa_private_key):
    try:
        # Подключаемся к серверу
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((server_host, server_port))

        # 1. Обмен ECDH публичными ключами для генерации общего секрета (PFS)
        server_ecdh_public_key_pem = server_socket.recv(4096)
        server_ecdh_public_key = deserialize_ecdh_public_key(server_ecdh_public_key_pem)

        client_ecdh_private_key, client_ecdh_public_key = generate_ecdh_keys()
        client_ecdh_public_key_pem = serialize_ecdh_public_key(client_ecdh_public_key)
        server_socket.sendall(client_ecdh_public_key_pem)

        # 2. Вычисление общего секрета
        aes_key = derive_shared_key(client_ecdh_private_key, server_ecdh_public_key)

        print(f"[+] Установлено зашифрованное соединение с сервером {server_host}:{server_port}")

        # SOCKS5 Handshake
        # Читаем запрос клиента (CONNECT)
        request = client_conn.recv(4096)
        if request[0] != 0x05: # SOCKS5 version
            raise Exception("Unsupported SOCKS version")

        # Отправляем ответ SOCKS5 (No authentication required)
        client_conn.sendall(b'\x05\x00')

        # Читаем запрос на подключение
        request = client_conn.recv(4096)
        if request[1] != 0x01: # CONNECT command
            raise Exception("Unsupported SOCKS command")

        addr_type = request[3]
        if addr_type == 0x01: # IPv4
            target_host = socket.inet_ntoa(request[4:8])
            target_port = int.from_bytes(request[8:10], 'big')
        elif addr_type == 0x03: # Domain name
            domain_len = request[4]
            target_host = request[5:5+domain_len].decode()
            target_port = int.from_bytes(request[5+domain_len:7+domain_len], 'big')
        else:
            raise Exception("Unsupported address type")

        print(f"[+] SOCKS5 запрос на {target_host}:{target_port}")

        # Отправляем информацию о целевом хосте и порте на сервер
        encrypted_target_info = encrypt_data(aes_key, f"{target_host}:{target_port}".encode())
        server_socket.sendall(encrypted_target_info)

        # Отправляем ответ SOCKS5 (Connection established)
        client_conn.sendall(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')

        # Запускаем перенаправление трафика в обе стороны
        client_to_server_thread = threading.Thread(target=forward_data, args=(client_conn, server_socket, aes_key, True))
        server_to_client_thread = threading.Thread(target=forward_data, args=(server_socket, client_conn, aes_key, False))

        client_to_server_thread.start()
        server_to_client_thread.start()

        client_to_server_thread.join()
        server_to_client_thread.join()

    except Exception as e:
        print(f"[-] Ошибка при обработке клиентского соединения: {e}")
    finally:
        client_conn.close()

def start_client(local_host, local_port, server_host, server_port):
    client_rsa_private_key, client_rsa_public_key = generate_rsa_keys()

    local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    local_socket.bind((local_host, local_port))
    local_socket.listen(5)
    print(f"[*] Клиент SOCKS5 прокси слушает на {local_host}:{local_port}")

    while True:
        client_conn, addr = local_socket.accept()
        print(f"[*] Принято локальное соединение от {addr[0]}:{addr[1]}")
        client_handler = threading.Thread(target=handle_client_connection, args=(client_conn, server_host, server_port, client_rsa_private_key))
        client_handler.start()

if __name__ == "__main__":
    LOCAL_HOST = '127.0.0.1'
    LOCAL_PORT = int(input("Введите локальный порт для SOCKS5 прокси (например, 1080): "))
    SERVER_HOST = input("Введите IP-адрес сервера: ")
    SERVER_PORT = int(input("Введите порт сервера: "))
    start_client(LOCAL_HOST, LOCAL_PORT, SERVER_HOST, SERVER_PORT)

