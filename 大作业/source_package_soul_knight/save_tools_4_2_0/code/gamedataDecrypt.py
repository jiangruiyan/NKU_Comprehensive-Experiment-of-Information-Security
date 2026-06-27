def xor_crypt(data: bytes, password: str) -> bytes:
    """
    元气骑士 4.x 通用 XOR 加解密算法
    由于 XOR 的对称性，传入明文就是加密，传入密文就是解密。
    """
    result = bytearray(data)
    pwd_len = len(password)
    
    # 对应汇编中的 while (true) 大循环
    for i in range(len(result)):
        # 对应 System.String$$get_Chars
        key_char = ord(password[i % pwd_len])
        
        # 对应 r0_12 = r6_2 % 0xf * (r6_2 + 0 - r6_2 / 5 * 5);
        t = (i % 15) * (i % 5)
        
        # 对应 *(uint8_t*)(... + 0x10) = (int8_t)(r0_12 % 0x5c) ^ r0_10 ^ r0_15;  
        # (0x5c 就是 92)
        result[i] = result[i] ^ key_char ^ (t % 92)
        
    return bytes(result)







