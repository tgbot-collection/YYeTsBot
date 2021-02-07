#!/usr/local/bin/python3
# coding: utf-8

# YYeTsBot - test.py
# 2/7/21 12:07
#

__author__ = "Benny <benny.think@gmail.com>"

import base64
from hashlib import md5
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def pad(data):
    length = 16 - (len(data) % 16)
    return data + (chr(length) * length).encode()


def unpad(data):
    return data[:-(data[-1] if type(data[-1]) == int else ord(data[-1]))]


def bytes_to_key(data, salt, output=48):
    # extended from https://gist.github.com/gsakkis/4546068
    assert len(salt) == 8, len(salt)
    data = bytes(data, "ascii")
    data += salt
    key = md5(data).digest()
    final_key = key
    while len(final_key) < output:
        key = md5(key + data).digest()
        final_key += key
    return final_key[:output]


def decrypt(encrypted, passphrase):
    encrypted = base64.b64decode(encrypted)
    assert encrypted[0:8] == b"Salted__"
    salt = encrypted[8:16]
    key_iv = bytes_to_key(passphrase, salt, 32 + 16)
    key = key_iv[:32]
    iv = key_iv[32:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    a = decryptor.update(encrypted[16:]) + decryptor.finalize()
    return unpad(a)


if __name__ == '__main__':
    passphrase = "39300"
    test = "U2FsdGVkX19Sch0x9oifjNaBt9eTkZSPUUVVhpjAp0s="
    result = decrypt(test, passphrase)
    print(result)
