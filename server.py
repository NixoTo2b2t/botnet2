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
def forward_data(source, destination, aes_key, is_client_to_target):
    while True:
        try:
            data = source.recv(4096)
            if not data:
                break
            
            # Если данные идут от клиента к целевому хосту, расшифровываем
            if is_client_to_target:
                decrypted_data = decrypt_data(aes_key, data)
                destination.sendall(decrypted_data)
            # Если данные идут от целевого хоста к клиенту, шифруем
            else:
                encrypted_data = encrypt_data(aes_key, data)
                destination.sendall(encrypted_data)

        except Exception as e:
            print(f"[-] Ошибка перенаправления данных: {e}")
            break

# Обработка клиентского соединения
def handle_client(client_socket, server_rsa_private_key):
    try:
        # 1. Обмен ECDH публичными ключами для генерации общего секрета (PFS)
        server_ecdh_private_key, server_ecdh_public_key = generate_ecdh_keys()
        server_ecdh_public_key_pem = serialize_ecdh_public_key(server_ecdh_public_key)
        client_socket.sendall(server_ecdh_public_key_pem)

        client_ecdh_public_key_pem = client_socket.recv(4096)
        client_ecdh_public_key = deserialize_ecdh_public_key(client_ecdh_public_key_pem)

        # 2. Вычисление общего секрета
        aes_key = derive_shared_key(server_ecdh_private_key, client_ecdh_public_key)

        print(f"[+] Установлено зашифрованное соединение с {client_socket.getpeername()}")

        # Ожидаем от клиента информацию о целевом хосте и порте
        encrypted_target_info = client_socket.recv(4096)
        target_info = decrypt_data(aes_key, encrypted_target_info).decode().split(":")
        target_host = target_info[0]
        target_port = int(target_info[1])

        # Подключаемся к целевому хосту
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.connect((target_host, target_port))
        print(f"[+] Подключено к целевому хосту: {target_host}:{target_port}")

        # Запускаем перенаправление трафика в обе стороны
        client_to_target_thread = threading.Thread(target=forward_data, args=(client_socket, target_socket, aes_key, True))
        target_to_client_thread = threading.Thread(target=forward_data, args=(target_socket, client_socket, aes_key, False))

        client_to_target_thread.start()
        target_to_client_thread.start()

        client_to_target_thread.join()
        target_to_client_thread.join()

    except Exception as e:
        print(f"[-] Ошибка при обработке клиента: {e}")
    finally:
        client_socket.close()

def start_server(host, port):
    server_rsa_private_key, server_rsa_public_key = generate_rsa_keys()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[*] Сервер слушает на {host}:{port}")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"[*] Принято соединение от {addr[0]}:{addr[1]}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket, server_rsa_private_key))
        client_handler.start()

if __name__ == "__main__":
    HOST = input("Введите IP-адрес для сервера (например, 0.0.0.0): ")
    PORT = int(input("Введите порт для сервера (например, 9999): "))
    start_server(HOST, PORT)



