# Import necessary modules from pycryptodome
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
# This module converts binary data to hexadecimal
from binascii import hexlify, unhexlify

g = open("/run/secrets/rsa_psw")
pwd = g.read()
g.close()

with open("docker/mysecretkey.pem", "rb") as f:
    data = f.read()
    mykey = RSA.import_key(data, pwd)

public_key = mykey.public_key()

def encrypt_note(note: str):
    to_en = note.encode()
    cipher_rsa = PKCS1_OAEP.new(public_key)
    encrypted = cipher_rsa.encrypt(to_en)
    encrypted_string = hexlify(encrypted)
    return encrypted_string.decode()

def decrypt_note(note: str):
    to_dec = note.encode()
    binary_data = unhexlify(to_dec)
    cipher_rsa = PKCS1_OAEP.new(mykey)
    decrypted = cipher_rsa.decrypt(binary_data)
    return decrypted.decode()