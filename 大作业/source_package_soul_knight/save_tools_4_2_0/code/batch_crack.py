import os
import json
import base64
import time
from collections import defaultdict
from Crypto.Cipher import DES

XOR_CRACK_TIMEOUT = 30   # XOR 爆破超时秒数，超时则跳过

# ============================================================
# 可配置密钥区 —— 修改这里即可切换密钥
# ============================================================
DES_KEY          = "iambo"            # DES 加密密钥 (从 CMD.EDI.EncryptHandler$$Decrypt 的调用方传入)
DES_XOR_CIPHER   = "\x11(55(#"        # unseeStrmaybepassword 字面量 (stringliteral 0x4BCC3EC)
DES_XOR_PASSWORD = "PASSWORD"         # 用于 XOR 解密 IV 的密码 (stringliteral "PASSWORD")

# ----------------- 核心算法区 ----------------- #
def get_t(i: int) -> int:
    """计算随着位置变化的干扰项"""
    return ((i % 15) * (i % 5)) % 92

def crypt_data(data: bytes, password: str) -> bytes:
    """XOR 加解密函数 (用于 game.data 及 IV 计算)"""
    result = bytearray(data)
    pwd_len = len(password)
    if pwd_len == 0: return data
    
    for i in range(len(result)):
        pc = ord(password[i % pwd_len])
        result[i] = result[i] ^ pc ^ get_t(i)
        
    return bytes(result)

def _pad_to_8(s: str) -> bytes:
    """将字符串截断/补零到 8 字节, 模拟 C# char[8] + Encoding.ASCII.GetBytes"""
    raw = s[:8].encode('ascii', errors='replace')
    return raw.ljust(8, b'\x00')

def _compute_des_iv(xor_cipher: str, xor_password: str) -> bytes:
    """
    还原 DES CBC IV:
      iv_string = Abo.CryptUtil.DecryptXor(unseeStrmaybepassword, password)
    然后截断/补零到 8 字节
    """
    cipher_bytes = xor_cipher.encode('latin-1')   # 保留原始字节值
    iv_bytes = crypt_data(cipher_bytes, xor_password)
    iv_str = iv_bytes.decode('latin-1')
    return _pad_to_8(iv_str)

def des_decrypt(ciphertext_b64: str,
                des_key: str = DES_KEY,
                xor_cipher: str = DES_XOR_CIPHER,
                xor_password: str = DES_XOR_PASSWORD) -> str:
    """
    还原 CMD.EDI.EncryptHandler$$Decrypt:
      1. 用 XOR 解密得到 IV
      2. 密钥和 IV 截断/补零到 8 字节
      3. Base64 解码密文
      4. DES-CBC + PKCS5 去填充
      5. 返回明文字符串
    """
    key_bytes = _pad_to_8(des_key)
    iv_bytes  = _compute_des_iv(xor_cipher, xor_password)
    raw = base64.b64decode(ciphertext_b64)
    cipher = DES.new(key_bytes, DES.MODE_CBC, iv_bytes)
    plaintext = cipher.decrypt(raw)
    # 去 PKCS5/PKCS7 填充
    pad_len = plaintext[-1]
    if 1 <= pad_len <= 8 and plaintext[-pad_len:] == bytes([pad_len]) * pad_len:
        plaintext = plaintext[:-pad_len]
    return plaintext.decode('utf-8')

def des_encrypt(plaintext: str,
                des_key: str = DES_KEY,
                xor_cipher: str = DES_XOR_CIPHER,
                xor_password: str = DES_XOR_PASSWORD) -> str:
    """
    DES-CBC 加密 + Base64 编码 (用于重新打包)
    """
    key_bytes = _pad_to_8(des_key)
    iv_bytes  = _compute_des_iv(xor_cipher, xor_password)
    data = plaintext.encode('utf-8')
    # PKCS5/PKCS7 填充
    pad_len = 8 - len(data) % 8
    data += bytes([pad_len]) * pad_len
    cipher = DES.new(key_bytes, DES.MODE_CBC, iv_bytes)
    encrypted = cipher.encrypt(data)
    return base64.b64encode(encrypted).decode('ascii')

def crack_password(ciphertext: bytes, max_pwd_len: int = 50, timeout: float = XOR_CRACK_TIMEOUT) -> list:
    """通过 JSON 常见符号组合反推密码 (带超时)"""
    patterns = [b'{"', b'":', b',"', b'"}', b':[', b']}']
    candidates = []
    start_time = time.time()

    for pwd_len in range(1, max_pwd_len + 1):
        if time.time() - start_time > timeout:
            print(f"    [!] XOR 爆破超时 ({timeout}s)，已尝试密码长度 1~{pwd_len-1}，跳过")
            break
        votes = [defaultdict(int) for _ in range(pwd_len)]
        for pattern in patterns:
            pat_len = len(pattern)
            for start_pos in range(len(ciphertext) - pat_len + 1):
                temp_pwd_chars = {}
                conflict = False
                for j in range(pat_len):
                    i = start_pos + j
                    pt_byte = pattern[j]
                    ct_byte = ciphertext[i]
                    guessed_key_byte = ct_byte ^ pt_byte ^ get_t(i)
                    
                    if not (32 <= guessed_key_byte <= 126):
                        conflict = True
                        break
                        
                    key_idx = i % pwd_len
                    if key_idx in temp_pwd_chars and temp_pwd_chars[key_idx] != guessed_key_byte:
                        conflict = True
                        break
                    temp_pwd_chars[key_idx] = guessed_key_byte
                
                if not conflict:
                    for k_idx, k_byte in temp_pwd_chars.items():
                        votes[k_idx][k_byte] += 1
                        
        guessed_password = bytearray(pwd_len)
        valid_password = True
        for k_idx in range(pwd_len):
            if not votes[k_idx]:
                valid_password = False
                break
            best_char = max(votes[k_idx].items(), key=lambda item: item[1])[0]
            guessed_password[k_idx] = best_char
            
        if valid_password:
            try:
                candidates.append(guessed_password.decode('utf-8'))
            except UnicodeDecodeError:
                pass
    return candidates

def _looks_like_base64_des(data: bytes) -> bool:
    """粗判是否像 DES 密文 (Base64 编码且解码后长度是 8 的倍数)"""
    try:
        text = data.decode('ascii').strip()
        if not text or len(text) < 8:
            return False
        raw = base64.b64decode(text, validate=True)
        return len(raw) % 8 == 0 and len(raw) >= 8
    except Exception:
        return False

# ----------------- 文件处理逻辑 ----------------- #
def try_decrypt(data: bytes, filename: str = ""):
    """尝试多种方式解密文件，返回 (解析后的JSON对象, 使用的密钥/方式)"""
    # 1. 尝试直接作为明文 JSON 解析
    try:
        text = data.decode('utf-8')
        parsed = json.loads(text)
        return parsed, "plaintext"
    except Exception:
        pass

    # 2. 尝试 DES-CBC 解密 (item_data.data 等)
    des_attempted = False
    if _looks_like_base64_des(data):
        des_attempted = True
        try:
            ciphertext_b64 = data.decode('ascii').strip()
            plaintext = des_decrypt(ciphertext_b64)
            parsed = json.loads(plaintext)
            return parsed, f"DES(key={DES_KEY})"
        except json.JSONDecodeError:
            print(f"    [!] DES 解密成功但 JSON 解析失败，密钥可能不对: {filename}")
        except UnicodeDecodeError:
            print(f"    [!] DES 解密产生非 UTF-8 数据，密钥可能不对: {filename}")
        except Exception as e:
            print(f"    [!] DES 解密异常 ({type(e).__name__}: {e}): {filename}")

    # 3. 尝试定制的 XOR 算法爆破 (game.data 等)
    possible_passwords = crack_password(data)
    for pwd in possible_passwords:
        decrypted_bytes = crypt_data(data, pwd)
        try:
            text = decrypted_bytes.decode('utf-8')
            parsed = json.loads(text)
            return parsed, pwd
        except Exception:
            continue
            
    return None, None

def _load_cracked_keys(key_log_file: str) -> dict:
    """从 cracked_keys.txt 加载已破解的文件→密钥映射"""
    cache = {}
    if not os.path.exists(key_log_file):
        return cache
    with open(key_log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ": " in line:
                path, key = line.split(": ", 1)
                cache[path] = key   # 后出现的覆盖先出现的
    return cache

# ----------------- 批量执行流程 ----------------- #
if __name__ == "__main__":
    workspace = r"E:\Crack\soul-knight-4-2-0\crack"
    in_dir = os.path.join(workspace, "datafile", "files")
    out_dir = os.path.join(workspace, "datafile", "decryptFiles")
    key_log_file = os.path.join(workspace, "datafile", "cracked_keys.txt")

    if not os.path.exists(in_dir):
        print(f"[-] 输入目录不存在: {in_dir}")
        exit(1)

    # 加载已有的破解记录，跳过已知文件
    cracked_cache = _load_cracked_keys(key_log_file)
    if cracked_cache:
        print(f"[*] 已加载 {len(cracked_cache)} 条历史破解记录，已解密文件将跳过")

    print(f"[*] 开始批量解密，源目录: {in_dir}")
    print(f"[*] 输出目录: {out_dir}")
    
    success_count = 0
    skip_count = 0
    fail_count = 0

    with open(key_log_file, "a", encoding="utf-8") as key_out:
        for root, dirs, files in os.walk(in_dir):
            # 构建对应的输出目录层次
            rel_path = os.path.relpath(root, in_dir)
            target_out_dir = os.path.join(out_dir, rel_path) if rel_path != "." else out_dir
            if not os.path.exists(target_out_dir):
                os.makedirs(target_out_dir)

            for file in files:
                in_path = os.path.join(root, file)
                out_path = os.path.join(target_out_dir, file + ".json")
                rel_file_path = os.path.join(rel_path, file) if rel_path != "." else file

                # 复用已有破解记录
                if rel_file_path in cracked_cache:
                    if os.path.exists(out_path):
                        print(f"[~] 跳过 (已解密): {rel_file_path} (密钥: {cracked_cache[rel_file_path]})")
                        skip_count += 1
                        continue
                
                with open(in_path, "rb") as f:
                    cipher_bytes = f.read()
                
                if not cipher_bytes:
                    continue

                t0 = time.time()
                parsed_json, key = try_decrypt(cipher_bytes, filename=rel_file_path)
                elapsed = time.time() - t0
                
                if parsed_json is not None:
                    with open(out_path, "w", encoding="utf-8") as out_f:
                        json.dump(parsed_json, out_f, indent=4, ensure_ascii=False)
                        
                    key_out.write(f"{rel_file_path}: {key}\n")
                    key_out.flush()
                    print(f"[+] 成功: {rel_file_path} (密钥/方式: {key}) [{elapsed:.1f}s]")
                    success_count += 1
                else:
                    print(f"[-] 失败: {rel_file_path} (无法爆破或非标准JSON加密) [{elapsed:.1f}s]")
                    fail_count += 1

    print("=" * 50)
    print(f"批量处理完成！成功 {success_count} 个，跳过 {skip_count} 个，失败 {fail_count} 个。")
    print(f"所有的破解记录已保存于: {key_log_file}")
