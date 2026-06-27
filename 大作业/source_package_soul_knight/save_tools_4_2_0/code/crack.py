import os
import json
from collections import defaultdict

# ----------------- 核心算法区 ----------------- #
def get_t(i: int) -> int:
    """计算随着位置变化的干扰项 (完全还原反汇编公式)"""
    return ((i % 15) * (i % 5)) % 92

def crypt_data(data: bytes, password: str) -> bytes:
    """双向加解密函数由于是 XOR，加密和解密用的是同一个函数"""
    result = bytearray(data)
    pwd_len = len(password)
    
    for i in range(len(result)):
        pc = ord(password[i % pwd_len])
        result[i] = result[i] ^ pc ^ get_t(i)
        
    return bytes(result)

# ----------------- 爆破核心区 ----------------- #
def crack_password(ciphertext: bytes, max_pwd_len: int = 50) -> list:
    """
    已知明文攻击：通过 JSON 常见的符号组合反推密码
    原理: C(密文) = P(明文) ^ K(密码) ^ T(干扰项)
    推出: K(密码) = C(密文) ^ P(明文) ^ T(干扰项)
    """
    # 既然是 JSON 档，必然大量包含以下符号特征组合
    patterns = [b'{"', b'":', b',"', b'"}', b':[', b']}']
    candidates = []

    print("[*] 开始爆击密钥规律，扫描 JSON 指纹...")
    
    # 假设密码长度在 1 到 max_pwd_len 之间
    for pwd_len in range(1, max_pwd_len + 1):
        # 建立一个“投票箱”，用来统计这 pwd_len 个密码字符中最可能的真实字母
        votes = [defaultdict(int) for _ in range(pwd_len)]
        
        # 拿着 JSON 特征词去密文里像滑块一样挨个滚动测试
        for pattern in patterns:
            pat_len = len(pattern)
            
            for start_pos in range(len(ciphertext) - pat_len + 1):
                temp_pwd_chars = {}
                conflict = False
                
                for j in range(pat_len):
                    i = start_pos + j
                    pt_byte = pattern[j]           # 猜想的明文(P)
                    ct_byte = ciphertext[i]        # 提取的密文(C)
                    
                    # 🚀 利用公式反推出当前的钥匙(K)
                    guessed_key_byte = ct_byte ^ pt_byte ^ get_t(i)
                    
                    # 密码一般是可见字符，如果算出乱码，说明这个位置猜错了，直接放弃
                    if not (32 <= guessed_key_byte <= 126):
                        conflict = True
                        break
                        
                    key_idx = i % pwd_len
                    # 检查在这个短片段内，推算出来的同一个位置的密码是否有冲突
                    if key_idx in temp_pwd_chars and temp_pwd_chars[key_idx] != guessed_key_byte:
                        conflict = True
                        break
                        
                    temp_pwd_chars[key_idx] = guessed_key_byte
                
                # 如果这个片段完美且没有冲突，给算出来的每个密码字符投一票
                if not conflict:
                    for k_idx, k_byte in temp_pwd_chars.items():
                        votes[k_idx][k_byte] += 1
                        
        # 统计投票，拼出该长度下最可能的密码
        guessed_password = bytearray(pwd_len)
        valid_password = True
        
        for k_idx in range(pwd_len):
            if not votes[k_idx]:  # 如果某个字母一个有意义的票都没得到，说明这个密码长度不对
                valid_password = False
                break
                
            # 选出该位置得票最多的字母
            best_char = max(votes[k_idx].items(), key=lambda item: item[1])[0]
            guessed_password[k_idx] = best_char
            
        if valid_password:
            try:
                candidates.append(guessed_password.decode('utf-8'))
            except UnicodeDecodeError:
                pass

    return candidates

# ----------------- 执行流程 ----------------- #
if __name__ == "__main__":
    file_name = "E:\Crack\soul-knight-4-2-0\crack\code\game.data"
    
    if not os.path.exists(file_name):
        print(f"[-] 找不到文件 {file_name}，请将存档放到当前目录！")
        exit(1)
        
    with open(file_name, "rb") as f:
        cipher_bytes = f.read()
        
    print(f"[*] 成功读取存档，累计 {len(cipher_bytes)} 字节。")
    
    # 爆出所有候选密码 (基于各种长度猜测)
    possible_passwords = crack_password(cipher_bytes)
    print(f"[+] 找到了 {len(possible_passwords)} 条可能的密码线路，开始尝试解密...")
    
    success = False
    for pwd in possible_passwords:
        # 用推算出来的密码试着去解密
        decrypted_bytes = crypt_data(cipher_bytes, pwd)
        try:
            # 尝试解码并解析为 JSON
            decrypted_str = decrypted_bytes.decode('utf-8')
            parsed_json = json.loads(decrypted_str)
            
            print("\n" + "="*50)
            print(f"✅ 爆破成功！")
            print(f"🔑 真正的密钥是: '{pwd}'")
            print(f"📊 解密后的 JSON 前 200 个字符预览:")
            print(decrypted_str[:200] + "...")
            print("="*50)
            
            # 将解密出的 JSON 写入新文件 (与输入文件同目录)
            import os
            out_file = os.path.join(os.path.dirname(os.path.abspath(file_name)), "decrypted_game.json")
            with open(out_file, "w", encoding="utf-8") as out:
                out.write(json.dumps(parsed_json, indent=4, ensure_ascii=False))
            print(f"[+] 明文存档已保存为: {out_file}")
            
            # 将密钥追加记录到同级目录的文件中
            key_log_file = os.path.join(os.path.dirname(os.path.abspath(file_name)), "cracked_keys.txt")
            with open(key_log_file, "a", encoding="utf-8") as key_out:
                base_name = os.path.basename(file_name)
                key_out.write(f"{base_name}: {pwd}\n")
            print(f"[+] 密钥已同步记录至: {key_log_file}")
            
            success = True
            break # 成功解密，退出轮询
        except Exception:
            # 解析 JSON 失败说明这个猜测的密码不对，继续试下一个
            continue
            
    if not success:
        print("[-] 爆破失败：未能找出正确的密码，或存档已被完全破坏。")