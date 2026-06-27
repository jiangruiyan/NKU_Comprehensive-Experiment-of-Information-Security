"""独立测试 DES 加解密逻辑"""
import base64
from Crypto.Cipher import DES

def get_t(i):
    return ((i % 15) * (i % 5)) % 92

def crypt_data(data, password):
    result = bytearray(data)
    pwd_len = len(password)
    for i in range(len(result)):
        pc = ord(password[i % pwd_len])
        result[i] = result[i] ^ pc ^ get_t(i)
    return bytes(result)

def pad_to_8(s):
    raw = s[:8].encode('ascii', errors='replace')
    return raw.ljust(8, b'\x00')

# 1. IV 计算
unsee_bytes = "\x11(55(#".encode('latin-1')
iv_decrypted = crypt_data(unsee_bytes, "PASSWORD")
iv_str = iv_decrypted.decode('latin-1')
iv_padded = pad_to_8(iv_str)
print(f"IV decrypted string: {iv_str!r}")
print(f"IV padded hex:       {iv_padded.hex()}")
print(f"IV expected hex:     4168626f6f6c0000  (Ahbool\\x00\\x00)")
print(f"IV match: {iv_padded.hex() == '4168626f6f6c0000'}")
print()

# 2. Key 计算
key_padded = pad_to_8("iambo")
print(f"Key padded hex:      {key_padded.hex()}")
print(f"Key expected hex:    69616d626f000000  (iambo\\x00\\x00\\x00)")
print(f"Key match: {key_padded.hex() == '69616d626f000000'}")
print()

# 3. 加解密轮回测试
test_json = '{"hello":"world","gems":999}'
# Encrypt
data = test_json.encode('utf-8')
pad_len = 8 - len(data) % 8
data += bytes([pad_len]) * pad_len
cipher = DES.new(key_padded, DES.MODE_CBC, iv_padded)
encrypted = base64.b64encode(cipher.encrypt(data)).decode('ascii')
print(f"Encrypted b64: {encrypted}")

# Decrypt
raw = base64.b64decode(encrypted)
cipher2 = DES.new(key_padded, DES.MODE_CBC, iv_padded)
plain = cipher2.decrypt(raw)
p = plain[-1]
if 1 <= p <= 8:
    plain = plain[:-p]
decrypted = plain.decode('utf-8')
print(f"Decrypted:     {decrypted}")
print(f"Roundtrip OK:  {decrypted == test_json}")
