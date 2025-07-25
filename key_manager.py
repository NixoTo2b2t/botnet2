from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

# Генерация RSA ключей
def generate_rsa_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

# Сериализация публичного ключа RSA
def serialize_rsa_public_key(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

# Десериализация публичного ключа RSA
def deserialize_rsa_public_key(pem_data):
    return serialization.load_pem_public_key(
        pem_data,
        backend=default_backend()
    )

# Генерация ECDH ключей
def generate_ecdh_keys():
    private_key = ec.generate_private_key(
        ec.SECP384R1(), # Выбираем эллиптическую кривую
        default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

# Сериализация публичного ключа ECDH
def serialize_ecdh_public_key(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

# Десериализация публичного ключа ECDH
def deserialize_ecdh_public_key(pem_data):
    return serialization.load_pem_public_key(
        pem_data,
        backend=default_backend()
    )

# Вычисление общего секрета ECDH
def derive_shared_key(private_key, peer_public_key):
    shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
    derived_key = HKDF( # Используем HKDF для получения ключа фиксированной длины
        algorithm=hashes.SHA256(),
        length=32, # 256 бит для AES-256
        salt=None,
        info=b'handshake data',
        backend=default_backend()
    ).derive(shared_key)
    return derived_key

# Генерация случайного AES ключа (для случаев без PFS)
def generate_aes_key():
    return os.urandom(32) # 256 бит для AES-256

# Шифрование данных с помощью AES-256-GCM
def encrypt_data(key, data):
    iv = os.urandom(12)  # GCM требует 12-байтовый IV
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    return iv + encryptor.tag + ciphertext

# Расшифровка данных с помощью AES-256-GCM
def decrypt_data(key, encrypted_data):
    if len(encrypted_data) < 28:  # 12 байт IV + 16 байт tag
        raise ValueError("Encrypted data too short")
    
    iv = encrypted_data[:12]
    tag = encrypted_data[12:28]
    ciphertext = encrypted_data[28:]
    
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    # decryptor.authenticate_additional_data(b'') # This line is not needed when tag is passed to GCM constructor
    return decryptor.update(ciphertext) + decryptor.finalize()

